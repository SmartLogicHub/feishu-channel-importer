import sys
import unittest
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.value_normalizer import (  # noqa: E402
    NormalizationError,
    created_time_range,
    ms_to_shanghai_date,
    normalize_for_target,
    resolve_display_value,
    to_feishu_date_ms,
)


class DateNormalizationTests(unittest.TestCase):
    def test_date_values_become_shanghai_midnight(self):
        expected = 1781107200000

        self.assertEqual(to_feishu_date_ms("2026-06-11"), expected)
        self.assertEqual(to_feishu_date_ms(46184), expected)
        self.assertEqual(to_feishu_date_ms("46184"), expected)
        self.assertEqual(to_feishu_date_ms(expected), expected)

    def test_created_time_range_is_inclusive_by_day_and_exclusive_at_end(self):
        start, end = created_time_range(date(2026, 7, 20), date(2026, 7, 23))

        self.assertEqual(ms_to_shanghai_date(start), date(2026, 7, 20))
        self.assertEqual(ms_to_shanghai_date(end - 1), date(2026, 7, 23))
        self.assertEqual(ms_to_shanghai_date(end), date(2026, 7, 24))


class FieldNormalizationTests(unittest.TestCase):
    def test_resolves_lookup_option_ids_and_nested_text(self):
        self.assertEqual(
            resolve_display_value(["optA"], {"optA": "Atom CC"}), "Atom CC"
        )
        self.assertEqual(resolve_display_value({"text": "店铺甲"}), "店铺甲")

    def test_unknown_option_id_is_a_clear_error(self):
        with self.assertRaisesRegex(NormalizationError, "optMissing"):
            resolve_display_value(["optMissing"], {"optA": "Atom CC"})

    def test_normalizes_number_select_text_and_date_for_target(self):
        self.assertEqual(normalize_for_target("12.5", 2), 12.5)
        self.assertEqual(normalize_for_target("Atom CC", 3), "Atom CC")
        self.assertEqual(normalize_for_target(["A", "B"], 1), "A | B")
        self.assertEqual(normalize_for_target("2026-06-11", 5), 1781107200000)


if __name__ == "__main__":
    unittest.main()
