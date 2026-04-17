#source: github.com/zeittresor

import sys
from pathlib import Path

from .runtime_checks import preload_torch

# On some Windows + PyQt setups, preloading torch before creating QApplication
# avoids later DLL initialization failures when captioning/training imports torch.
preload_torch()

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from .logging_utils import setup_logging
from .ui.main_window import MainWindow


def main():
    project_root = Path(__file__).resolve().parent.parent
    setup_logging(project_root)
    app = QApplication(sys.argv)
    icon_candidates = [project_root / "app" / "assets" / "app_icon.ico", project_root / "app" / "assets" / "app_icon.png"]
    for icon_path in icon_candidates:
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
            break
    window = MainWindow(project_root)
    window.show()
    sys.exit(app.exec())
