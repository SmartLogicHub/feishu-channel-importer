import struct
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect  # noqa: E402

from ui.theme import APP_STYLE  # noqa: E402
from ui.widgets import Card  # noqa: E402


PROJECT_DIR = Path(__file__).resolve().parents[1]
RESOURCES_DIR = PROJECT_DIR / "resources"
ICON_PATH = RESOURCES_DIR / "icon.ico"
EXPECTED_SIZES = {16, 24, 32, 48, 64, 128, 256}


def read_ico_sizes(path: Path) -> set[int]:
    data = path.read_bytes()
    reserved, image_type, count = struct.unpack_from("<HHH", data, 0)
    if reserved != 0 or image_type != 1:
        raise AssertionError("不是有效的 ICO 文件")
    sizes = set()
    for index in range(count):
        width, height = struct.unpack_from("<BB", data, 6 + index * 16)
        decoded_width = width or 256
        decoded_height = height or 256
        if decoded_width != decoded_height:
            raise AssertionError("ICO 图层必须为正方形")
        sizes.add(decoded_width)
    return sizes


class VisualAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_icon_sources_and_ico_sizes_exist(self):
        self.assertTrue((RESOURCES_DIR / "icon.svg").is_file())
        self.assertTrue((RESOURCES_DIR / "icon-small.svg").is_file())
        self.assertEqual(read_ico_sizes(ICON_PATH), EXPECTED_SIZES)

    def test_glacier_theme_contains_approved_palette(self):
        for color in ("#13213B", "#3370FF", "#4F8CFF", "#F4F7FC", "#18233A"):
            self.assertIn(color, APP_STYLE)

    def test_card_uses_soft_drop_shadow(self):
        card = Card()
        effect = card.graphicsEffect()

        self.assertIsInstance(effect, QGraphicsDropShadowEffect)
        self.assertGreaterEqual(effect.blurRadius(), 18)

    def test_mapping_editor_has_dedicated_spacing_and_status_styles(self):
        for selector in (
            "QFrame#mappingCard",
            "QLabel#statusChip",
            "QLabel#emptyState",
            "QLabel#rowError",
            "QPushButton#mappingDeleteButton",
            "QLabel#mappingArrow",
        ):
            self.assertIn(selector, APP_STYLE)


if __name__ == "__main__":
    unittest.main()
