from __future__ import annotations

DARK_QSS = """
QWidget {
    background-color: #12161f;
    color: #dce6f5;
    font-size: 12px;
}
QMainWindow::separator {
    background: #0b0e14;
    width: 4px;
    height: 4px;
}
QToolBar {
    background: #161b26;
    border: none;
    padding: 4px;
    spacing: 4px;
}
QToolBar QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 6px 10px;
    color: #dce6f5;
}
QToolBar QToolButton:hover {
    background: #1f2735;
    border-color: #2b374b;
}
QToolBar QToolButton:pressed {
    background: #2b374b;
}
QToolBar::separator {
    background: #2b374b;
    width: 1px;
    margin: 6px 4px;
}
QMenuBar {
    background: #161b26;
}
QMenuBar::item {
    background: transparent;
    padding: 5px 10px;
}
QMenuBar::item:selected {
    background: #232c3c;
    border-radius: 4px;
}
QMenu {
    background: #1a2130;
    border: 1px solid #2b374b;
    padding: 4px;
}
QMenu::item {
    padding: 6px 28px 6px 22px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #2a4a75;
}
QMenu::separator {
    height: 1px;
    background: #2b374b;
    margin: 4px 8px;
}
QDockWidget {
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
    color: #8fa6c8;
    font-weight: 600;
}
QDockWidget::title {
    background: #161b26;
    padding: 7px 10px;
    border-bottom: 1px solid #0b0e14;
}
QGroupBox {
    border: 1px solid #263042;
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 10px;
    font-weight: 600;
    color: #9fb4d4;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QPushButton {
    background: #1d2635;
    border: 1px solid #2b374b;
    border-radius: 5px;
    padding: 6px 10px;
}
QPushButton:hover {
    background: #263247;
    border-color: #3a4b66;
}
QPushButton:pressed {
    background: #151c28;
}
QPushButton:checked {
    background: #2a4a75;
    border-color: #3f7bc4;
}
QPushButton#accent {
    background: #2f6fce;
    border-color: #3f85ee;
    color: white;
    font-weight: 600;
}
QPushButton#accent:hover {
    background: #3a7fe4;
}
QPushButton#danger:hover {
    background: #6b2630;
    border-color: #a33a48;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {
    background: #0e131c;
    border: 1px solid #2b374b;
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: #2f6fce;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {
    border-color: #3f85ee;
}
QComboBox::drop-down {
    border: none;
    width: 18px;
}
QComboBox QAbstractItemView {
    background: #161d2a;
    border: 1px solid #2b374b;
    selection-background-color: #2a4a75;
    outline: none;
}
QScrollArea {
    border: none;
}
QScrollBar:vertical {
    background: #0e131c;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2b374b;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #3a4b66;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #0e131c;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: #2b374b;
    border-radius: 5px;
    min-width: 30px;
}
QListWidget {
    background: #0e131c;
    border: 1px solid #222b3a;
    border-radius: 4px;
    outline: none;
}
QListWidget::item {
    padding: 6px 6px;
    border-radius: 3px;
}
QListWidget::item:selected {
    background: #2a4a75;
}
QListWidget::item:hover {
    background: #1d2635;
}
QSplitter::handle {
    background: #0b0e14;
}
QStatusBar {
    background: #161b26;
    color: #8fa6c8;
}
QLabel#hint {
    color: #7186a6;
}
QLabel#warn {
    color: #ffb4a8;
}
QLabel#title {
    color: #eaf1fc;
    font-size: 14px;
    font-weight: 700;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
}
QToolTip {
    background: #1a2130;
    color: #dce6f5;
    border: 1px solid #2b374b;
}
"""
