"""Light theme for SpaceWire Camera Control."""


def load_stylesheet() -> str:
    return """
    QWidget {
        background-color: #f4f6f9;
        color: #1e293b;
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        font-size: 10pt;
    }

    QMainWindow {
        background-color: #f4f6f9;
    }

    QGroupBox {
        background-color: #ffffff;
        border: 1px solid #d8dee9;
        border-radius: 6px;
        margin-top: 12px;
        padding: 10px 10px 10px 10px;
        font-weight: 600;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 6px;
        color: #475569;
        background-color: transparent;
    }

    QLabel {
        background-color: transparent;
    }

    QLabel#SectionTitle {
        color: #64748b;
        font-size: 9pt;
        font-weight: 600;
        letter-spacing: 0.5px;
    }

    QLabel#ConnectionSummary {
        font-size: 12pt;
        font-weight: 600;
        color: #0f172a;
    }

    QLabel#MonospaceValue {
        font-family: Consolas, "Courier New", monospace;
        color: #334155;
    }

    QLabel#MutedLabel {
        color: #64748b;
    }

    QLabel#OkStatus {
        color: #15803d;
        font-weight: 600;
    }

    QLabel#ErrorStatus {
        color: #b91c1c;
        font-weight: 600;
    }

    QLabel#UnavailableValue {
        color: #94a3b8;
        font-style: italic;
    }

    QLabel#ImageFrame {
        background-color: #eef2f7;
        border: 1px solid #d8dee9;
        border-radius: 4px;
        color: #94a3b8;
    }

    QLabel#DebugBanner {
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1d4ed8;
        padding: 6px;
        font-size: 9pt;
        border-radius: 4px;
    }

    QPushButton {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        padding: 4px 12px;
        min-height: 0px;
        max-height: 32px;
        color: #1e293b;
    }

    QPushButton:hover {
        background-color: #f8fafc;
        border-color: #94a3b8;
    }

    QPushButton:pressed {
        background-color: #e2e8f0;
    }

    QPushButton:disabled {
        background-color: #f1f5f9;
        color: #94a3b8;
        border-color: #e2e8f0;
    }

    QPushButton#PrimaryButton {
        background-color: #2563eb;
        border-color: #2563eb;
        color: #ffffff;
        font-weight: 600;
    }

    QPushButton#PrimaryButton:hover {
        background-color: #1d4ed8;
        border-color: #1d4ed8;
    }

    QPushButton#PrimaryButton:pressed {
        background-color: #1e40af;
        border-color: #1e40af;
    }

    QPushButton#PrimaryButton:disabled {
        background-color: #93c5fd;
        border-color: #93c5fd;
        color: #eff6ff;
    }

    QPushButton#SecondaryButton {
        background-color: #ffffff;
        border-color: #2563eb;
        color: #2563eb;
        font-weight: 600;
    }

    QPushButton#SecondaryButton:hover {
        background-color: #eff6ff;
    }

    QPushButton#SecondaryButton:pressed {
        background-color: #dbeafe;
    }

    QPushButton#SecondaryButton:disabled {
        background-color: #f8fafc;
        border-color: #cbd5e1;
        color: #94a3b8;
    }

    QPushButton#WarningButton {
        background-color: #f59e0b;
        border-color: #d97706;
        color: #ffffff;
        font-weight: 600;
    }

    QPushButton#WarningButton:hover {
        background-color: #d97706;
        border-color: #b45309;
    }

    QPushButton#WarningButton:pressed {
        background-color: #b45309;
        border-color: #92400e;
    }

    QPushButton#WarningButton:disabled {
        background-color: #fde68a;
        border-color: #fcd34d;
        color: #fffbeb;
    }

    QComboBox#PatternCombo {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 4px;
        padding: 2px 8px;
        min-height: 22px;
    }

    QComboBox#PatternCombo:disabled {
        background-color: #f1f5f9;
        color: #94a3b8;
    }

    QComboBox#PatternCombo::drop-down {
        border: none;
        width: 24px;
    }

    QComboBox#PatternCombo QAbstractItemView {
        background-color: #ffffff;
        border: 1px solid #d8dee9;
        selection-background-color: #eff6ff;
        selection-color: #1d4ed8;
    }

    QScrollArea {
        background-color: transparent;
        border: 1px solid #d8dee9;
        border-radius: 4px;
    }

    QWidget#FieldRow {
        background-color: transparent;
    }

    QWidget#FieldRowSelected {
        background-color: #eff6ff;
        border-radius: 4px;
    }

    QPlainTextEdit#LogPanel {
        background-color: #ffffff;
        border: 1px solid #d8dee9;
        color: #334155;
        font-family: Consolas, "Courier New", monospace;
        font-size: 9pt;
        padding: 4px;
        border-radius: 4px;
    }

    QStatusBar {
        background-color: #ffffff;
        border-top: 1px solid #d8dee9;
        color: #64748b;
    }

    QMenuBar {
        background-color: #ffffff;
        border-bottom: 1px solid #d8dee9;
    }

    QMenuBar::item:selected {
        background-color: #eff6ff;
        color: #1d4ed8;
    }

    QMenu {
        background-color: #ffffff;
        border: 1px solid #d8dee9;
    }

    QMenu::item:selected {
        background-color: #eff6ff;
        color: #1d4ed8;
    }

    QCheckBox {
        spacing: 6px;
    }

    QCheckBox::indicator {
        width: 14px;
        height: 14px;
        border: 1px solid #94a3b8;
        background-color: #ffffff;
        border-radius: 2px;
    }

    QCheckBox::indicator:checked {
        background-color: #2563eb;
        border-color: #2563eb;
    }
    """
