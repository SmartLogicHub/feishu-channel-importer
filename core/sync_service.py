"""Orchestrate source reads, date filtering, preflight planning and writes."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections import Counter
from dataclasses import asdict
from datetime import date
from typing import Any

from .excel_reader import read_excel_all
from .models import (
    PlanError,
    PreflightResult,
    SourceConfig,
    SourcePlan,
    SyncResult,
    TargetConfig,
)
from .planner import build_source_plan
from .value_normalizer import (
    NormalizationError,
    created_time_range,
    normalize_for_target,
    resolve_display_value,
    to_feishu_date_ms,
)


class InvalidPreflightError(RuntimeError):
    """Raised when a stale or unknown preflight token is used."""


def _canonical(value: Any):
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return value


class SyncService:
    def __init__(self, client):
        self.client = client
        self._snapshot: dict[str, Any] | None = None

    def invalidate_preflight(self):
        self._snapshot = None

    def _signature(
        self,
        target: TargetConfig,
        sources: list[SourceConfig],
        start_date: date,
        end_date: date,
    ) -> str:
        payload = {
            "target": asdict(target),
            "sources": [asdict(source) for source in sources],
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _target_field_map(fields: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {field["id"]: field for field in fields}

    @staticmethod
    def _normalize_existing_records(
        records: list[dict[str, Any]], target_fields: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        by_name = {field["name"]: field for field in target_fields}
        normalized = []
        for record in records:
            fields = {}
            for name, value in record.get("fields", {}).items():
                metadata = by_name.get(name)
                if metadata is None:
                    continue
                try:
                    fields[name] = normalize_for_target(
                        value,
                        int(metadata["type"]),
                        option_names=metadata.get("options") or None,
                    )
                except NormalizationError:
                    fields[name] = resolve_display_value(value)
            normalized.append({"record_id": record.get("record_id"), "fields": fields})
        return normalized

    def _read_source_rows(
        self,
        source: SourceConfig,
        start_ms: int,
        end_ms: int,
    ) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]], dict[str, dict[str, str]]]:
        if source.source_type == "excel":
            raw_rows = read_excel_all(source.url, sheet_name=source.excel_sheet_name)
            source_fields: list[dict[str, Any]] = []
            option_names: dict[str, dict[str, str]] = {}
            rows = [dict(row) for row in raw_rows]
        elif source.source_type == "feishu":
            source_fields = self.client.list_fields(source.app_token, source.table_id)
            by_id = {field["id"]: field for field in source_fields}
            wanted_names = set()
            for mapping in source.mappings:
                if not mapping.enabled or mapping.value_mode != "source":
                    continue
                current = by_id.get(mapping.source_field_id or "")
                name = current["name"] if current else mapping.source_field_name
                if name:
                    wanted_names.add(name)
            current_date_field = by_id.get(source.date_field_id or "")
            current_date_name = (
                current_date_field["name"] if current_date_field else source.date_field_name
            )
            if current_date_name:
                wanted_names.add(current_date_name)
            records = self.client.list_records(
                source.app_token,
                source.table_id,
                view_id=source.view_id,
                field_names=sorted(wanted_names),
            )
            rows = []
            for record in records:
                row = dict(record.get("fields", {}))
                for field in source_fields:
                    if field["name"] in row:
                        row[field["id"]] = row[field["name"]]
                row["_record_id"] = record.get("record_id")
                rows.append(row)
            option_names = {}
            for mapping in source.mappings:
                if not mapping.enabled or not mapping.source_field_id:
                    continue
                metadata = by_id.get(mapping.source_field_id)
                if metadata and int(metadata["type"]) in (3, 19):
                    option_names[mapping.source_field_id] = self.client.resolve_lookup_options(
                        source.app_token, metadata
                    )
        else:
            raise ValueError(f"不支持的来源类型: {source.source_type}")

        read_count = len(rows)
        date_key = source.date_field_id or source.date_field_name
        if not date_key:
            return rows, read_count, source_fields, option_names

        filtered = []
        for row in rows:
            value = row.get(date_key)
            if value in (None, ""):
                continue
            try:
                timestamp = int(value) if source.date_filter_mode == "created_time" else to_feishu_date_ms(value)
            except (TypeError, ValueError, NormalizationError):
                continue
            if start_ms <= timestamp < end_ms:
                filtered.append(row)
        return filtered, read_count, source_fields, option_names

    def preflight(
        self,
        target: TargetConfig,
        sources: list[SourceConfig],
        start_date: date,
        end_date: date,
    ) -> PreflightResult:
        start_ms, end_ms = created_time_range(start_date, end_date)
        target_fields = self.client.list_fields(target.app_token, target.table_id)
        target_map = self._target_field_map(target_fields)
        needed_target_names = {
            target_map[field_id]["name"]
            for source in sources
            for field_id in source.dedupe_target_field_ids
            if field_id in target_map
        }
        existing_raw = self.client.list_records(
            target.app_token,
            target.table_id,
            field_names=sorted(needed_target_names),
        )
        existing = self._normalize_existing_records(existing_raw, target_fields)

        plans: list[SourcePlan] = []
        for source in sources:
            if not source.enabled:
                continue
            try:
                rows, read_count, _, option_names = self._read_source_rows(
                    source, start_ms, end_ms
                )
                plan = build_source_plan(
                    source_id=source.id,
                    source_name=source.name,
                    source_rows=rows,
                    existing_records=existing,
                    mappings=source.mappings,
                    dedupe_target_field_ids=source.dedupe_target_field_ids,
                    target_fields=target_map,
                    source_option_names=option_names,
                )
                plan.read_count = read_count
                plan.in_range_count = len(rows)
                if not plan.errors:
                    existing.extend(
                        {"record_id": None, "fields": dict(record)}
                        for record in plan.creates
                    )
            except Exception as exc:
                plan = SourcePlan(source.id, source.name)
                plan.errors.append(PlanError(source.name, "来源", str(exc)))
            plans.append(plan)

        signature = self._signature(target, sources, start_date, end_date)
        result = PreflightResult(
            token=uuid.uuid4().hex,
            signature=signature,
            created_at_ms=int(time.time() * 1000),
            plans=plans,
        )
        self._snapshot = {
            "result": result,
            "target": target,
            "sources": sources,
            "start_date": start_date,
            "end_date": end_date,
            "target_fields": target_fields,
        }
        return result

    @staticmethod
    def _record_counter(records: list[dict[str, Any]], field_names: set[str]) -> Counter:
        counter = Counter()
        for record in records:
            fields = record.get("fields", {})
            key = tuple((name, _canonical(fields.get(name))) for name in sorted(field_names))
            counter[key] += 1
        return counter

    def apply(self, preflight_token: str, progress_callback=None) -> SyncResult:
        if not self._snapshot or self._snapshot["result"].token != preflight_token:
            raise InvalidPreflightError("预检结果已失效，请重新预检")
        preflight: PreflightResult = self._snapshot["result"]
        target: TargetConfig = self._snapshot["target"]
        result = SyncResult(
            skipped_count=sum(plan.skipped_count for plan in preflight.plans),
            failed_sources=[plan.source_name for plan in preflight.plans if plan.errors],
        )
        writable_plans = [plan for plan in preflight.plans if not plan.errors]
        total = sum(len(plan.creates) for plan in writable_plans)
        current = 0
        for plan in writable_plans:
            if progress_callback:
                progress_callback(current, total, f"正在同步：{plan.source_name}")
            created = self.client.batch_create_records(
                target.app_token, target.table_id, plan.creates
            )
            current += created
            result.created_count += created

        expected_records = [record for plan in writable_plans for record in plan.creates]
        if not expected_records:
            result.verified = True
        else:
            field_names = {name for record in expected_records for name in record}
            target_fields = self._snapshot["target_fields"]
            actual_raw = self.client.list_records(
                target.app_token, target.table_id, field_names=sorted(field_names)
            )
            actual = self._normalize_existing_records(actual_raw, target_fields)
            expected_counter = self._record_counter(
                [{"fields": record} for record in expected_records], field_names
            )
            actual_counter = self._record_counter(actual, field_names)
            result.verified = all(
                actual_counter[key] >= count for key, count in expected_counter.items()
            )
        if progress_callback:
            progress_callback(current, total, "同步完成，已完成写后核对")
        self.invalidate_preflight()
        return result
