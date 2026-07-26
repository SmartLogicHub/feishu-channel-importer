"""Pure mapping, validation and multi-count deduplication logic."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any

from .models import FieldMapping, PlanError, SourcePlan
from .value_normalizer import NormalizationError, normalize_for_target


class MappingError(ValueError):
    """Raised when a configured mapping cannot safely produce a target value."""


def _source_value(row: dict[str, Any], mapping: FieldMapping):
    if mapping.value_mode == "constant":
        return mapping.constant_value
    if mapping.value_mode != "source":
        raise MappingError(f"不支持的值来源: {mapping.value_mode}")
    for key in (mapping.source_field_id, mapping.source_field_name, mapping.excel_column):
        if key and key in row:
            return row[key]
    return ""


def map_source_row(
    row: dict[str, Any],
    mappings: list[FieldMapping],
    target_fields: dict[str, dict[str, Any]],
    source_option_names: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for mapping in mappings:
        if not mapping.enabled:
            continue
        target = target_fields.get(mapping.target_field_id)
        if target is None:
            raise MappingError(f"目标字段不存在: {mapping.target_field_name}")
        if not target.get("writable", True):
            raise MappingError(f"目标字段“{target['name']}”是只读字段，不能写入")

        raw_value = _source_value(row, mapping)
        option_names = None
        if source_option_names and mapping.source_field_id:
            option_names = source_option_names.get(mapping.source_field_id)
        try:
            value = normalize_for_target(
                raw_value, int(target["type"]), option_names=option_names
            )
        except NormalizationError as exc:
            raise MappingError(f"字段“{target['name']}”: {exc}") from exc

        if value == "" or value is None:
            continue
        target_options = target.get("options")
        if int(target["type"]) == 3 and target_options is not None:
            allowed = set(target_options.values()) if isinstance(target_options, dict) else set(target_options)
            if value not in allowed:
                raise MappingError(f"字段“{target['name']}”不存在选项“{value}”")
        result[target["name"]] = value
    return result


def _hashable(value: Any):
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return value


def _dedupe_key(fields: dict[str, Any], dedupe_names: list[str]):
    values = []
    for name in dedupe_names:
        value = fields.get(name)
        if value == "" or value is None:
            return None, name
        values.append(_hashable(value))
    return tuple(values), None


def build_source_plan(
    *,
    source_id: str,
    source_name: str,
    source_rows: list[dict[str, Any]],
    existing_records: list[dict[str, Any]],
    mappings: list[FieldMapping],
    dedupe_target_field_ids: list[str],
    target_fields: dict[str, dict[str, Any]],
    source_option_names: dict[str, dict[str, str]] | None = None,
) -> SourcePlan:
    plan = SourcePlan(
        source_id=source_id,
        source_name=source_name,
        read_count=len(source_rows),
        in_range_count=len(source_rows),
    )
    dedupe_names = []
    for field_id in dedupe_target_field_ids:
        target = target_fields.get(field_id)
        if target is None:
            plan.errors.append(PlanError(source_name, "配置", f"查重字段不存在: {field_id}"))
            return plan
        dedupe_names.append(target["name"])
    if not dedupe_names:
        plan.errors.append(PlanError(source_name, "配置", "请至少选择一个查重字段"))
        return plan

    existing_counts: Counter = Counter()
    for record in existing_records:
        key, missing = _dedupe_key(record.get("fields", {}), dedupe_names)
        if key is not None and missing is None:
            existing_counts[key] += 1

    for index, row in enumerate(source_rows, start=1):
        row_reference = str(row.get("_record_id") or row.get("record_id") or index)
        try:
            mapped = map_source_row(row, mappings, target_fields, source_option_names)
        except MappingError as exc:
            plan.errors.append(PlanError(source_name, row_reference, str(exc)))
            continue
        key, missing_name = _dedupe_key(mapped, dedupe_names)
        if key is None:
            plan.errors.append(
                PlanError(source_name, row_reference, f"查重字段“{missing_name}”不能为空")
            )
            continue
        if existing_counts[key] > 0:
            existing_counts[key] -= 1
            plan.skipped_count += 1
        else:
            plan.creates.append(mapped)
    return plan
