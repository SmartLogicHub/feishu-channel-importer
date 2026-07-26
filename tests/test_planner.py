import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.models import FieldMapping  # noqa: E402
from core.planner import MappingError, build_source_plan, map_source_row  # noqa: E402


TARGET_FIELDS = {
    "date": {"id": "date", "name": "统计时间", "type": 5, "writable": True},
    "product": {
        "id": "product",
        "name": "商品名称",
        "type": 3,
        "writable": True,
        "options": {"Atom CC", "Atom Max"},
    },
    "store": {
        "id": "store",
        "name": "店铺",
        "type": 3,
        "writable": True,
        "options": {"得物-测试店"},
    },
    "visitors": {
        "id": "visitors",
        "name": "商品访客数",
        "type": 2,
        "writable": True,
    },
    "formula": {
        "id": "formula",
        "name": "平台",
        "type": 19,
        "writable": False,
    },
}


def enabled_mappings():
    return [
        FieldMapping(
            enabled=True,
            value_mode="source",
            source_field_id="source-date",
            source_field_name="数据日期",
            target_field_id="date",
            target_field_name="统计时间",
            target_field_type=5,
        ),
        FieldMapping(
            enabled=True,
            value_mode="source",
            source_field_id="source-product",
            source_field_name="产品名称",
            target_field_id="product",
            target_field_name="商品名称",
            target_field_type=3,
        ),
        FieldMapping(
            enabled=True,
            value_mode="constant",
            target_field_id="store",
            target_field_name="店铺",
            target_field_type=3,
            constant_value="得物-测试店",
        ),
        FieldMapping(
            enabled=False,
            value_mode="source",
            source_field_name="访客数",
            target_field_id="visitors",
            target_field_name="商品访客数",
            target_field_type=2,
        ),
    ]


class MappingTests(unittest.TestCase):
    def test_maps_different_names_constant_and_only_enabled_fields(self):
        row = {
            "数据日期": "2026-06-11",
            "产品名称": "Atom CC",
            "访客数": 99,
            "支付金额": 100,
        }

        mapped = map_source_row(row, enabled_mappings(), TARGET_FIELDS)

        self.assertEqual(
            mapped,
            {
                "统计时间": 1781107200000,
                "商品名称": "Atom CC",
                "店铺": "得物-测试店",
            },
        )

    def test_blocks_read_only_target_field(self):
        mapping = FieldMapping(
            enabled=True,
            value_mode="constant",
            target_field_id="formula",
            target_field_name="平台",
            target_field_type=19,
            constant_value="得物",
        )

        with self.assertRaisesRegex(MappingError, "只读"):
            map_source_row({}, [mapping], TARGET_FIELDS)

    def test_blocks_unknown_single_select_option(self):
        row = {"产品名称": "新商品"}
        mapping = enabled_mappings()[1]

        with self.assertRaisesRegex(MappingError, "新商品"):
            map_source_row(row, [mapping], TARGET_FIELDS)


class DedupePlanningTests(unittest.TestCase):
    def test_existing_duplicate_count_offsets_only_same_number_of_source_rows(self):
        row = {"数据日期": "2026-06-11", "产品名称": "Atom CC"}
        mapped = map_source_row(row, enabled_mappings(), TARGET_FIELDS)
        plan = build_source_plan(
            source_id="dewu",
            source_name="得物",
            source_rows=[row.copy(), row.copy()],
            existing_records=[{"record_id": "existing-1", "fields": mapped}],
            mappings=enabled_mappings(),
            dedupe_target_field_ids=["date", "product", "store"],
            target_fields=TARGET_FIELDS,
        )

        self.assertEqual(plan.skipped_count, 1)
        self.assertEqual(plan.creates, [mapped])
        self.assertEqual(plan.errors, [])

    def test_empty_dedupe_value_becomes_blocking_row_error(self):
        mappings = enabled_mappings()
        mappings[1] = FieldMapping(
            enabled=True,
            value_mode="source",
            source_field_name="产品名称",
            target_field_id="product",
            target_field_name="商品名称",
            target_field_type=3,
        )
        plan = build_source_plan(
            source_id="dewu",
            source_name="得物",
            source_rows=[{"数据日期": "2026-06-11", "产品名称": ""}],
            existing_records=[],
            mappings=mappings,
            dedupe_target_field_ids=["date", "product", "store"],
            target_fields=TARGET_FIELDS,
        )

        self.assertEqual(plan.creates, [])
        self.assertEqual(len(plan.errors), 1)
        self.assertIn("商品名称", plan.errors[0].message)


if __name__ == "__main__":
    unittest.main()
