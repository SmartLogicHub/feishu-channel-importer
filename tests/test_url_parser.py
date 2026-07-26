import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.url_parser import parse_bitable_url  # noqa: E402


class BitableUrlParserTests(unittest.TestCase):
    def test_parses_base_table_and_view_from_full_url(self):
        result = parse_bitable_url(
            "https://example.feishu.cn/base/app123?view=view789&table=table456"
        )

        self.assertEqual(result.app_token, "app123")
        self.assertEqual(result.table_id, "table456")
        self.assertEqual(result.view_id, "view789")

    def test_accepts_query_parameters_in_any_order(self):
        result = parse_bitable_url(
            "https://example.feishu.cn/base/app123?table=table456&view=view789"
        )

        self.assertEqual((result.table_id, result.view_id), ("table456", "view789"))

    def test_accepts_plain_app_token(self):
        result = parse_bitable_url("appTokenExample1234567890")

        self.assertEqual(result.app_token, "appTokenExample1234567890")
        self.assertIsNone(result.table_id)
        self.assertIsNone(result.view_id)

    def test_rejects_empty_or_unrecognized_url(self):
        for value in ("", "https://example.com/not-a-base/value", "contains spaces"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_bitable_url(value)


if __name__ == "__main__":
    unittest.main()
