"""Render the approved SVG artwork and bundle exact PNG frames into an ICO."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


PROJECT_DIR = Path(__file__).resolve().parents[1]
RESOURCES_DIR = PROJECT_DIR / "resources"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def render_svg(source: Path, destination: Path, size: int) -> bytes:
    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise RuntimeError(f"无法读取 SVG：{source}")
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    image.setDevicePixelRatio(1.0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(painter)
    painter.end()
    if not image.save(str(destination), "PNG"):
        raise RuntimeError(f"无法保存 PNG：{destination}")
    return destination.read_bytes()


def write_ico(destination: Path, frames: list[tuple[int, bytes]]) -> None:
    header = struct.pack("<HHH", 0, 1, len(frames))
    directory = bytearray()
    payload = bytearray()
    offset = 6 + len(frames) * 16
    for size, png in frames:
        dimension = 0 if size == 256 else size
        directory.extend(
            struct.pack(
                "<BBBBHHII",
                dimension,
                dimension,
                0,
                0,
                1,
                32,
                len(png),
                offset,
            )
        )
        payload.extend(png)
        offset += len(png)
    destination.write_bytes(header + directory + payload)


def build() -> Path:
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for size in SIZES:
        source = RESOURCES_DIR / ("icon-small.svg" if size <= 24 else "icon.svg")
        png_path = RESOURCES_DIR / f"icon-{size}.png"
        frames.append((size, render_svg(source, png_path, size)))
    ico_path = RESOURCES_DIR / "icon.ico"
    write_ico(ico_path, frames)
    return ico_path


if __name__ == "__main__":
    result = build()
    print(f"Generated {result} with {len(SIZES)} sizes")
