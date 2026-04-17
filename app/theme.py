DARK_STYLESHEET = """
QMainWindow, QDialog, QWidget#AppRoot, QWidget#ScrollPage, QWidget#TabPage {
    background: #1d2330;
    color: #e9eef7;
    font-size: 10pt;
}
QWidget {
    color: #e9eef7;
    font-size: 10pt;
}
QLabel {
    background: transparent;
    min-height: 24px;
    padding: 2px 0;
}
QGroupBox {
    border: 1px solid #394457;
    border-radius: 14px;
    margin-top: 16px;
    padding: 18px 14px 14px 14px;
    font-weight: 600;
    background: #252d3c;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background: #1d2330;
}
QPushButton, QComboBox, QLineEdit, QSpinBox, QTextEdit, QTableWidget {
    border: 1px solid #3d495d;
    border-radius: 10px;
    background: #2b3444;
}
QPushButton {
    padding: 9px 12px;
    font-weight: 600;
    min-height: 20px;
}
QPushButton:hover {
    background: #34415a;
}
QPushButton:pressed {
    background: #41506e;
}
QPushButton:disabled {
    color: #8d97aa;
    background: #262d39;
}
QLineEdit, QComboBox, QSpinBox {
    padding: 7px 10px;
    min-height: 30px;
    selection-background-color: #4a5f85;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QTableWidget:focus {
    border: 1px solid #6f9dff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background: #2b3444;
    selection-background-color: #465a7e;
    border: 1px solid #3d495d;
}
QTextEdit, QTableWidget {
    padding: 6px;
    selection-background-color: #465a7e;
    gridline-color: #404b60;
    alternate-background-color: #253043;
}
QTableWidget {
    min-height: 260px;
}
QHeaderView::section {
    background: #313c50;
    border: 0;
    border-right: 1px solid #42506a;
    padding: 10px 9px;
    font-weight: 600;
}
QTabWidget::pane {
    border: 0;
    margin-top: 8px;
    padding-top: 10px;
    background: transparent;
}
QTabBar::tab {
    background: #283245;
    border: 1px solid #3d495d;
    padding: 10px 15px;
    margin-right: 6px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}
QTabBar::tab:selected {
    background: #36445e;
    border-bottom-color: #36445e;
}
QTabBar::tab:!selected {
    margin-top: 4px;
}
QProgressBar {
    border: 1px solid #3d495d;
    border-radius: 8px;
    text-align: center;
    background: #253042;
    min-height: 24px;
}
QProgressBar::chunk {
    border-radius: 7px;
    background: #5f90ff;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #202837;
    border: none;
    margin: 2px;
}
QScrollBar:vertical { width: 14px; }
QScrollBar:horizontal { height: 14px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #506280;
    border-radius: 6px;
    min-height: 26px;
    min-width: 26px;
}
QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page {
    background: none;
    border: none;
}
QSplitter::handle {
    background: #1d2330;
}
QToolTip {
    background: #11161f;
    color: #eef5ff;
    border: 1px solid #5f90ff;
    padding: 6px;
}
"""

LIGHT_STYLESHEET = """
QMainWindow, QDialog, QWidget#AppRoot, QWidget#ScrollPage, QWidget#TabPage {
    background: #f4f7fb;
    color: #1b2430;
    font-size: 10pt;
}
QWidget {
    color: #1b2430;
    font-size: 10pt;
}
QLabel {
    background: transparent;
    min-height: 24px;
    padding: 2px 0;
}
QGroupBox {
    border: 1px solid #d6deea;
    border-radius: 14px;
    margin-top: 16px;
    padding: 18px 14px 14px 14px;
    font-weight: 600;
    background: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background: #f4f7fb;
}
QPushButton, QComboBox, QLineEdit, QSpinBox, QTextEdit, QTableWidget {
    border: 1px solid #d7dfeb;
    border-radius: 10px;
    background: #ffffff;
}
QPushButton {
    padding: 9px 12px;
    font-weight: 600;
    min-height: 20px;
}
QPushButton:hover {
    background: #ecf3ff;
}
QPushButton:pressed {
    background: #dbe7ff;
}
QLineEdit, QComboBox, QSpinBox {
    padding: 7px 10px;
    min-height: 30px;
    selection-background-color: #dce8ff;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QTableWidget:focus {
    border: 1px solid #4f80ff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    selection-background-color: #dce8ff;
    border: 1px solid #d7dfeb;
}
QTextEdit, QTableWidget {
    padding: 6px;
    selection-background-color: #dce8ff;
    gridline-color: #d7dfeb;
    alternate-background-color: #f5f8fe;
}
QTableWidget {
    min-height: 260px;
}
QHeaderView::section {
    background: #eef3fb;
    border: 0;
    border-right: 1px solid #d7dfeb;
    padding: 10px 9px;
    font-weight: 600;
}
QTabWidget::pane {
    border: 0;
    margin-top: 8px;
    padding-top: 10px;
    background: transparent;
}
QTabBar::tab {
    background: #eef2f8;
    border: 1px solid #d7dfeb;
    padding: 10px 15px;
    margin-right: 6px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}
QTabBar::tab:selected {
    background: #ffffff;
    border-bottom-color: #ffffff;
}
QTabBar::tab:!selected {
    margin-top: 4px;
}
QProgressBar {
    border: 1px solid #d7dfeb;
    border-radius: 8px;
    text-align: center;
    background: #ffffff;
    min-height: 24px;
}
QProgressBar::chunk {
    border-radius: 7px;
    background: #4f80ff;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #e6edf8;
    border: none;
    margin: 2px;
}
QScrollBar:vertical { width: 14px; }
QScrollBar:horizontal { height: 14px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #96afdd;
    border-radius: 6px;
    min-height: 26px;
    min-width: 26px;
}
QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page {
    background: none;
    border: none;
}
QSplitter::handle {
    background: #f4f7fb;
}
QToolTip {
    background: #ffffff;
    color: #102038;
    border: 1px solid #4f80ff;
    padding: 6px;
}
"""


def get_stylesheet(mode: str) -> str:
    return LIGHT_STYLESHEET if str(mode).lower().strip() == 'light' else DARK_STYLESHEET
