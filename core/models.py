"""Serializable configuration and synchronization models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TargetConfig:
    url: str
    app_token: str
    table_id: str
    view_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TargetConfig":
        return cls(**data)


@dataclass(frozen=True)
class FieldMapping:
    enabled: bool
    value_mode: str
    target_field_id: str
    target_field_name: str
    target_field_type: int
    source_field_id: str | None = None
    source_field_name: str | None = None
    excel_column: str | None = None
    constant_value: Any = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FieldMapping":
        return cls(**data)


@dataclass(frozen=True)
class SourceConfig:
    id: str
    name: str
    source_type: str
    enabled: bool = True
    url: str = ""
    app_token: str = ""
    table_id: str = ""
    view_id: str | None = None
    date_filter_mode: str = "created_time"
    date_field_id: str | None = None
    date_field_name: str | None = None
    excel_sheet_name: str | None = None
    mappings: list[FieldMapping] = field(default_factory=list)
    dedupe_target_field_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceConfig":
        values = dict(data)
        values["mappings"] = [
            FieldMapping.from_dict(item) for item in values.get("mappings", [])
        ]
        return cls(**values)


@dataclass(frozen=True)
class AppConfig:
    schema_version: int = 1
    target: TargetConfig | None = None
    sources: list[SourceConfig] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        target_data = data.get("target")
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            target=TargetConfig.from_dict(target_data) if target_data else None,
            sources=[SourceConfig.from_dict(item) for item in data.get("sources", [])],
            history=list(data.get("history", [])),
        )


@dataclass(frozen=True)
class PlanError:
    source_name: str
    row_reference: str
    message: str


@dataclass
class SourcePlan:
    source_id: str
    source_name: str
    read_count: int = 0
    in_range_count: int = 0
    skipped_count: int = 0
    creates: list[dict[str, Any]] = field(default_factory=list)
    errors: list[PlanError] = field(default_factory=list)


@dataclass
class PreflightResult:
    token: str
    signature: str
    created_at_ms: int
    plans: list[SourcePlan] = field(default_factory=list)

    @property
    def has_blocking_errors(self) -> bool:
        return any(plan.errors for plan in self.plans)


@dataclass
class SyncResult:
    created_count: int = 0
    skipped_count: int = 0
    failed_sources: list[str] = field(default_factory=list)
    verified: bool = False
