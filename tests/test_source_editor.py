import os
import sys
import unittest
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.models import FieldMapping, SourceConfig  # noqa: E402
from ui.dialogs.source_editor import SourceEditorDialog  # noqa: E402


SOURCE_FIELDS = [
    {
        "id": "src-created",
        "name": "创建时间",
        "type": 1001,
        "ui_type": "CreatedTime",
    },
    {
        "id": "src-date",
        "name": "统计时间",
        "type": 5,
        "ui_type": "DateTime",
    },
    {
        "id": "src-product",
        "name": "产品名称",
        "type": 1,
        "ui_type": "Text",
    },
    {
        "id": "src-shop",
        "name": "店铺",
        "type": 3,
        "ui_type": "SingleSelect",
    },
]

TARGET_FIELDS = [
    {
        "id": "dst-date",
        "name": "统计时间",
        "type": 5,
        "ui_type": "DateTime",
        "writable": True,
    },
    {
        "id": "dst-product",
        "name": "商品名称",
        "type": 3,
        "ui_type": "SingleSelect",
        "writable": True,
    },
    {
        "id": "dst-shop",
        "name": "店铺",
        "type": 3,
        "ui_type": "SingleSelect",
        "writable": True,
    },
    {
        "id": "dst-score",
        "name": "种草词搜索人气中位值和",
        "type": 2,
        "ui_type": "Number",
        "writable": True,
    },
    {
        "id": "dst-platform",
        "name": "平台",
        "type": 19,
        "ui_type": "Lookup",
        "writable": False,
    },
    {
        "id": "dst-formula",
        "name": "销售额",
        "type": 20,
        "ui_type": "Formula",
        "writable": False,
    },
]


class SourceEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def loaded_dialog(self, source=None):
        dialog = SourceEditorDialog(source)
        dialog.set_field_metadata(SOURCE_FIELDS, TARGET_FIELDS)
        return dialog

    def target_item_labels(self, row):
        return [
            row.target_combo.itemText(index)
            for index in range(row.target_combo.count())
        ]

    def target_item_index(self, row, field_id):
        return row.target_combo.findData(field_id)

    def target_item_is_enabled(self, row, field_id):
        index = self.target_item_index(row, field_id)
        self.assertGreaterEqual(index, 0)
        return row.target_combo.model().item(index).isEnabled()

    def test_metadata_starts_empty_and_reports_field_counts(self):
        dialog = self.loaded_dialog()

        self.assertEqual(dialog.mapping_count(), 0)
        self.assertTrue(dialog.add_mapping_button.isEnabled())
        self.assertEqual(dialog.writable_target_fields, TARGET_FIELDS[:4])
        self.assertIn("汇总表共 6 个字段", dialog.field_summary_label.text())
        self.assertIn("4 个可写", dialog.field_summary_label.text())
        self.assertIn("2 个自动生成/只读", dialog.field_summary_label.text())
        self.assertEqual(
            dialog.field_catalog_button.text(), "查看全部 6 个汇总表字段"
        )

    def test_source_name_drives_mapping_labels(self):
        dialog = self.loaded_dialog()
        dialog.source_name_edit.setText("小红书")

        row = dialog.add_mapping()

        self.assertEqual(dialog.mapping_source_heading.text(), "小红书字段或固定值")
        self.assertEqual(dialog.mapping_target_heading.text(), "汇总表字段")
        self.assertEqual(row.mode_combo.itemText(0), "取值方式：小红书字段")
        self.assertEqual(row.mode_combo.itemText(1), "取值方式：固定值")
        self.assertEqual(row.source_combo.itemText(0), "请选择小红书字段")
        self.assertEqual(row.enabled_checkbox.text(), "写入此字段")
        self.assertEqual(row.dedupe_checkbox.text(), "用于查重")

        dialog.source_name_edit.setText("得物")

        self.assertEqual(dialog.mapping_source_heading.text(), "得物字段或固定值")
        self.assertEqual(row.mode_combo.itemText(0), "取值方式：得物字段")
        self.assertEqual(row.source_combo.itemText(0), "请选择得物字段")

    def test_mapping_row_places_source_value_before_target(self):
        dialog = self.loaded_dialog()

        row = dialog.add_mapping()

        self.assertLess(
            row.top_layout.indexOf(row.value_stack),
            row.top_layout.indexOf(row.target_combo),
        )

    def test_user_adds_different_name_mapping_and_can_remove_it(self):
        dialog = self.loaded_dialog()
        row = dialog.add_mapping()
        row.select_target("dst-product")
        row.select_source("src-product")
        row.dedupe_checkbox.setChecked(True)

        mappings, dedupe = dialog.build_mappings()

        self.assertEqual(len(mappings), 1)
        self.assertEqual(mappings[0].target_field_name, "商品名称")
        self.assertEqual(mappings[0].source_field_name, "产品名称")
        self.assertEqual(dedupe, ["dst-product"])

        dialog.remove_mapping(row)
        self.assertEqual(dialog.mapping_count(), 0)
        self.assertEqual(dialog.build_mappings(), ([], []))

    def test_selected_target_stays_visible_but_disabled_in_other_rows(self):
        dialog = self.loaded_dialog()
        first = dialog.add_mapping()
        second = dialog.add_mapping()

        first.select_target("dst-product")

        self.assertIn("dst-product", first.available_target_ids())
        self.assertGreaterEqual(self.target_item_index(second, "dst-product"), 0)
        self.assertFalse(self.target_item_is_enabled(second, "dst-product"))
        self.assertIn(
            "商品名称（已用于其他映射）", self.target_item_labels(second)
        )
        self.assertIn("dst-shop", second.available_target_ids())

    def test_target_selector_shows_all_fields_and_disables_read_only(self):
        dialog = self.loaded_dialog()

        row = dialog.add_mapping()

        labels = self.target_item_labels(row)
        self.assertIn("—— 可写字段 ——", labels)
        self.assertIn("商品名称", labels)
        self.assertIn("—— 自动生成/不可写字段 ——", labels)
        self.assertIn("平台（查找引用，自动生成/不可写）", labels)
        self.assertIn("销售额（公式，自动生成/不可写）", labels)
        self.assertTrue(self.target_item_is_enabled(row, "dst-product"))
        self.assertFalse(self.target_item_is_enabled(row, "dst-platform"))
        self.assertFalse(self.target_item_is_enabled(row, "dst-formula"))

    def test_arbitrary_new_writable_target_field_is_selectable(self):
        future_field = {
            "id": "dst-future",
            "name": "未来新增指标",
            "type": 2,
            "ui_type": "Number",
            "writable": True,
        }
        dialog = SourceEditorDialog()
        dialog.set_field_metadata(SOURCE_FIELDS, TARGET_FIELDS + [future_field])

        row = dialog.add_mapping()

        self.assertIn("未来新增指标", self.target_item_labels(row))
        self.assertTrue(self.target_item_is_enabled(row, "dst-future"))

    def test_restored_missing_target_field_requires_reselection(self):
        missing_mapping = FieldMapping(
            enabled=True,
            value_mode="source",
            source_field_id="src-product",
            source_field_name="产品名称",
            target_field_id="dst-removed",
            target_field_name="已经删除的字段",
            target_field_type=1,
        )
        source = SourceConfig(
            id="source-with-missing-target",
            name="小红书",
            source_type="feishu",
            mappings=[missing_mapping],
            dedupe_target_field_ids=["dst-removed"],
        )

        dialog = self.loaded_dialog(source)
        row = dialog.mapping_rows[0]

        self.assertEqual(row.validation_error(), "原目标字段已不存在，请重新选择")

    def test_restored_target_that_became_read_only_is_rejected(self):
        read_only_mapping = FieldMapping(
            enabled=True,
            value_mode="source",
            source_field_id="src-product",
            source_field_name="产品名称",
            target_field_id="dst-platform",
            target_field_name="平台",
            target_field_type=19,
        )
        source = SourceConfig(
            id="source-with-read-only-target",
            name="小红书",
            source_type="feishu",
            mappings=[read_only_mapping],
            dedupe_target_field_ids=["dst-platform"],
        )

        dialog = self.loaded_dialog(source)
        row = dialog.mapping_rows[0]

        self.assertEqual(
            row.validation_error(), "该目标字段由飞书自动生成，不能写入"
        )

    def test_mapping_selectors_show_only_field_names_without_api_type_english(self):
        dialog = self.loaded_dialog()
        row = dialog.add_mapping()

        target_labels = [
            row.target_combo.itemText(index)
            for index in range(1, row.target_combo.count())
        ]
        source_labels = [
            row.source_combo.itemText(index)
            for index in range(1, row.source_combo.count())
        ]

        self.assertTrue(
            {"统计时间", "商品名称", "店铺", "种草词搜索人气中位值和"}.issubset(
                set(target_labels)
            )
        )
        self.assertIn("平台（查找引用，自动生成/不可写）", target_labels)
        self.assertIn("销售额（公式，自动生成/不可写）", target_labels)
        self.assertEqual(
            source_labels, ["创建时间", "统计时间", "产品名称", "店铺"]
        )
        self.assertNotIn("DateTime", " ".join(target_labels + source_labels))
        self.assertNotIn("SingleSelect", " ".join(target_labels + source_labels))
        self.assertNotIn("Text", " ".join(target_labels + source_labels))

    def test_constant_mode_serializes_only_the_fixed_value(self):
        dialog = self.loaded_dialog()
        row = dialog.add_mapping()
        row.select_target("dst-shop")
        row.mode_combo.setCurrentIndex(row.mode_combo.findData("constant"))
        row.fixed_edit.setText("小红书旗舰店")

        mapping = row.to_mapping()

        self.assertEqual(mapping.value_mode, "constant")
        self.assertEqual(mapping.constant_value, "小红书旗舰店")
        self.assertIsNone(mapping.source_field_id)
        self.assertEqual(row.value_stack.currentWidget(), row.fixed_edit)

    def test_created_time_is_automatic_and_field_date_is_selectable(self):
        dialog = self.loaded_dialog()

        self.assertEqual(dialog.filter_mode_combo.currentData(), "created_time")
        self.assertEqual(dialog.date_field_combo.currentData(), "src-created")
        self.assertFalse(dialog.date_field_combo.isEnabled())

        dialog.filter_mode_combo.setCurrentIndex(
            dialog.filter_mode_combo.findData("field_date")
        )

        self.assertTrue(dialog.date_field_combo.isEnabled())
        self.assertEqual(dialog.date_field_combo.currentData(), "src-date")

    def test_field_date_restore_keeps_the_saved_date_field(self):
        alternate_date = {
            "id": "src-date-2",
            "name": "数据日期",
            "type": 5,
            "ui_type": "DateTime",
        }
        source = SourceConfig(
            id="dewu",
            name="得物",
            source_type="feishu",
            date_filter_mode="field_date",
            date_field_id="src-date-2",
            date_field_name="数据日期",
        )
        dialog = SourceEditorDialog(source)

        dialog.set_field_metadata(SOURCE_FIELDS + [alternate_date], TARGET_FIELDS)

        self.assertEqual(dialog.date_field_combo.currentData(), "src-date-2")
        self.assertTrue(dialog.date_field_combo.isEnabled())

    def test_legacy_restore_discards_only_completely_empty_candidates(self):
        configured = FieldMapping(
            enabled=True,
            value_mode="source",
            source_field_id="src-product",
            source_field_name="产品名称",
            target_field_id="dst-product",
            target_field_name="商品名称",
            target_field_type=3,
        )
        empty_candidate = FieldMapping(
            enabled=False,
            value_mode="constant",
            source_field_id=None,
            source_field_name=None,
            target_field_id="dst-score",
            target_field_name="种草词搜索人气中位值和",
            target_field_type=2,
            constant_value="",
        )
        source = SourceConfig(
            id="xiaohongshu",
            name="小红书",
            source_type="feishu",
            date_filter_mode="created_time",
            date_field_id="src-created",
            date_field_name="创建时间",
            mappings=[configured, empty_candidate],
            dedupe_target_field_ids=["dst-product"],
        )

        dialog = self.loaded_dialog(source)

        self.assertEqual(dialog.mapping_count(), 1)
        self.assertEqual(dialog.mapping_rows[0].selected_target_id(), "dst-product")
        self.assertEqual(dialog.mapping_rows[0].selected_source_id(), "src-product")
        self.assertTrue(dialog.mapping_rows[0].dedupe_checkbox.isChecked())

    def test_field_catalog_lists_all_fields_and_read_only_status(self):
        from ui.dialogs.field_catalog import FieldCatalogDialog

        catalog = FieldCatalogDialog(TARGET_FIELDS)

        self.assertEqual(catalog.table.rowCount(), 6)
        field_types = [catalog.table.item(row, 1).text() for row in range(6)]
        statuses = [catalog.table.item(row, 2).text() for row in range(6)]
        self.assertEqual(
            field_types,
            ["日期", "单选", "单选", "数字", "查找引用", "公式"],
        )
        self.assertEqual(statuses[:4], ["可写"] * 4)
        self.assertEqual(statuses[4:], ["飞书自动生成/只读"] * 2)

    def test_validation_rejects_incomplete_rows_and_accepts_valid_mapping(self):
        dialog = self.loaded_dialog()
        row = dialog.add_mapping()

        self.assertFalse(dialog.validate_mappings())
        self.assertIn("目标字段", row.error_label.text())

        row.select_target("dst-product")
        row.select_source("src-product")
        row.dedupe_checkbox.setChecked(True)

        self.assertTrue(dialog.validate_mappings())


if __name__ == "__main__":
    unittest.main()
