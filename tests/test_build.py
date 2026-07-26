import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build  # noqa: E402


class BuildCommandTests(unittest.TestCase):
    def test_excludes_unused_optional_heavy_modules(self):
        command = build.build_command(icon_path="")
        argument_pairs = list(zip(command, command[1:]))

        for module_name in ("torch", "scipy", "matplotlib"):
            self.assertIn(("--exclude-module", module_name), argument_pairs)


if __name__ == "__main__":
    unittest.main()
