import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.importer import run_import  # noqa: E402


class LegacyImporterCompatibilityTests(unittest.TestCase):
    @patch("core.importer.FeishuClient")
    @patch("core.importer.read_excel_all")
    def test_run_import_normalizes_values_and_uses_current_batch_api(
        self, read_excel_all, client_class
    ):
        read_excel_all.return_value = [
            {"日期": "46184", "商品": "Atom CC", "未映射": "不应写入"}
        ]
        client = client_class.return_value
        client.batch_create_records.return_value = 1

        created = run_import(
            "source.xlsx",
            "Sheet1",
            "cli_test",
            "secret",
            "app_token",
            "table_id",
            {"日期": "统计时间", "商品": "商品名称"},
            field_types={"统计时间": 5, "商品名称": 1},
        )

        self.assertEqual(created, 1)
        client.batch_create_records.assert_called_once_with(
            "app_token",
            "table_id",
            [{"统计时间": 1781107200000, "商品名称": "Atom CC"}],
        )


if __name__ == "__main__":
    unittest.main()
