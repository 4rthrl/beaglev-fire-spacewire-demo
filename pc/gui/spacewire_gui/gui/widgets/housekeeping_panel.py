"""Camera housekeeping summary, refresh control, and register inspector."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from spacewire_gui.gui.widgets.status_indicator import IndicatorState, StatusIndicator
from spacewire_gui.models.housekeeping import (
    GROUP_LABELS,
    GROUP_ORDER,
    HousekeepingSnapshot,
)
from spacewire_gui.models.housekeeping_display import (
    EMPTY,
    camera_error_state,
    field_label,
    field_style,
    format_field,
    group_display_keys,
    iter_searchable_fields,
    monitor_availability_state,
    spacewire_error_state,
    summary_camera_id,
    summary_firmware,
    summary_frame_counter,
    summary_image_size,
    summary_image_source,
    summary_operating_mode,
    summary_pattern,
    summary_tc_counter,
)
from spacewire_gui.models.spacewire_status import SpaceWireStatus

_SEVERITY_TO_INDICATOR = {
    IndicatorState.INACTIVE.value: IndicatorState.INACTIVE,
    IndicatorState.ACTIVE.value: IndicatorState.ACTIVE,
    IndicatorState.WARNING.value: IndicatorState.WARNING,
    IndicatorState.ERROR.value: IndicatorState.ERROR,
}


def _set_object_name(widget: QWidget, name: str) -> None:
    widget.setObjectName(name)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


class _SummaryRow(QWidget):
    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        name = QLabel(label)
        name.setObjectName("MutedLabel")
        name.setMinimumWidth(110)

        self._value = QLabel(EMPTY)
        self._value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._value.setWordWrap(True)
        self._value.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        layout.addWidget(name)
        layout.addWidget(self._value, stretch=1)

    def set_text(self, text: str, *, monospace: bool = False) -> None:
        self._value.setText(text)
        _set_object_name(self._value, "MonospaceValue" if monospace else "")


class _FieldRow(QWidget):
    def __init__(
        self,
        label: str,
        value: str,
        style_name: str,
        selected: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(8)

        name = QLabel(label)
        name.setObjectName("MutedLabel")
        name.setMinimumWidth(160)
        name.setWordWrap(True)

        self._value = QLabel(value)
        self._value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._value.setWordWrap(True)
        self._value.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        if style_name == "error":
            _set_object_name(self._value, "ErrorStatus")
        elif style_name == "unavailable":
            _set_object_name(self._value, "UnavailableValue")
        elif style_name == "mono":
            _set_object_name(self._value, "MonospaceValue")

        layout.addWidget(name)
        layout.addWidget(self._value, stretch=1)
        _set_object_name(self, "FieldRowSelected" if selected else "FieldRow")


class HousekeepingPanel(QGroupBox):
    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("CAMERA HOUSEKEEPING", parent)
        self._snapshot = HousekeepingSnapshot()
        self._link_available = False
        self._request_pending = False
        self._selected_field: str | None = None
        self._field_rows: dict[str, _FieldRow] = {}
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Maximum,
        )
        self._build_ui()
        self._show_empty_details()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self._refresh_button = QPushButton("Refresh Housekeeping")
        self._refresh_button.setObjectName("PrimaryButton")
        self._refresh_button.setFixedHeight(32)
        self._refresh_button.setEnabled(False)
        self._refresh_button.clicked.connect(self._on_refresh_clicked)
        self._status_label = QLabel("No data")
        self._status_label.setObjectName("MutedLabel")
        toolbar.addWidget(self._refresh_button)
        toolbar.addWidget(self._status_label, stretch=1)
        layout.addLayout(toolbar)

        panes = QHBoxLayout()
        panes.setSpacing(12)
        panes.addWidget(self._build_summary_pane(), stretch=2)
        panes.addWidget(self._build_inspector_pane(), stretch=3)
        layout.addLayout(panes, stretch=1)

        self._clear_summary()

    def _build_summary_pane(self) -> QWidget:
        pane = QWidget()
        pane.setMinimumWidth(260)
        pane.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title = QLabel("CAMERA SUMMARY")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self._camera_id = _SummaryRow("Camera ID")
        self._firmware = _SummaryRow("Firmware")
        self._operating_mode = _SummaryRow("Operating Mode")
        self._image_source = _SummaryRow("Image Source")
        self._pattern = _SummaryRow("Pattern")
        self._image_size = _SummaryRow("Image Size")
        self._tc_counter = _SummaryRow("TC Counter")
        self._frame_counter = _SummaryRow("Frame Counter")
        for row in (
            self._camera_id,
            self._firmware,
            self._operating_mode,
            self._image_source,
            self._pattern,
            self._image_size,
            self._tc_counter,
            self._frame_counter,
        ):
            layout.addWidget(row)

        layout.addStretch(1)

        self._camera_error = StatusIndicator("Camera Error")
        self._monitors = StatusIndicator("Monitors")
        self._spacewire = StatusIndicator("SpaceWire")
        for indicator in (self._camera_error, self._monitors, self._spacewire):
            layout.addWidget(indicator)

        return pane

    def _build_inspector_pane(self) -> QWidget:
        pane = QWidget()
        pane.setMinimumWidth(320)
        pane.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        inspector = QHBoxLayout()
        inspector.setSpacing(8)
        group_label = QLabel("Group")
        group_label.setObjectName("MutedLabel")
        self._group_combo = QComboBox()
        self._group_combo.setObjectName("PatternCombo")
        self._group_combo.setFixedHeight(32)
        for group_id in GROUP_ORDER:
            self._group_combo.addItem(GROUP_LABELS[group_id], group_id)
        self._group_combo.currentIndexChanged.connect(self._on_group_changed)

        find_label = QLabel("Find")
        find_label.setObjectName("MutedLabel")
        self._field_combo = QComboBox()
        self._field_combo.setObjectName("PatternCombo")
        self._field_combo.setFixedHeight(32)
        self._field_combo.setEditable(True)
        self._field_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._field_combo.setEnabled(False)
        completer = QCompleter(self._field_combo.model(), self._field_combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._field_combo.setCompleter(completer)
        line_edit = self._field_combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText("Find field...")
        self._field_combo.activated.connect(self._on_field_activated)

        inspector.addWidget(group_label)
        inspector.addWidget(self._group_combo, stretch=1)
        inspector.addWidget(find_label)
        inspector.addWidget(self._field_combo, stretch=2)
        layout.addLayout(inspector)

        self._details_host = QWidget()
        self._details_layout = QVBoxLayout(self._details_host)
        self._details_layout.setContentsMargins(0, 0, 0, 0)
        self._details_layout.setSpacing(0)
        self._details_layout.addStretch(1)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._scroll.setMinimumHeight(160)
        self._scroll.setWidget(self._details_host)
        layout.addWidget(self._scroll, stretch=1)

        return pane

    def _on_refresh_clicked(self) -> None:
        if self._request_pending or not self._link_available:
            return
        self._request_pending = True
        self._status_label.setText("Requesting...")
        _set_object_name(self._status_label, "MutedLabel")
        self._refresh_button.setEnabled(False)
        self.refresh_requested.emit()

    def _on_group_changed(self) -> None:
        group_id = self._current_group_id()
        if self._selected_field is not None:
            keys = group_display_keys(group_id)
            if self._selected_field not in keys:
                self._selected_field = None
        self._rebuild_details()

    def _on_field_activated(self, index_or_text: object) -> None:
        if isinstance(index_or_text, int):
            index = index_or_text
        else:
            index = self._field_combo.currentIndex()
        data = self._field_combo.itemData(index)
        if not isinstance(data, tuple) or len(data) != 2:
            return
        group_id, key = data
        self._selected_field = key
        self._set_group(group_id)
        self._rebuild_details()
        row = self._field_rows.get(key)
        if row is not None:
            self._scroll.ensureWidgetVisible(row)

    def update_status(self, status: SpaceWireStatus) -> None:
        self._link_available = status.image_requests_available()
        self._update_refresh_enabled()

    def set_snapshot(self, snapshot: HousekeepingSnapshot) -> None:
        self._snapshot = snapshot.copy()
        self._rebuild_field_combo()
        self._update_summary()
        self._rebuild_details()

    def set_request_status(self, success: bool, message: str) -> None:
        self._request_pending = False
        if success:
            self._status_label.setText("Received")
            _set_object_name(self._status_label, "OkStatus")
        else:
            self._status_label.setText(f"Failed: {message}")
            _set_object_name(self._status_label, "ErrorStatus")
        self._update_refresh_enabled()

    def _update_refresh_enabled(self) -> None:
        self._refresh_button.setEnabled(
            self._link_available and not self._request_pending
        )

    def _current_group_id(self) -> str:
        data = self._group_combo.currentData()
        if isinstance(data, str):
            return data
        return GROUP_ORDER[0]

    def _set_group(self, group_id: str) -> None:
        index = self._group_combo.findData(group_id)
        if index < 0 or index == self._group_combo.currentIndex():
            return
        self._group_combo.blockSignals(True)
        self._group_combo.setCurrentIndex(index)
        self._group_combo.blockSignals(False)

    def _clear_summary(self) -> None:
        self._camera_id.set_text(EMPTY, monospace=True)
        self._firmware.set_text(EMPTY)
        self._operating_mode.set_text(EMPTY)
        self._image_source.set_text(EMPTY)
        self._pattern.set_text(EMPTY)
        self._image_size.set_text(EMPTY)
        self._tc_counter.set_text(EMPTY)
        self._frame_counter.set_text(EMPTY)
        self._camera_error.set_state(IndicatorState.INACTIVE, EMPTY)
        self._monitors.set_state(IndicatorState.INACTIVE, EMPTY)
        self._spacewire.set_state(IndicatorState.INACTIVE, EMPTY)

    def _update_summary(self) -> None:
        if self._snapshot.is_empty():
            self._clear_summary()
            return

        self._camera_id.set_text(summary_camera_id(self._snapshot), monospace=True)
        self._firmware.set_text(summary_firmware(self._snapshot))
        self._operating_mode.set_text(summary_operating_mode(self._snapshot))
        self._image_source.set_text(summary_image_source(self._snapshot))
        self._pattern.set_text(summary_pattern(self._snapshot))
        self._image_size.set_text(summary_image_size(self._snapshot))
        self._tc_counter.set_text(summary_tc_counter(self._snapshot))
        self._frame_counter.set_text(summary_frame_counter(self._snapshot))

        error_severity, error_text = camera_error_state(self._snapshot)
        monitor_severity, monitor_text = monitor_availability_state(self._snapshot)
        spw_severity, spw_text = spacewire_error_state(self._snapshot)
        self._camera_error.set_state(_SEVERITY_TO_INDICATOR[error_severity], error_text)
        self._monitors.set_state(_SEVERITY_TO_INDICATOR[monitor_severity], monitor_text)
        self._spacewire.set_state(_SEVERITY_TO_INDICATOR[spw_severity], spw_text)

    def _rebuild_field_combo(self) -> None:
        previous = self._selected_field
        self._field_combo.blockSignals(True)
        self._field_combo.clear()
        items = iter_searchable_fields(self._snapshot)
        self._field_combo.setEnabled(bool(items))
        for group_id, key, text in items:
            self._field_combo.addItem(text, (group_id, key))
        if previous:
            for index in range(self._field_combo.count()):
                data = self._field_combo.itemData(index)
                if isinstance(data, tuple) and data[1] == previous:
                    self._field_combo.setCurrentIndex(index)
                    break
        self._field_combo.blockSignals(False)
        if previous is None or self._field_combo.currentIndex() < 0:
            self._field_combo.setCurrentIndex(-1)
            line_edit = self._field_combo.lineEdit()
            if line_edit is not None:
                line_edit.clear()
                line_edit.setPlaceholderText("Find field...")

    def _clear_details(self) -> None:
        self._field_rows.clear()
        while self._details_layout.count():
            item = self._details_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _show_empty_details(self) -> None:
        self._clear_details()
        placeholder = QLabel("Refresh housekeeping to inspect camera registers.")
        placeholder.setObjectName("MutedLabel")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._details_layout.addWidget(placeholder)
        self._details_layout.addStretch(1)

    def _rebuild_details(self) -> None:
        if self._snapshot.is_empty():
            self._show_empty_details()
            return

        group_id = self._current_group_id()
        self._clear_details()
        for key in group_display_keys(group_id):
            if (
                self._snapshot.get(key) == ""
                and key != "image_size_raw"
            ):
                continue
            selected = key == self._selected_field
            row = _FieldRow(
                field_label(key),
                format_field(self._snapshot, key),
                field_style(self._snapshot, key),
                selected,
            )
            self._details_layout.addWidget(row)
            self._field_rows[key] = row
        self._details_layout.addStretch(1)
        if self._selected_field in self._field_rows:
            self._scroll.ensureWidgetVisible(self._field_rows[self._selected_field])
