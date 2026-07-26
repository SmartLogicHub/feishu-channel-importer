import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config_manager import load_app_config, save_app_config  # noqa: E402
from core.models import (  # noqa: E402
    AppConfig,
    FieldMapping,
    SourceConfig,
    TargetConfig,
)


class AppConfigTests(unittest.TestCase):
    def test_round_trips_target_sources_and_mappings_without_secret(self):
        config = AppConfig(
            target=TargetConfig(
                url="https://example.feishu.cn/base/app?table=target&view=summary",
                app_token="app",
                table_id="target",
                view_id="summary",
            ),
            sources=[
                SourceConfig(
                    id="source-1",
                    name="得物",
                    source_type="feishu",
                    url="https://example.feishu.cn/base/app?table=source&view=daily",
                    app_token="app",
                    table_id="source",
                    view_id="daily",
                    date_filter_mode="created_time",
                    mappings=[
                        FieldMapping(
                            enabled=True,
                            value_mode="source",
                            source_field_id="product",
                            source_field_name="产品名称",
                            target_field_id="target-product",
                            target_field_name="商品名称",
                            target_field_type=3,
                        )
                    ],
                    dedupe_target_field_ids=["target-product"],
                )
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            save_app_config(config, path)
            loaded = load_app_config(path)
            raw_text = path.read_text(encoding="utf-8")

        self.assertEqual(loaded, config)
        self.assertNotIn("app_secret", json.loads(raw_text))
        self.assertNotIn("secret-value", raw_text)

    def test_missing_config_returns_default_schema(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            loaded = load_app_config(Path(temp_dir) / "missing.json")

        self.assertEqual(loaded.schema_version, 1)
        self.assertIsNone(loaded.target)
        self.assertEqual(loaded.sources, [])


if __name__ == "__main__":
    unittest.main()
