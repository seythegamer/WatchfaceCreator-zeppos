from __future__ import annotations

import sys
import tempfile
import traceback
import uuid
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from . import constants as C
from .model import Project, make_project
from .ui.mainwindow import MainWindow
from .ui.theme import DARK_QSS


def _prepare_project(settings: QSettings) -> tuple[Project, Path | None]:
    last = settings.value("last_project")
    if last:
        folder = Path(str(last))
        if (folder / "project.json").exists():
            try:
                return Project.load(folder), folder
            except Exception as error:  # noqa: BLE001
                print(f"Nie można wczytać ostatniego projektu {folder}: {error}")
    base = Path(tempfile.gettempdir()) / "WatchFaceStudio" / "projects"
    base.mkdir(parents=True, exist_ok=True)
    root = base / f"nowa-tarcza-{uuid.uuid4().hex[:6]}"
    project = make_project("Moja tarcza", "Cyfrowa", root)
    project.save()
    return project, None


def _install_excepthook() -> None:
    def hook(kind, value, tb) -> None:
        traceback.print_exception(kind, value, tb)
        QMessageBox.critical(
            None,
            "Nieoczekiwany błąd",
            f"Wystąpił błąd aplikacji:\n\n{value}\n\nSzczegóły w konsoli.",
        )

    sys.excepthook = hook


def run() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName(C.SETTINGS_ORG)
    app.setApplicationName(C.SETTINGS_APP)
    app.setApplicationDisplayName(C.APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_QSS)

    font = app.font()
    font.setFamily("Segoe UI")
    font.setPointSize(9)
    app.setFont(font)

    _install_excepthook()
    settings = QSettings(C.SETTINGS_ORG, C.SETTINGS_APP)
    project, saved_root = _prepare_project(settings)
    window = MainWindow(project, saved_root)
    window.show()
    return app.exec()
