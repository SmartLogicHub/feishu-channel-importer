"""Small, testable wrapper around the Feishu Open Platform REST API."""
from __future__ import annotations

import json
from typing import Any

import requests


BASE_URL = "https://open.feishu.cn/open-apis"
READ_ONLY_FIELD_TYPES = {19, 20, 21, 1001, 1002, 1003, 1004}


class FeishuApiError(RuntimeError):
    """A sanitized Feishu API failure safe to show in the UI."""


class FeishuClient:
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        *,
        session=None,
        timeout: tuple[int, int] = (10, 45),
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.session = session or requests.Session()
        self.timeout = timeout
        self._token: str | None = None

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if authenticated:
            headers["Authorization"] = f"Bearer {self._get_token()}"
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        try:
            response = self.session.request(
                method,
                f"{BASE_URL}{path}",
                headers=headers,
                params=params or {},
                json=json_body,
                timeout=self.timeout,
            )
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise FeishuApiError(f"无法连接飞书 API [{path}]") from exc
        if response.status_code >= 400 or data.get("code", 0) != 0:
            message = data.get("msg") or f"HTTP {response.status_code}"
            raise FeishuApiError(f"飞书 API 请求失败 [{path}]: {message}")
        return data

    def _get_token(self) -> str:
        if self._token:
            return self._token
        data = self._request(
            "POST",
            "/auth/v3/tenant_access_token/internal",
            json_body={"app_id": self.app_id, "app_secret": self.app_secret},
            authenticated=False,
        )
        token = data.get("tenant_access_token")
        if not token:
            raise FeishuApiError("飞书未返回 tenant_access_token")
        self._token = token
        return token

    def _get(self, path: str, params: dict | None = None) -> dict:
        return self._request("GET", path, params=params)

    def _post(self, path: str, body: dict) -> dict:
        return self._request("POST", path, json_body=body)

    def _paginate_items(
        self, path: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        base_params = dict(params or {})
        items: list[dict[str, Any]] = []
        page_token = None
        while True:
            page_params = dict(base_params)
            if page_token:
                page_params["page_token"] = page_token
            data = self._get(path, page_params).get("data", {})
            items.extend(data.get("items", []))
            if not data.get("has_more"):
                return items
            page_token = data.get("page_token")
            if not page_token:
                raise FeishuApiError("飞书分页结果缺少 page_token")

    def list_spreadsheets(self, page_token: str | None = None):
        params: dict[str, Any] = {"page_size": 100, "type": "bitable"}
        if page_token:
            params["page_token"] = page_token
        data = self._get("/drive/v1/files", params).get("data", {})
        items = [
            {"name": item["name"], "token": item["token"]}
            for item in data.get("files", [])
        ]
        return items, data.get("page_token")

    def list_tables(self, app_token: str) -> list[dict[str, Any]]:
        items = self._paginate_items(
            f"/bitable/v1/apps/{app_token}/tables", {"page_size": 100}
        )
        return [{"name": item["name"], "id": item["table_id"]} for item in items]

    def list_views(self, app_token: str, table_id: str) -> list[dict[str, Any]]:
        items = self._paginate_items(
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/views",
            {"page_size": 100},
        )
        return [{"name": item["view_name"], "id": item["view_id"]} for item in items]

    def list_fields(self, app_token: str, table_id: str) -> list[dict[str, Any]]:
        items = self._paginate_items(
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            {"page_size": 100},
        )
        fields = []
        for item in items:
            property_data = item.get("property") or {}
            options = {
                option["id"]: option["name"]
                for option in property_data.get("options", [])
            }
            fields.append(
                {
                    "name": item["field_name"],
                    "id": item["field_id"],
                    "type": item["type"],
                    "ui_type": item.get("ui_type", ""),
                    "property": property_data,
                    "options": options,
                    "writable": item["type"] not in READ_ONLY_FIELD_TYPES,
                }
            )
        return fields

    def list_records(
        self,
        app_token: str,
        table_id: str,
        *,
        view_id: str | None = None,
        field_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"page_size": 500}
        if view_id:
            params["view_id"] = view_id
        if field_names:
            params["field_names"] = json.dumps(field_names, ensure_ascii=False)
        return self._paginate_items(
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records", params
        )

    def resolve_lookup_options(
        self, app_token: str, field_metadata: dict[str, Any]
    ) -> dict[str, str]:
        if int(field_metadata.get("type", 0)) == 3:
            options = field_metadata.get("options")
            if isinstance(options, dict):
                return dict(options)
            return {
                option["id"]: option["name"]
                for option in field_metadata.get("property", {}).get("options", [])
            }
        if int(field_metadata.get("type", 0)) != 19:
            return {}
        property_data = field_metadata.get("property", {})
        target_table = property_data.get("filter_info", {}).get("target_table")
        target_field = property_data.get("target_field")
        if not target_table or not target_field:
            return {}
        referenced = next(
            (field for field in self.list_fields(app_token, target_table) if field["id"] == target_field),
            None,
        )
        return dict(referenced.get("options", {})) if referenced else {}

    def batch_create_records(
        self, app_token: str, table_id: str, records: list[dict[str, Any]]
    ) -> int:
        total = 0
        for start in range(0, len(records), 500):
            batch = records[start : start + 500]
            body = {"records": [{"fields": fields} for fields in batch]}
            self._post(
                f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
                body,
            )
            total += len(batch)
        return total

    def create_table(
        self, app_token: str, table_name: str, fields_config: list[dict[str, Any]]
    ) -> dict[str, str]:
        body = {
            "table": {
                "name": table_name,
                "default_view_name": "默认视图",
                "fields": [
                    {"field_name": item["field_name"], "type": item["type"]}
                    for item in fields_config
                ],
            }
        }
        data = self._post(f"/bitable/v1/apps/{app_token}/tables", body)
        return {"table_id": data["data"]["table_id"]}
