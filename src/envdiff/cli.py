"""命令行入口。"""

from __future__ import annotations

import argparse
import fnmatch
import sys

from . import __version__
from .diff import Status, diff_environments, has_differences, summarize
from .mask import is_secret_key, mask_value, secret_kinds
from .parser import ParseError, load_path
from .render import RENDERERS, Row


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="envdiff",
        description="对比两份环境变量配置，默认脱敏输出差异。",
    )
    parser.add_argument("left", metavar="LEFT", help="基准配置：.env / .json 路径，或 - 表示标准输入")
    parser.add_argument("right", metavar="RIGHT", help="目标配置：.env / .json 路径")
    parser.add_argument(
        "-f", "--format", choices=sorted(RENDERERS), default="text", help="输出格式（默认 text）"
    )
    parser.add_argument("--all", action="store_true", help="同时列出未变化的变量")
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="GLOB",
        help="只保留 key 匹配该 glob 的变量，可重复",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="排除 key 匹配该 glob 的变量，可重复",
    )
    parser.add_argument(
        "--no-mask", action="store_true", help="输出原文，不脱敏（危险，仅本地调试）"
    )
    parser.add_argument("--exit-zero", action="store_true", help="即使有差异也返回 0")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _decorate(entry, mask: bool) -> Row:
    kinds = tuple(
        dict.fromkeys(
            secret_kinds(entry.left or "") + secret_kinds(entry.right or "")
        )
    )
    sensitive = is_secret_key(entry.key) or bool(kinds)

    left, right = entry.left, entry.right
    if mask and sensitive:
        left = None if left is None else mask_value(left)
        right = None if right is None else mask_value(right)

    return Row(entry.key, entry.status, left, right, masked=sensitive and mask, kinds=kinds)


def _filter_entries(entries, include: list[str], exclude: list[str]):
    """按 key 的 glob 过滤；大小写敏感，与 shell 的 fnmatch 一致。"""
    if include:
        entries = [
            entry
            for entry in entries
            if any(fnmatch.fnmatchcase(entry.key, pattern) for pattern in include)
        ]
    if exclude:
        entries = [
            entry
            for entry in entries
            if not any(fnmatch.fnmatchcase(entry.key, pattern) for pattern in exclude)
        ]
    return entries


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        left = load_path(args.left)
        right = load_path(args.right)
    except ParseError as exc:
        print(f"envdiff: {exc}", file=sys.stderr)
        return 2

    entries = diff_environments(left, right)
    entries = _filter_entries(entries, args.include, args.exclude)
    summary = summarize(entries)
    rows = [_decorate(entry, mask=not args.no_mask) for entry in entries]
    if not args.all:
        rows = [row for row in rows if row.status is not Status.SAME]

    if args.no_mask and any(is_secret_key(entry.key) or secret_kinds(entry.left or "") or secret_kinds(entry.right or "") for entry in entries):
        print("envdiff: 警告：--no-mask 会输出疑似密钥原文", file=sys.stderr)

    print(RENDERERS[args.format](rows, summary, args.left, args.right))

    if has_differences(entries) and not args.exit_zero:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
