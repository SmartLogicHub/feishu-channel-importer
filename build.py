"""Build the portable single-file Windows application with PyInstaller."""
import os
import subprocess
import sys


APP_NAME = "飞书渠道数据汇总工具"


def build_command(icon_path=r"resources\icon.ico"):
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", APP_NAME,
        "--hidden-import", "requests",
        "--hidden-import", "openpyxl",
        "--hidden-import", "pandas",
        "--hidden-import", "cryptography",
        "--hidden-import", "zoneinfo",
        "--hidden-import", "tzdata",
        "--collect-all", "tzdata",
        "--hidden-import", "urllib3",
        "--hidden-import", "charset_normalizer",
        "--hidden-import", "certifi",
        "--exclude-module", "torch",
        "--exclude-module", "scipy",
        "--exclude-module", "matplotlib",
        "main.py",
    ]

    if os.path.exists(icon_path):
        cmd[3:3] = [
            "--icon", icon_path,
            "--add-data", f"{icon_path}{os.pathsep}resources",
        ]
    return cmd


def build():
    cmd = build_command()

    print("PyInstaller from:", sys.executable)
    print("开始打包...")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"\n打包完成：dist/{APP_NAME}.exe")

if __name__ == "__main__":
    build()
