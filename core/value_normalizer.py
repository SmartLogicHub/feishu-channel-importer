"""Normalize Excel and Feishu field values before planning or writing."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from numbers import Number
import re
from zoneinfo import ZoneInfo


SHANGHAI = ZoneInfo("Asia/Shanghai")
EXCEL_EPOCH = datetime(1899, 12, 30, tzinfo=SHANGHAI)


class NormalizationError(ValueError):
    """Raised when a source value cannot be safely converted."""


def to_feishu_date_ms(value) -> int:
    if value is None or value == "":
        raise NormalizationError("日期不能为空")

    if isinstance(value, Number) and not isinstance(value, bool):
        numeric = float(value)
        if numeric >= 100_000_000_000:
            return int(numeric)
        if numeric >= 1_000_000_000:
            return int(numeric * 1000)
        return int((EXCEL_EPOCH + timedelta(days=numeric)).timestamp() * 1000)

    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()

    if isinstance(value, datetime):
        calendar_date = value.date()
    elif isinstance(value, date):
        calendar_date = value
    else:
        text_value = str(value).strip().replace("/", "-")
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text_value):
            return to_feishu_date_ms(float(text_value))
        try:
            calendar_date = datetime.fromisoformat(text_value).date()
        except ValueError as exc:
            raise NormalizationError(f"无法识别日期: {value}") from exc

    midnight = datetime.combine(calendar_date, time.min, tzinfo=SHANGHAI)
    return int(midnight.timestamp() * 1000)


def created_time_range(start_date: date, end_date: date) -> tuple[int, int]:
    if end_date < start_date:
        raise NormalizationError("结束日期不能早于开始日期")
    start = datetime.combine(start_date, time.min, tzinfo=SHANGHAI)
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=SHANGHAI)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def ms_to_shanghai_date(milliseconds: int) -> date:
    return datetime.fromtimestamp(milliseconds / 1000, tz=SHANGHAI).date()


def resolve_display_value(value, option_names: dict[str, str] | None = None) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("text", "name", "value"):
            if key in value:
                return resolve_display_value(value[key], option_names)
        parts = [resolve_display_value(item, option_names) for item in value.values()]
        return " | ".join(part for part in parts if part)
    if isinstance(value, (list, tuple, set)):
        parts = [resolve_display_value(item, option_names) for item in value]
        return " | ".join(part for part in parts if part)

    text_value = str(value).strip()
    if option_names is not None and text_value in option_names:
        return option_names[text_value]
    if option_names is not None and text_value.startswith("opt"):
        raise NormalizationError(f"无法解析飞书选项 ID: {text_value}")
    return text_value


def normalize_for_target(
    value, target_type: int, *, option_names: dict[str, str] | None = None
):
    if value is None or value == "":
        return ""
    if target_type == 5:
        return to_feishu_date_ms(value)

    display = resolve_display_value(value, option_names)
    if not display:
        return ""
    if target_type == 2:
        try:
            numeric = float(display.replace(",", ""))
        except ValueError as exc:
            raise NormalizationError(f"无法转换为数字: {display}") from exc
        return int(numeric) if numeric.is_integer() else numeric
    if target_type == 15:
        url = display if display.startswith(("http://", "https://")) else "https://" + display
        return {"link": url, "text": display}
    return display
