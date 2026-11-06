"""解析 .env / JSON 配置为扁平键值对。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_ESCAPES = {
    "n": "\n",
    "r": "\r",
    "t": "\t",
    '"': '"',
    "\\": "\\",
}


class ParseError(ValueError):
    """输入无法解析。消息中带文件名与行号。"""


def _split_quoted(value: str, source: str, lineno: int) -> tuple[str, str] | None:
    """拆出开头的引号字符串，返回 (内容, 剩余部分)；不以引号开头则返回 None。"""
    if not value:
        return None

    quote = value[0]
    if quote not in "\"'":
        return None

    out: list[str] = []
    i = 1
    while i < len(value):
        ch = value[i]
        if quote == '"' and ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            out.append(_ESCAPES.get(nxt, nxt))
            i += 2
            continue
        if ch == quote:
            return "".join(out), value[i + 1 :]
        out.append(ch)
        i += 1

    raise ParseError(f"{source}:{lineno}: 引号未闭合")


def _strip_inline_comment(rest: str) -> str:
    """去掉未加引号值后面的行内注释（要求 # 前有空白）。"""
    pos = rest.find(" #")
    if pos >= 0:
        rest = rest[:pos]
    elif rest.startswith("#"):
        rest = ""
    return rest.rstrip()


def parse_dotenv(text: str, source: str = "<input>") -> dict[str, str]:
    """解析 .env 文本。支持 export 前缀、单/双引号、行内注释。"""
    result: dict[str, str] = {}

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()

        if "=" not in line:
            raise ParseError(f"{source}:{lineno}: 缺少 '='")

        key, _, value = line.partition("=")
        key = key.strip()
        if not _KEY_RE.match(key):
            raise ParseError(f"{source}:{lineno}: 非法变量名 {key!r}")

        value = value.strip()
        quoted = _split_quoted(value, source, lineno)
        if quoted is not None:
            value, rest = quoted
            rest = rest.strip()
            if rest and not rest.startswith("#"):
                raise ParseError(f"{source}:{lineno}: 引号后有多余内容 {rest!r}")
        else:
            value = _strip_inline_comment(value)

        result[key] = value

    return result


def _scalar_to_str(value: object, source: str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    raise ParseError(f"{source}: 仅支持扁平 JSON 对象，遇到 {type(value).__name__}")


def parse_json(text: str, source: str = "<json>") -> dict[str, str]:
    """解析扁平 JSON 对象。嵌套结构会报错，避免隐式语义。"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"{source}:{exc.lineno}: JSON 解析失败：{exc.msg}") from exc

    if not isinstance(data, dict):
        raise ParseError(f"{source}: 顶层必须是 JSON 对象")

    result: dict[str, str] = {}
    for key, value in data.items():
        if not _KEY_RE.match(key):
            raise ParseError(f"{source}: 非法变量名 {key!r}")
        result[key] = _scalar_to_str(value, source)
    return result


def load_path(path: str) -> dict[str, str]:
    """按扩展名加载配置；`-` 表示从标准输入读取 .env。"""
    if path == "-":
        return parse_dotenv(sys.stdin.read(), "<stdin>")

    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        reason = exc.strerror or str(exc)
        raise ParseError(f"无法读取 {path}: {reason}") from exc

    if p.suffix.lower() == ".json":
        return parse_json(text, str(p))
    return parse_dotenv(text, str(p))
