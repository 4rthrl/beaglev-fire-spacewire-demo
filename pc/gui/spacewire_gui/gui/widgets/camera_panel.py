"""Camera image view and pattern request controls."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from spacewire_gui.models.image_patterns import ALL_PATTERNS, COLOR_BOXES, PATTERN_LABELS
from spacewire_gui.models.spacewire_status import SpaceWireStatus


class _AspectRatioImageLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source_image: QImage | None = None
        self._use_fast_scale = False

    def set_source_image(self, image: QImage, *, fast_scale: bool = False) -> None:
        self._source_image = image
        self._use_fast_scale = fast_scale
        self._refresh()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        if self._source_image is None or self._source_image.isNull():
            return
        target = self.size()
        if target.width() <= 0 or target.height() <= 0:
            return

        mode = (
            Qt.TransformationMode.FastTransformation
            if self._use_fast_scale
            else Qt.TransformationMode.SmoothTransformation
        )
        pixmap = QPixmap.fromImage(self._source_image)
        self.setPixmap(
            pixmap.scaled(target, Qt.AspectRatioMode.KeepAspectRatio, mode)
        )


class CameraPanel(QGroupBox):
    pattern_changed = Signal(int)
    capture_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("CAMERA", parent)
        self._use_fast_scale = False
        self._has_errors = False
        self._controls_available = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._image_label = _AspectRatioImageLabel("No image")
        self._image_label.setObjectName("ImageFrame")
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setMinimumSize(280, 280)
        layout.addWidget(self._image_label, stretch=1)

        self._resolution_label = QLabel("Resolution: —")
        self._resolution_label.setObjectName("MutedLabel")
        layout.addWidget(self._resolution_label)

        controls = QWidget()
        controls.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        pattern_label = QLabel("Pattern")
        pattern_label.setObjectName("MutedLabel")
        controls_layout.addWidget(pattern_label)

        self._pattern_combo = QComboBox()
        self._pattern_combo.setObjectName("PatternCombo")
        self._pattern_combo.setFixedHeight(32)
        for pattern_id in ALL_PATTERNS:
            self._pattern_combo.addItem(PATTERN_LABELS[pattern_id], pattern_id)
        self._pattern_combo.currentIndexChanged.connect(self._on_pattern_changed)
        controls_layout.addWidget(self._pattern_combo, stretch=1)

        self._request_button = QPushButton("Request")
        self._request_button.setObjectName("PrimaryButton")
        self._request_button.setFixedHeight(32)
        self._request_button.setFixedWidth(100)
        self._request_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._request_button.clicked.connect(self._on_request_clicked)
        self._request_button.setEnabled(False)
        controls_layout.addWidget(self._request_button)

        layout.addWidget(controls)

    def _on_pattern_changed(self) -> None:
        pattern = self._pattern_combo.currentData()
        if pattern is None:
            return
        self._use_fast_scale = pattern == COLOR_BOXES
        self.pattern_changed.emit(int(pattern))

    def _on_request_clicked(self) -> None:
        self.capture_requested.emit(self.selected_pattern())

    def selected_pattern(self) -> int:
        return int(self._pattern_combo.currentData())

    def update_status(self, status: SpaceWireStatus) -> None:
        available = status.image_requests_available()
        if available and not self._controls_available:
            self._on_pattern_changed()
        self._controls_available = available

        self._pattern_combo.setEnabled(available)
        self._request_button.setEnabled(available)

        self._has_errors = status.has_operator_errors()
        if self._has_errors:
            self._request_button.setObjectName("WarningButton")
        else:
            self._request_button.setObjectName("PrimaryButton")
        self._request_button.style().unpolish(self._request_button)
        self._request_button.style().polish(self._request_button)

    def set_image(self, image: QImage) -> None:
        self._resolution_label.setText(
            f"Resolution: {image.width()} × {image.height()}"
        )
        self._image_label.set_source_image(image, fast_scale=self._use_fast_scale)
