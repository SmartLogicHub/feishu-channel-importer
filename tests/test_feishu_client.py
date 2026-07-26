import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.feishu_client import FeishuApiError, FeishuClient  # noqa: E402


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payloads):
        self.responses = [FakeResponse(payload) for payload in payloads]
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError("Unexpected request")
        return self.responses.pop(0)


TOKEN = {"code": 0, "tenant_access_token": "tenant-token"}


class FeishuClientContractTests(unittest.TestCase):
    def test_lists_all_record_pages_with_view_and_selected_fields(self):
        session = FakeSession(
            [
                TOKEN,
                {
                    "code": 0,
                    "data": {
                        "items": [{"record_id": "r1", "fields": {}}],
                        "has_more": True,
                        "page_token": "next",
                    },
                },
                {
                    "code": 0,
                    "data": {
                        "items": [{"record_id": "r2", "fields": {}}],
                        "has_more": False,
                    },
                },
            ]
        )
        client = FeishuClient("app-id", "secret-value", session=session)

        records = client.list_records(
            "app-token", "table-id", view_id="view-id", field_names=["商品名称"]
        )

        self.assertEqual([item["record_id"] for item in records], ["r1", "r2"])
        first_params = session.calls[1][2]["params"]
        self.assertEqual(first_params["view_id"], "view-id")
        self.assertIn("商品名称", first_params["field_names"])
        self.assertEqual(session.calls[2][2]["params"]["page_token"], "next")
        self.assertTrue(all(call[2].get("timeout") for call in session.calls))

    def test_batch_create_splits_1001_rows_into_500_500_1(self):
        session = FakeSession([TOKEN] + [{"code": 0, "data": {}}] * 3)
        client = FeishuClient("app-id", "secret-value", session=session)
        records = [{"商品名称": f"商品-{index}"} for index in range(1001)]

        written = client.batch_create_records("app-token", "table-id", records)

        self.assertEqual(written, 1001)
        sizes = [len(call[2]["json"]["records"]) for call in session.calls[1:]]
        self.assertEqual(sizes, [500, 500, 1])

    def test_resolves_lookup_options_from_referenced_table_field(self):
        session = FakeSession(
            [
                TOKEN,
                {
                    "code": 0,
                    "data": {
                        "items": [
                            {
                                "field_id": "target-field",
                                "field_name": "平台",
                                "type": 3,
                                "property": {
                                    "options": [
                                        {"id": "optA", "name": "小红书"},
                                        {"id": "optB", "name": "得物"},
                                    ]
                                },
                            }
                        ],
                        "has_more": False,
                    },
                },
            ]
        )
        client = FeishuClient("app-id", "secret-value", session=session)
        lookup = {
            "type": 19,
            "property": {
                "filter_info": {"target_table": "lookup-table"},
                "target_field": "target-field",
            },
        }

        options = client.resolve_lookup_options("app-token", lookup)

        self.assertEqual(options, {"optA": "小红书", "optB": "得物"})

    def test_field_metadata_accepts_null_property(self):
        session = FakeSession(
            [
                TOKEN,
                {
                    "code": 0,
                    "data": {
                        "items": [
                            {
                                "field_id": "plain-text",
                                "field_name": "备注",
                                "type": 1,
                                "property": None,
                            }
                        ],
                        "has_more": False,
                    },
                },
            ]
        )
        client = FeishuClient("app-id", "secret-value", session=session)

        fields = client.list_fields("app-token", "table-id")

        self.assertEqual(fields[0]["property"], {})
        self.assertEqual(fields[0]["options"], {})

    def test_api_error_does_not_disclose_credentials_or_token(self):
        session = FakeSession([TOKEN, {"code": 999, "msg": "request failed"}])
        client = FeishuClient("app-id", "secret-value", session=session)

        with self.assertRaises(FeishuApiError) as raised:
            client.list_tables("app-token")

        message = str(raised.exception)
        self.assertNotIn("secret-value", message)
        self.assertNotIn("tenant-token", message)
        self.assertNotIn("Authorization", message)


if __name__ == "__main__":
    unittest.main()
