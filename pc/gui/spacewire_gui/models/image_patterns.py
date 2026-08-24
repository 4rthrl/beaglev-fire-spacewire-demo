"""Image pattern identifiers matching the FPGA mock-camera command protocol."""

COLOR_BOXES = 0
SOLID_RED = 1
SOLID_GREEN = 2
SOLID_BLUE = 3
VERTICAL_COLOR_BARS = 4
HORIZONTAL_COLOR_BARS = 5
HORIZONTAL_BW_GRADIENT = 6
VERTICAL_BW_GRADIENT = 7

PATTERN_LABELS: dict[int, str] = {
    COLOR_BOXES: "Color Boxes / Grid",
    SOLID_RED: "Solid Red",
    SOLID_GREEN: "Solid Green",
    SOLID_BLUE: "Solid Blue",
    VERTICAL_COLOR_BARS: "Vertical Color Bars",
    HORIZONTAL_COLOR_BARS: "Horizontal Color Bars",
    HORIZONTAL_BW_GRADIENT: "Horizontal Black-to-White Gradient",
    VERTICAL_BW_GRADIENT: "Vertical Black-to-White Gradient",
}

ALL_PATTERNS: tuple[int, ...] = tuple(PATTERN_LABELS.keys())
