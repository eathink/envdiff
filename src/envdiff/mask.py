"""识别并脱敏疑似密钥。

两个维度同时判断：
1. 变量名像密钥（*_TOKEN、*_PASSWORD、API_KEY ...）
2. 变量值本身符合已知密钥格式（ghp_、sk-、AKIA ...）

脱敏后保留长度与指纹，便于判断"是否变了"，但不泄露原文。
"""

from __future__ import annotations

import hashlib
import re

# 变量名中的敏感片段。前后必须是词边界，避免 MONKEY 这类误判。
_SECRET_KEY_RE = re.compile(
    r"(?:^|_)(?:SECRETS?|TOKEN|PASSWORD|PASSWD|PWD|API_?KEY|PRIVATE_?KEY"
    r"|CREDENTIALS?|ACCESS_?KEY|AUTH_?TOKEN|SESSION)(?:$|_)",
    re.IGNORECASE,
)

# 常见密钥格式。命中即脱敏，无论变量名是什么。
_VALUE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    ),
)


def is_secret_key(key: str) -> bool:
    """变量名是否像密钥（PASSWORD、API_KEY 等）。"""
    return bool(_SECRET_KEY_RE.search(key))


def secret_kinds(value: str) -> list[str]:
    """返回值命中的密钥格式名称，空列表表示未命中。"""
    return [kind for kind, pattern in _VALUE_PATTERNS if pattern.search(value)]


def fingerprint(value: str) -> str:
    """值的短指纹，用于在脱敏后判断是否变化。"""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def mask_value(value: str) -> str:
    """脱敏：保留长度与指纹，去掉原文。"""
    return f"<redacted:{len(value)}c#{fingerprint(value)}>"
