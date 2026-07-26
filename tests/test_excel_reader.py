import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.excel_reader import read_excel_preview  # noqa: E402


class ExcelReaderTests(unittest.TestCase):
    def test_preview_reads_the_requested_sheet(self):
        with tempfile.TemporaryDirectory() as temporary:
            workbook = Path(temporary) / "multi-sheet.xlsx"
            with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
                pd.DataFrame({"第一页字段": ["A"]}).to_excel(
                    writer, sheet_name="第一页", index=False
                )
                pd.DataFrame({"第二页字段": ["B"]}).to_excel(
                    writer, sheet_name="第二页", index=False
                )

            preview = read_excel_preview(str(workbook), sheet_name="第二页")

        self.assertEqual(preview["headers"], ["第二页字段"])
        self.assertEqual(preview["rows"], [["B"]])
        self.assertEqual(preview["selected_sheet"], "第二页")


if __name__ == "__main__":
    unittest.main()
