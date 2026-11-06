"""把差异行渲染为 text / markdown / json。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .diff import Status


@dataclass(frozen=True)
class Row:
    key: str
    status: Status
    left: str | None
    right: str | None
    masked: bool = False
    kinds: tuple[str, ...] = field(default_factory=tuple)


_MARKERS = {
    Status.SAME: "=",
    Status.ADDED: "+",
    Status.REMOVED: "-",
    Status.CHANGED: "~",
}


def _one_line(value: str | None) -> str:
    if value is None:
        return ""
    return value.replace("\r", "\\r").replace("\n", "\\n")


def _markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def _summary_text(summary: dict[str, int]) -> str:
    return (
        f"{summary['changed']} 变更，{summary['added']} 新增，"
        f"{summary['removed']} 删除，{summary['same']} 未变"
    )


def render_text(
    rows: list[Row], summary: dict[str, int], left_label: str, right_label: str
) -> str:
    lines = [f"对比 {left_label} → {right_label}"]

    if not rows:
        lines.append("")
        lines.append(f"✓ 没有差异（{summary['same']} 个变量）")
        return "\n".join(lines)

    width = min(max((len(row.key) for row in rows), default=0), 40)
    lines.append("")
    for row in rows:
        marker = _MARKERS[row.status]
        if row.status is Status.CHANGED:
            value = f"{_one_line(row.left)} → {_one_line(row.right)}"
        elif row.status is Status.ADDED:
            value = _one_line(row.right)
        else:
            value = _one_line(row.left)
        lines.append(f"  {marker} {row.key:<{width}}  {value}")

    lines.append("")
    lines.append(_summary_text(summary))
    return "\n".join(lines)


def render_markdown(
    rows: list[Row], summary: dict[str, int], left_label: str, right_label: str
) -> str:
    lines = [
        f"对比 `{left_label}` → `{right_label}`",
        "",
        "| 状态 | 变量 | 左 | 右 |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        marker = _MARKERS[row.status]
        left = _markdown_escape(_one_line(row.left))
        right = _markdown_escape(_one_line(row.right))
        key = f"`{row.key}`"
        lines.append(f"| {marker} | {key} | {left} | {right} |")

    if not rows:
        lines.append("| | | | |")
        lines.append("")
        lines.append(f"✓ 没有差异（{summary['same']} 个变量）")
    else:
        lines.append("")
        lines.append(_summary_text(summary))
    return "\n".join(lines)


def render_json(
    rows: list[Row], summary: dict[str, int], left_label: str, right_label: str
) -> str:
    payload = {
        "left": left_label,
        "right": right_label,
        "summary": summary,
        "entries": [
            {
                "key": row.key,
                "status": row.status.value,
                "left": row.left,
                "right": row.right,
                "masked": row.masked,
                "secret_kinds": list(row.kinds),
            }
            for row in rows
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


RENDERERS = {
    "text": render_text,
    "markdown": render_markdown,
    "json": render_json,
}
