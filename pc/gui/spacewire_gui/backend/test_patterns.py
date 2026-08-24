"""Deterministic 64×64 test-pattern generators for the mock camera.

These functions are intentionally isolated so they can later be replaced or
aligned with the FPGA mock-camera TPG output without touching GUI code.
"""

from __future__ import annotations

from PySide6.QtGui import QImage, qRgb

from spacewire_gui.models.image_patterns import (
    COLOR_BOXES,
    HORIZONTAL_BW_GRADIENT,
    HORIZONTAL_COLOR_BARS,
    SOLID_BLUE,
    SOLID_GREEN,
    SOLID_RED,
    VERTICAL_BW_GRADIENT,
    VERTICAL_COLOR_BARS,
)

IMAGE_WIDTH = 64
IMAGE_HEIGHT = 64

_BAR_COLORS = (
    qRgb(255, 0, 0),
    qRgb(255, 255, 0),
    qRgb(0, 255, 0),
    qRgb(0, 255, 255),
    qRgb(0, 0, 255),
    qRgb(255, 0, 255),
    qRgb(255, 255, 255),
    qRgb(0, 0, 0),
)

_BOX_COLORS = (
    qRgb(255, 0, 0),
    qRgb(0, 255, 0),
    qRgb(0, 0, 255),
    qRgb(255, 255, 0),
    qRgb(255, 0, 255),
    qRgb(0, 255, 255),
    qRgb(255, 255, 255),
    qRgb(128, 128, 128),
)


def _solid_color(
    red: int,
    green: int,
    blue: int,
    width: int = IMAGE_WIDTH,
    height: int = IMAGE_HEIGHT,
) -> QImage:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    color = qRgb(red, green, blue)
    for y in range(height):
        for x in range(width):
            image.setPixel(x, y, color)
    return image


def generate_color_boxes(
    width: int = IMAGE_WIDTH,
    height: int = IMAGE_HEIGHT,
    cell_size: int = 8,
) -> QImage:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    for y in range(height):
        for x in range(width):
            cell_x = x // cell_size
            cell_y = y // cell_size
            color = _BOX_COLORS[(cell_x + cell_y) % len(_BOX_COLORS)]
            image.setPixel(x, y, color)
    return image


def generate_solid_red(width: int = IMAGE_WIDTH, height: int = IMAGE_HEIGHT) -> QImage:
    return _solid_color(255, 0, 0, width, height)


def generate_solid_green(width: int = IMAGE_WIDTH, height: int = IMAGE_HEIGHT) -> QImage:
    return _solid_color(0, 255, 0, width, height)


def generate_solid_blue(width: int = IMAGE_WIDTH, height: int = IMAGE_HEIGHT) -> QImage:
    return _solid_color(0, 0, 255, width, height)


def generate_vertical_color_bars(
    width: int = IMAGE_WIDTH,
    height: int = IMAGE_HEIGHT,
) -> QImage:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    bar_count = len(_BAR_COLORS)
    bar_width = max(width // bar_count, 1)
    for y in range(height):
        for x in range(width):
            bar = min(x // bar_width, bar_count - 1)
            image.setPixel(x, y, _BAR_COLORS[bar])
    return image


def generate_horizontal_color_bars(
    width: int = IMAGE_WIDTH,
    height: int = IMAGE_HEIGHT,
) -> QImage:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    bar_count = len(_BAR_COLORS)
    bar_height = max(height // bar_count, 1)
    for y in range(height):
        for x in range(width):
            bar = min(y // bar_height, bar_count - 1)
            image.setPixel(x, y, _BAR_COLORS[bar])
    return image


def generate_horizontal_bw_gradient(
    width: int = IMAGE_WIDTH,
    height: int = IMAGE_HEIGHT,
) -> QImage:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    x_max = max(width - 1, 1)
    for y in range(height):
        for x in range(width):
            gray = int(255 * x / x_max)
            image.setPixel(x, y, qRgb(gray, gray, gray))
    return image


def generate_vertical_bw_gradient(
    width: int = IMAGE_WIDTH,
    height: int = IMAGE_HEIGHT,
) -> QImage:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    y_max = max(height - 1, 1)
    for y in range(height):
        for x in range(width):
            gray = int(255 * y / y_max)
            image.setPixel(x, y, qRgb(gray, gray, gray))
    return image


def generate_pattern(pattern_id: int) -> QImage:
    if pattern_id == COLOR_BOXES:
        return generate_color_boxes()
    if pattern_id == SOLID_RED:
        return generate_solid_red()
    if pattern_id == SOLID_GREEN:
        return generate_solid_green()
    if pattern_id == SOLID_BLUE:
        return generate_solid_blue()
    if pattern_id == VERTICAL_COLOR_BARS:
        return generate_vertical_color_bars()
    if pattern_id == HORIZONTAL_COLOR_BARS:
        return generate_horizontal_color_bars()
    if pattern_id == HORIZONTAL_BW_GRADIENT:
        return generate_horizontal_bw_gradient()
    if pattern_id == VERTICAL_BW_GRADIENT:
        return generate_vertical_bw_gradient()
    raise ValueError(f"Unknown image pattern id: {pattern_id}")
