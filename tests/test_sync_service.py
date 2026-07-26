import sys
import unittest
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.models import FieldMapping, SourceConfig, TargetConfig  # noqa: E402
from core.sync_service import InvalidPreflightError, SyncService  # noqa: E402
from core.value_normalizer import created_time_range  # noqa: E402


TARGET_FIELDS = [
    {"id": "date", "name": "统计时间", "type": 5, "writable": True, "options": {}},
    {
        "id": "product",
        "name": "商品名称",
        "type": 3,
        "writable": True,
        "options": {"optA": "Atom CC"},
    },
    {
        "id": "store",
        "name": "店铺",
        "type": 3,
        "writable": True,
        "options": {"optStore": "小红书-测试店"},
    },
]

SOURCE_FIELDS = [
    {"id": "created", "name": "创建时间", "type": 1001, "writable": False, "options": {}},
    {"id": "source-date", "name": "统计时间", "type": 5, "writable": True, "options": {}},
    {"id": "source-product", "name": "商品名称", "type": 1, "writable": True, "options": {}},
]


def source_config(source_id="source", table_id="source-table"):
    return SourceConfig(
        id=source_id,
        name=source_id,
        source_type="feishu",
        app_token="app",
        table_id=table_id,
        view_id="view",
        date_filter_mode="created_time",
        date_field_id="created",
        date_field_name="创建时间",
        mappings=[
            FieldMapping(True, "source", "date", "统计时间", 5, "source-date", "统计时间"),
            FieldMapping(True, "source", "product", "商品名称", 3, "source-product", "商品名称"),
            FieldMapping(True, "constant", "store", "店铺", 3, constant_value="小红书-测试店"),
        ],
        dedupe_target_field_ids=["date", "product", "store"],
    )


class FakeClient:
    def __init__(self, source_records=None, fail_tables=None):
        self.records = {
            "target-table": [],
            "source-table": list(source_records or []),
            "good-table": list(source_records or []),
        }
        self.fail_tables = set(fail_tables or [])
        self.writes = []

    def list_fields(self, app_token, table_id):
        if table_id in self.fail_tables:
            raise RuntimeError("read failed")
        return TARGET_FIELDS if table_id == "target-table" else SOURCE_FIELDS

    def list_records(self, app_token, table_id, **kwargs):
        if table_id in self.fail_tables:
            raise RuntimeError("read failed")
        return list(self.records.get(table_id, []))

    def resolve_lookup_options(self, app_token, field_metadata):
        return dict(field_metadata.get("options", {}))

    def batch_create_records(self, app_token, table_id, records):
        self.writes.extend(records)
        self.records.setdefault(table_id, []).extend(
            {"record_id": f"new-{index}", "fields": dict(fields)}
            for index, fields in enumerate(records, start=1)
        )
        return len(records)


TARGET = TargetConfig("url", "app", "target-table", "summary")


class SyncServiceTests(unittest.TestCase):
    def test_filters_feishu_source_by_created_time_half_open_range(self):
        start_ms, end_ms = created_time_range(date(2026, 7, 20), date(2026, 7, 23))
        rows = [
            {"record_id": "before", "fields": {"创建时间": start_ms - 1, "统计时间": "2026-07-19", "商品名称": "Atom CC"}},
            {"record_id": "start", "fields": {"创建时间": start_ms, "统计时间": "2026-07-20", "商品名称": "Atom CC"}},
            {"record_id": "last", "fields": {"创建时间": end_ms - 1, "统计时间": "2026-07-23", "商品名称": "Atom CC"}},
            {"record_id": "after", "fields": {"创建时间": end_ms, "统计时间": "2026-07-24", "商品名称": "Atom CC"}},
        ]
        service = SyncService(FakeClient(rows))

        result = service.preflight(TARGET, [source_config()], date(2026, 7, 20), date(2026, 7, 23))

        plan = result.plans[0]
        self.assertEqual(plan.read_count, 4)
        self.assertEqual(plan.in_range_count, 2)
        self.assertEqual(len(plan.creates), 2)

    def test_saved_field_ids_survive_source_field_renames(self):
        start_ms, _ = created_time_range(date(2026, 7, 23), date(2026, 7, 23))

        class RenamedClient(FakeClient):
            def list_fields(self, app_token, table_id):
                if table_id == "target-table":
                    return TARGET_FIELDS
                return [
                    {"id": "created", "name": "创建日期", "type": 1001, "writable": False, "options": {}},
                    {"id": "source-date", "name": "数据日期", "type": 5, "writable": True, "options": {}},
                    {"id": "source-product", "name": "产品标题", "type": 1, "writable": True, "options": {}},
                ]

        rows = [{"record_id": "ok", "fields": {"创建日期": start_ms, "数据日期": "2026-07-23", "产品标题": "Atom CC"}}]
        service = SyncService(RenamedClient(rows))

        result = service.preflight(TARGET, [source_config()], date(2026, 7, 23), date(2026, 7, 23))

        self.assertEqual(result.plans[0].in_range_count, 1)
        self.assertEqual(len(result.plans[0].creates), 1)

    def test_one_source_failure_does_not_discard_other_source_plan(self):
        start_ms, _ = created_time_range(date(2026, 7, 23), date(2026, 7, 23))
        rows = [{"record_id": "ok", "fields": {"创建时间": start_ms, "统计时间": "2026-07-23", "商品名称": "Atom CC"}}]
        client = FakeClient(rows, fail_tables={"bad-table"})
        service = SyncService(client)

        result = service.preflight(
            TARGET,
            [source_config("good", "good-table"), source_config("bad", "bad-table")],
            date(2026, 7, 23),
            date(2026, 7, 23),
        )

        self.assertEqual(len(result.plans[0].creates), 1)
        self.assertEqual(len(result.plans[1].errors), 1)

    def test_later_source_sees_rows_planned_by_earlier_source(self):
        start_ms, _ = created_time_range(date(2026, 7, 23), date(2026, 7, 23))
        rows = [{"record_id": "ok", "fields": {"创建时间": start_ms, "统计时间": "2026-07-23", "商品名称": "Atom CC"}}]
        client = FakeClient(rows)
        client.records["second-table"] = list(rows)
        service = SyncService(client)

        result = service.preflight(
            TARGET,
            [source_config("first", "source-table"), source_config("second", "second-table")],
            date(2026, 7, 23),
            date(2026, 7, 23),
        )

        self.assertEqual(len(result.plans[0].creates), 1)
        self.assertEqual(result.plans[1].skipped_count, 1)
        self.assertEqual(result.plans[1].creates, [])

    def test_config_change_invalidation_blocks_old_preflight(self):
        service = SyncService(FakeClient([]))
        result = service.preflight(TARGET, [source_config()], date(2026, 7, 23), date(2026, 7, 23))
        service.invalidate_preflight()

        with self.assertRaises(InvalidPreflightError):
            service.apply(result.token)

    def test_apply_writes_missing_rows_and_verifies_target(self):
        start_ms, _ = created_time_range(date(2026, 7, 23), date(2026, 7, 23))
        rows = [{"record_id": "ok", "fields": {"创建时间": start_ms, "统计时间": "2026-07-23", "商品名称": "Atom CC"}}]
        client = FakeClient(rows)
        service = SyncService(client)
        preflight = service.preflight(TARGET, [source_config()], date(2026, 7, 23), date(2026, 7, 23))

        result = service.apply(preflight.token)

        self.assertEqual(result.created_count, 1)
        self.assertTrue(result.verified)
        self.assertEqual(len(client.writes), 1)


if __name__ == "__main__":
    unittest.main()
