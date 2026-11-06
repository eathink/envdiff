"""比较两份键值对，给出结构化差异。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"
    SAME = "same"


@dataclass(frozen=True)
class Entry:
    key: str
    left: str | None
    right: str | None
    status: Status


def diff_environments(left: dict[str, str], right: dict[str, str]) -> list[Entry]:
    """按 key 排序返回全部差异（含 SAME，便于调用方过滤）。"""
    entries: list[Entry] = []
    for key in sorted(set(left) | set(right)):
        in_left = key in left
        in_right = key in right
        if in_left and in_right:
            status = Status.SAME if left[key] == right[key] else Status.CHANGED
            entries.append(Entry(key, left[key], right[key], status))
        elif in_left:
            entries.append(Entry(key, left[key], None, Status.REMOVED))
        else:
            entries.append(Entry(key, None, right[key], Status.ADDED))
    return entries


def summarize(entries: list[Entry]) -> dict[str, int]:
    counts = {status.value: 0 for status in Status}
    for entry in entries:
        counts[entry.status.value] += 1
    return counts


def has_differences(entries: list[Entry]) -> bool:
    return any(entry.status is not Status.SAME for entry in entries)
