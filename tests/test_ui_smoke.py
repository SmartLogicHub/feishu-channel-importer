import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QItemSelectionModel  # noqa: E402
from PySide6.QtWidgets import QApplication, QAbstractItemView, QMessageBox  # noqa: E402

from core.models import AppConfig, TargetConfig  # noqa: E402
from ui.dialogs.source_editor import SourceEditorDialog  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.pages.excel_page import ExcelPage  # noqa: E402
from ui.pages.history_page import HistoryPage  # noqa: E402
from ui.pages.source_page import SourcePage  # noqa: E402


class UiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_has_five_navigation_pages(self):
        window = MainWindow()

        self.assertEqual(window.windowTitle(), "飞书渠道数据汇总工具")
        self.assertFalse(window.windowIcon().isNull())
        self.assertEqual(window.page_stack.count(), 5)
        self.assertEqual(
            set(window.nav_buttons), {"每日同步", "来源管理", "Excel 导入", "同步记录", "设置"}
        )

    def test_daily_sync_requires_preflight_before_sync(self):
        window = MainWindow()

        self.assertFalse(window.daily_page.sync_button.isEnabled())
        self.assertTrue(window.daily_page.preflight_button.isEnabled())
        self.assertIsNotNone(window.daily_page.start_date_edit)
        self.assertIsNotNone(window.daily_page.end_date_edit)

    def test_source_editor_exposes_addable_mapping_cards(self):
        dialog = SourceEditorDialog()
        dialog.set_field_metadata(
            source_fields=[{"id": "source-product", "name": "产品名称", "type": 1}],
            target_fields=[
                {"id": "target-product", "name": "商品名称", "type": 3, "writable": True},
                {"id": "formula", "name": "平台", "type": 19, "writable": False},
            ],
        )

        self.assertEqual(dialog.mapping_count(), 0)
        self.assertTrue(dialog.add_mapping_button.isEnabled())
        row = dialog.add_mapping()
        self.assertTrue(row.enabled_checkbox.isChecked())
        self.assertEqual(dialog.filter_mode_combo.count(), 2)
        self.assertIsNotNone(dialog.source_url_edit)

    def test_source_editor_refreshes_source_and_target_fields_together(self):
        class RecordingClient:
            def __init__(self, responses):
                self.responses = responses
                self.calls = []

            def list_fields(self, app_token, table_id):
                key = (app_token, table_id)
                self.calls.append(key)
                return self.responses[key]

        source_fields = [
            {"id": "source-product", "name": "产品名称", "type": 1}
        ]
        refreshed_target_fields = [
            {
                "id": "target-future",
                "name": "未来新增指标",
                "type": 2,
                "writable": True,
            }
        ]
        client = RecordingClient(
            {
                ("source-app", "source-table"): source_fields,
                ("target-app", "target-table"): refreshed_target_fields,
            }
        )
        target_url = (
            "https://example.feishu.cn/base/target-app"
            "?table=target-table&view=target-view"
        )
        window = MainWindow()
        window.client = client
        window.app_config = AppConfig(
            target=TargetConfig(
                target_url, "target-app", "target-table", "target-view"
            )
        )
        window.target_fields = [
            {"id": "old-target", "name": "旧字段", "type": 1, "writable": True}
        ]
        dialog = SourceEditorDialog()
        dialog.source_name_edit.setText("小红书")
        dialog.source_url_edit.setText(
            "https://example.feishu.cn/base/source-app"
            "?table=source-table&view=source-view"
        )

        window._load_source_dialog_fields(dialog)

        self.assertEqual(
            client.calls,
            [
                ("source-app", "source-table"),
                ("target-app", "target-table"),
            ],
        )
        self.assertEqual(window.target_fields, refreshed_target_fields)
        self.assertEqual(dialog.source_fields, source_fields)
        self.assertEqual(dialog.target_fields, refreshed_target_fields)
        row = dialog.add_mapping()
        self.assertGreaterEqual(row.target_combo.findData("target-future"), 0)
        self.assertIn("小红书", dialog.field_summary_label.text())

    @patch("ui.main_window.save_credentials")
    @patch("ui.main_window.save_app_config")
    @patch("ui.main_window.load_credentials", return_value=None)
    @patch("ui.main_window.load_app_config", return_value=AppConfig())
    def test_saving_unchanged_target_keeps_fields_loaded_by_connection_test(
        self, _load_config, _load_credentials, _save_config, _save_credentials
    ):
        window = MainWindow()
        target_url = (
            "https://example.feishu.cn/base/app123?table=table456&view=view789"
        )
        window.settings_page.app_id_edit.setText("cli_test")
        window.settings_page.app_secret_edit.setText("secret")
        window.settings_page.target_url_edit.setText(target_url)
        window.app_config = AppConfig(
            target=TargetConfig(target_url, "app123", "table456", "view789")
        )
        loaded_fields = [{"id": "field-1", "name": "商品名称", "type": 1}]
        window.target_fields = loaded_fields

        window._save_settings()

        self.assertEqual(window.target_fields, loaded_fields)

    def test_excel_sheet_change_emits_file_and_sheet(self):
        page = ExcelPage()
        page.file_path_edit.setText("book.xlsx")
        selected = []
        page.sheet_selected.connect(lambda path, sheet: selected.append((path, sheet)))
        page.set_preview(
            {
                "headers": ["商品"],
                "rows": [["A"]],
                "sheet_names": ["第一页", "第二页"],
                "selected_sheet": "第一页",
            },
            [],
        )

        page.sheet_combo.setCurrentText("第二页")

        self.assertEqual(selected[-1], ("book.xlsx", "第二页"))

    def test_source_page_exposes_enable_toggle(self):
        page = SourcePage()

        self.assertTrue(hasattr(page, "toggle_requested"))

    def test_history_page_supports_multi_row_delete_requests(self):
        page = HistoryPage()
        page.set_history(
            [
                {"time": "2026-07-23 09:00:00", "sources": "小红书"},
                {"time": "2026-07-23 10:00:00", "sources": "得物"},
                {"time": "2026-07-23 11:00:00", "sources": "Excel 导入"},
            ]
        )

        self.assertEqual(
            page.table.selectionBehavior(),
            QAbstractItemView.SelectionBehavior.SelectRows,
        )
        self.assertEqual(
            page.table.selectionMode(),
            QAbstractItemView.SelectionMode.ExtendedSelection,
        )
        self.assertFalse(page.delete_button.isEnabled())
        self.assertTrue(page.clear_button.isEnabled())

        selection = page.table.selectionModel()
        flags = (
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows
        )
        selection.select(page.table.model().index(0, 0), flags)
        selection.select(page.table.model().index(2, 0), flags)
        requested_rows = []
        page.delete_requested.connect(requested_rows.append)

        page.delete_button.click()

        self.assertEqual(requested_rows, [[0, 2]])
        page.set_history([])
        self.assertFalse(page.delete_button.isEnabled())
        self.assertFalse(page.clear_button.isEnabled())

    @patch("ui.main_window.save_app_config")
    @patch("ui.main_window.QMessageBox.question")
    def test_deleting_selected_history_requires_confirmation(
        self, question, save_config
    ):
        history = [
            {"time": "第一条"},
            {"time": "第二条"},
            {"time": "第三条"},
        ]
        window = MainWindow()
        window.app_config = AppConfig(history=history)
        window.history_page.set_history(history)
        question.return_value = QMessageBox.StandardButton.No

        window._delete_history_rows([0, 2])

        self.assertEqual(window.app_config.history, history)
        save_config.assert_not_called()

        question.return_value = QMessageBox.StandardButton.Yes
        window._delete_history_rows([0, 2])

        self.assertEqual(window.app_config.history, [{"time": "第二条"}])
        self.assertEqual(window.history_page.table.rowCount(), 1)
        save_config.assert_called_once_with(window.app_config)

    @patch("ui.main_window.save_app_config")
    @patch("ui.main_window.QMessageBox.question")
    def test_clearing_history_only_changes_local_history(
        self, question, save_config
    ):
        target = TargetConfig("目标链接", "app", "table", "view")
        history = [{"time": "第一条"}, {"time": "第二条"}]
        window = MainWindow()
        window.app_config = AppConfig(target=target, history=history)
        window.history_page.set_history(history)
        question.return_value = QMessageBox.StandardButton.Yes

        window._clear_history()

        self.assertEqual(window.app_config.history, [])
        self.assertEqual(window.app_config.target, target)
        self.assertEqual(window.history_page.table.rowCount(), 0)
        save_config.assert_called_once_with(window.app_config)
        confirmation_text = question.call_args.args[2]
        self.assertIn("不会删除或更改飞书", confirmation_text)


if __name__ == "__main__":
    unittest.main()
