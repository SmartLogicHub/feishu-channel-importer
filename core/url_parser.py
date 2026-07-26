"""Parse Feishu Bitable app, table and view identifiers from user input."""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class BitableLocation:
    app_token: str
    table_id: str | None = None
    view_id: str | None = None


def parse_bitable_url(value: str) -> BitableLocation:
    text = str(value or "").strip()
    if not text:
        raise ValueError("请输入飞书多维表格链接或 app_token")

    if "://" not in text:
        if TOKEN_RE.fullmatch(text):
            return BitableLocation(app_token=text)
        raise ValueError("无法识别飞书多维表格链接")

    parsed = urlparse(text)
    path_parts = [part for part in parsed.path.split("/") if part]
    try:
        base_index = path_parts.index("base")
        app_token = path_parts[base_index + 1]
    except (ValueError, IndexError) as exc:
        raise ValueError("链接中缺少 /base/{app_token}") from exc

    if not TOKEN_RE.fullmatch(app_token):
        raise ValueError("链接中的 app_token 无效")

    query = parse_qs(parsed.query)
    table_id = query.get("table", [None])[0]
    view_id = query.get("view", [None])[0]
    return BitableLocation(app_token=app_token, table_id=table_id, view_id=view_id)
