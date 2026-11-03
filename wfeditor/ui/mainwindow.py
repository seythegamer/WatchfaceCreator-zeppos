from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QGuiApplication, QImage, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QToolBar,
)

from .. import constants as C
from ..exporter import export_source_zip, export_zpk
from ..model import Element, History, Project, make_project, slugify
from ..render import font_missing_polish
from .canvas import Canvas
from .dialogs import NewProjectDialog, PreviewDialog, ProjectSettingsDialog
from .inspector import Inspector
from .layers import LayersPanel
from .palette import Palette
from .previewdata import PreviewDataPanel


class MainWindow(QMainWindow):
    def __init__(self, project: Project, saved_root: Path | None = None) -> None:
        super().__init__()
        self.settings = QSettings(C.SETTINGS_ORG, C.SETTINGS_APP)
        self.project = project
        self.saved_root = saved_root
        self.history = History()
        self.dirty = saved_root is None

        self.setWindowTitle(C.APP_TITLE)
        self.resize(1440, 900)
        self.setMinimumSize(1080, 720)

        self.canvas = Canvas(project)
        self.setCentralWidget(self.canvas)

        self.inspector = Inspector(project)
        self.palette = Palette()
        self.layers = LayersPanel(project)
        self.preview_data = PreviewDataPanel(project)

        self._build_docks()
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()
        self._connect()
        self._load_recents()
        self._apply_project(project, saved_root)

        geometry = self.settings.value("window/geometry")
        state = self.settings.value("window/state")
        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state)
        self._update_undo()
        self._update_title()

    def _build_docks(self) -> None:
        left = QDockWidget("Biblioteka", self)
        left.setObjectName("dock_palette")
        left.setWidget(self.palette)
        left.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        left.setMinimumWidth(230)

        layers = QDockWidget("Warstwy", self)
        layers.setObjectName("dock_layers")
        layers.setWidget(self.layers)
        layers.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        right = QDockWidget("Właściwości", self)
        right.setObjectName("dock_inspector")
        right.setWidget(self.inspector)
        right.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        right.setMinimumWidth(360)

        data = QDockWidget("Dane podglądu", self)
        data.setObjectName("dock_preview_data")
        data.setWidget(self.preview_data)
        data.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        data.setMinimumWidth(360)
        self.data_dock = data

        self.addDockWidget(Qt.LeftDockWidgetArea, left)
        self.addDockWidget(Qt.LeftDockWidgetArea, layers)
        self.splitDockWidget(left, layers, Qt.Vertical)
        self.addDockWidget(Qt.RightDockWidgetArea, right)
        self.addDockWidget(Qt.RightDockWidgetArea, data)
        self.splitDockWidget(right, data, Qt.Vertical)
        self.resizeDocks([left, layers], [380, 380], Qt.Vertical)
        self.resizeDocks([right, data], [520, 320], Qt.Vertical)

    def _action(self, text: str, slot, shortcut: str | None = None) -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        return action

    def _build_actions(self) -> None:
        self.act_new = self._action("Nowa tarcza…", self.new_project, "Ctrl+N")
        self.act_open = self._action("Otwórz projekt…", self.open_project, "Ctrl+O")
        self.act_save = self._action("Zapisz", self.save_project, "Ctrl+S")
        self.act_save_as = self._action("Zapisz jako…", self.save_project_as, "Ctrl+Shift+S")
        self.act_export_zpk = self._action("Eksportuj .zpk…", self.export_zpk, "Ctrl+E")
        self.act_export_zip = self._action("Eksportuj ZIP źródłowy…", self.export_zip)
        self.act_preview = self._action("Podgląd tarczy", self.show_preview, "F5")
        self.act_quit = self._action("Wyjście", self.close, "Ctrl+Alt+Q")

        self.act_undo = self._action("Cofnij", self.undo, "Ctrl+Z")
        self.act_redo = self._action("Ponów", self.redo, "Ctrl+Y")
        self.act_duplicate = self._action("Duplikuj element", self.duplicate_selected, "Ctrl+D")
        self.act_delete = self._action("Usuń element", self.delete_selected)
        self.act_delete.setShortcut(QKeySequence(Qt.Key_Delete))
        self.act_delete.setShortcutContext(Qt.WidgetShortcut)
        self.canvas.addAction(self.act_delete)
        self.act_settings = self._action("Ustawienia projektu…", self.project_settings)

        self.act_grid = self._action("Siatka", self.toggle_grid)
        self.act_grid.setCheckable(True)
        self.act_grid.setChecked(True)
        self.act_snap = self._action("Przyciąganie do siatki", self.toggle_snap)
        self.act_snap.setCheckable(True)
        self.act_snap.setChecked(True)
        self.act_live = self._action("Czas rzeczywisty", self.toggle_live)
        self.act_live.setCheckable(True)
        self.act_about = self._action("O programie", self.show_about)

    def _build_menus(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("Plik")
        file_menu.addAction(self.act_new)
        file_menu.addAction(self.act_open)
        self.recent_menu = file_menu.addMenu("Ostatnie projekty")
        file_menu.addSeparator()
        file_menu.addAction(self.act_save)
        file_menu.addAction(self.act_save_as)
        file_menu.addSeparator()
        file_menu.addAction(self.act_export_zpk)
        file_menu.addAction(self.act_export_zip)
        file_menu.addAction(self.act_preview)
        file_menu.addSeparator()
        file_menu.addAction(self.act_quit)

        edit_menu = menu.addMenu("Edycja")
        edit_menu.addAction(self.act_undo)
        edit_menu.addAction(self.act_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_duplicate)
        edit_menu.addAction(self.act_delete)
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_settings)

        view_menu = menu.addMenu("Widok")
        view_menu.addAction(self.act_grid)
        view_menu.addAction(self.act_snap)
        view_menu.addSeparator()
        view_menu.addAction(self.act_live)
        view_menu.addSeparator()
        view_menu.addAction(self.data_dock.toggleViewAction())

        help_menu = menu.addMenu("Pomoc")
        help_menu.addAction(self.act_about)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Główny", self)
        toolbar.setObjectName("main_toolbar")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
        toolbar.addAction(self.act_new)
        toolbar.addAction(self.act_open)
        toolbar.addAction(self.act_save)
        toolbar.addSeparator()
        toolbar.addAction(self.act_undo)
        toolbar.addAction(self.act_redo)
        toolbar.addSeparator()
        toolbar.addAction(self.act_preview)
        toolbar.addAction(self.act_export_zpk)
        toolbar.addAction(self.act_export_zip)
        toolbar.addSeparator()
        toolbar.addAction(self.act_settings)
        self.addToolBar(toolbar)

    def _build_statusbar(self) -> None:
        self.status_hint = QLabel("Gotowe")
        self.status_coords = QLabel("")
        self.status_zoom = QLabel("")
        self.status_device = QLabel(f"{C.DEVICE['name']}  •  {C.DEVICE['width']} px")
        self.status_device.setObjectName("hint")
        self.statusBar().addWidget(self.status_hint, 1)
        self.statusBar().addPermanentWidget(self.status_coords)
        self.statusBar().addPermanentWidget(self.status_zoom)
        self.statusBar().addPermanentWidget(self.status_device)

    def _connect(self) -> None:
        self.canvas.selectionChanged.connect(self._on_selection)
        self.canvas.liveChanged.connect(self._on_live)
        self.canvas.editFinished.connect(self._commit)
        self.canvas.deleteRequested.connect(self.delete_selected)
        self.canvas.positionChanged.connect(self._on_position)
        self.canvas.zoomChanged.connect(self._on_zoom)
        self.canvas.statusMessage.connect(self._on_status)

        self.inspector.live.connect(self._on_live)
        self.inspector.committed.connect(self._commit)
        self.inspector.projectSettingsRequested.connect(self.project_settings)
        self.inspector.statusMessage.connect(self._on_status)

        self.layers.selected.connect(self._on_layer_selected)
        self.layers.changed.connect(self._on_layers_changed)
        self.layers.actionRequested.connect(self._on_layer_action)
        self.layers.statusMessage.connect(self._on_status)

        self.palette.addRequested.connect(self.add_element)
        self.palette.importImageRequested.connect(self.import_image)
        self.palette.importFontRequested.connect(self.import_font)
        self.palette.backgroundRequested.connect(self.import_background)

        self.preview_data.changed.connect(self._apply_preview_data)
        self.preview_data.statusMessage.connect(self._on_status)

    def _apply_project(self, project: Project, saved_root: Path | None) -> None:
        self.project = project
        self.saved_root = saved_root
        self.canvas.set_project(project)
        self.inspector.set_project(project)
        self.layers.set_project(project)
        self.preview_data.set_project(project)
        self.history.reset(project.snapshot())
        self.dirty = saved_root is None
        self._apply_preview_data()
        self._update_title()
        self._update_undo()

    def _apply_preview_data(self) -> None:
        moment = self.preview_data.moment()
        if moment is not None and self.act_live.isChecked():
            self.act_live.setChecked(False)
            self.canvas.set_live(False)
        self.canvas.set_preview_data(
            self.preview_data.samples(), moment, self.preview_data.weather_index()
        )

    def _on_selection(self, element: Element | None) -> None:
        self.inspector.set_element(element)
        self.layers.set_selected(element.id if element else None)
        if element is not None:
            self._on_status(f"Wybrano: {element.name}")

    def _on_layer_selected(self, element_id: str | None) -> None:
        self.canvas.select(element_id)

    def _on_layers_changed(self) -> None:
        self.canvas.refresh()
        self._commit()

    def _on_layer_action(self, action: str) -> None:
        if action == "duplicate":
            self.duplicate_selected()
        elif action == "delete":
            self.delete_selected()
        elif action == "up":
            self.layers.move_selected(-1)
        elif action == "down":
            self.layers.move_selected(1)

    def _on_live(self) -> None:
        self.inspector.sync_geometry()
        self.canvas.refresh()

    def _on_position(self, x: int, y: int) -> None:
        self.status_coords.setText("" if x < 0 else f"x: {x}   y: {y}")

    def _on_zoom(self, scale: float) -> None:
        self.status_zoom.setText(f"{round(scale * 100)} %")

    def _on_status(self, message: str) -> None:
        self.status_hint.setText(message)
        self.statusBar().showMessage(message, 4000)

    def _commit(self) -> None:
        if self.project is None:
            return
        self.history.push(self.project.snapshot())
        self.dirty = True
        self.preview_data.refresh_sources()
        self._update_title()
        self._update_undo()
        selected = self.canvas.selected_id
        self.layers.refresh()
        self.layers.set_selected(selected)

    def _update_undo(self) -> None:
        self.act_undo.setEnabled(self.history.can_undo)
        self.act_redo.setEnabled(self.history.can_redo)

    def _update_title(self) -> None:
        star = " *" if self.dirty else ""
        self.setWindowTitle(f"{self.project.name}{star} — {C.APP_TITLE}")

    def _apply_state(self, state: dict) -> None:
        selected = self.canvas.selected_id
        self.project.restore(state)
        valid = any(el.id == selected for el in self.project.elements)
        self.canvas.selected_id = selected if valid else None
        self.layers.refresh()
        self.preview_data.refresh_sources()
        self.canvas.select(self.canvas.selected_id)
        self.layers.set_selected(self.canvas.selected_id)
        self.canvas.refresh()
        self._update_undo()
        self.dirty = True
        self._update_title()

    def undo(self) -> None:
        state = self.history.undo()
        if state is not None:
            self._apply_state(state)
            self._on_status("Cofnięto")

    def redo(self) -> None:
        state = self.history.redo()
        if state is not None:
            self._apply_state(state)
            self._on_status("Ponowiono")

    def add_element(self, kind: str) -> None:
        if kind == "image":
            self.import_image()
            return
        element = self.project.add_element(kind)
        self.canvas.select(element.id)
        self.canvas.refresh()
        self._commit()
        self.canvas.setFocus()
        self._on_status(f"Dodano: {element.name}")

    def duplicate_selected(self) -> None:
        element = self.canvas.selected_element()
        if element is None:
            return
        clone = element.clone()
        self.project.elements.append(clone)
        self.canvas.select(clone.id)
        self.canvas.refresh()
        self._commit()
        self._on_status(f"Zduplikowano: {element.name}")

    def delete_selected(self) -> None:
        element = self.canvas.selected_element()
        if element is None:
            return
        self.project.elements = [el for el in self.project.elements if el.id != element.id]
        self.canvas.select(None)
        self.canvas.refresh()
        self._commit()
        self._on_status(f"Usunięto: {element.name}")

    def toggle_grid(self) -> None:
        self.canvas.set_grid(self.act_grid.isChecked())

    def toggle_snap(self) -> None:
        self.canvas.set_snap(self.act_snap.isChecked())

    def toggle_live(self) -> None:
        self.canvas.set_live(self.act_live.isChecked())
        self._on_status("Podgląd czasu rzeczywistego włączony" if self.act_live.isChecked() else "Podgląd czasu przykładowego")

    def _temp_root(self) -> Path:
        base = Path(tempfile.gettempdir()) / "WatchFaceStudio" / "projects"
        base.mkdir(parents=True, exist_ok=True)
        return base / f"{slugify(self.project.name)}-{uuid.uuid4().hex[:6]}"

    def new_project(self) -> None:
        dialog = NewProjectDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        name, template, author = dialog.values()
        root = self._temp_root()
        project = make_project(name, template, root)
        project.author = author or project.author
        try:
            project.save()
        except OSError as error:
            QMessageBox.critical(self, "Błąd", f"Nie udało się przygotować projektu:\n{error}")
            return
        self._apply_project(project, None)
        self._on_status(f"Utworzono nową tarczę: {name}")

    def open_project(self) -> None:
        start = str(self.settings.value("last_open_dir", str(C.PROJECTS_DIR)))
        folder = QFileDialog.getExistingDirectory(self, "Otwórz projekt", start)
        if not folder:
            return
        self._open_path(Path(folder))

    def _open_path(self, folder: Path) -> None:
        try:
            project = Project.load(folder)
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Błąd", f"Nie można otworzyć projektu:\n{error}")
            return
        if self.dirty:
            answer = QMessageBox.question(
                self,
                "Niezapisane zmiany",
                "Bieżący projekt ma niezapisane zmiany. Otworzyć inny projekt?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self._apply_project(project, folder)
        self.settings.setValue("last_open_dir", str(folder))
        self.add_recent(folder)
        self._on_status(f"Otwarto: {project.name}")

    def save_project(self) -> bool:
        if self.saved_root is None:
            return self.save_project_as()
        try:
            self.project.save(self.saved_root)
        except OSError as error:
            QMessageBox.critical(self, "Błąd zapisu", str(error))
            return False
        self.dirty = False
        self._update_title()
        self.add_recent(self.saved_root)
        self._on_status(f"Zapisano: {self.saved_root}")
        return True

    def save_project_as(self) -> bool:
        start = str(self.settings.value("save_dir", str(C.PROJECTS_DIR)))
        parent = QFileDialog.getExistingDirectory(self, "Wybierz folder dla projektu", start)
        if not parent:
            return False
        target = self.project.unique_root(Path(parent))
        old_root = self.project.root
        try:
            target.mkdir(parents=True, exist_ok=True)
            if old_root is not None and old_root != target and (old_root / "assets").exists():
                shutil.copytree(old_root / "assets", target / "assets", dirs_exist_ok=True)
            self.project.save(target)
        except OSError as error:
            QMessageBox.critical(self, "Błąd zapisu", str(error))
            return False
        self.saved_root = target
        self.dirty = False
        self.settings.setValue("save_dir", str(Path(parent)))
        self.add_recent(target)
        self._update_title()
        self._on_status(f"Zapisano: {target}")
        return True

    def project_settings(self) -> None:
        dialog = ProjectSettingsDialog(self.project, self)
        if dialog.exec() != QDialog.Accepted:
            return
        dialog.apply()
        self._commit()
        self.canvas.refresh()
        self.inspector.set_element(self.canvas.selected_element())
        self.layers.refresh()
        self.layers.set_selected(self.canvas.selected_id)
        self._on_status("Zapisano ustawienia projektu")

    def import_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importuj obraz",
            "",
            "Obrazy (*.png *.jpg *.jpeg *.bmp *.webp);;Wszystkie pliki (*)",
        )
        if not path:
            return
        try:
            rel = self.project.import_asset(Path(path), "icons")
        except OSError as error:
            QMessageBox.critical(self, "Błąd", f"Nie udało się zaimportować obrazu:\n{error}")
            return
        image = QImage(path)
        if image.isNull():
            QMessageBox.critical(self, "Błąd", "Nie można odczytać obrazu.")
            return
        width, height = image.width(), image.height()
        scale = min(1.0, 400 / max(width, height))
        element = self.project.add_element("image")
        element.props["src"] = rel
        element.w = max(8, int(width * scale))
        element.h = max(8, int(height * scale))
        element.x = int((C.DEVICE["width"] - element.w) / 2)
        element.y = int((C.DEVICE["height"] - element.h) / 2)
        element.name = f"Obraz: {Path(path).stem}"
        self.canvas.select(element.id)
        self.canvas.refresh()
        self._commit()
        self._on_status(f"Zaimportowano obraz: {Path(path).name}")

    def import_font(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Importuj czcionkę", "", "Czcionki (*.ttf *.otf)"
        )
        if not path:
            return
        try:
            rel = self.project.import_font(Path(path))
        except OSError as error:
            QMessageBox.critical(self, "Błąd", f"Nie udało się zaimportować czcionki:\n{error}")
            return
        font_file = self.project.asset_file(rel)
        missing = font_missing_polish(font_file) if font_file else ()
        if missing:
            QMessageBox.warning(
                self,
                "Brak polskich znaków",
                "Ta czcionka nie zawiera znaków: "
                + " ".join(missing)
                + ".\nNa zegarku mogą one nie wyświetlić się poprawnie.",
            )
        self._commit()
        self._on_status(f"Zaimportowano czcionkę: {Path(rel).name}")

    def import_background(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz tło",
            "",
            "Obrazy (*.png *.jpg *.jpeg *.bmp *.webp);;Wszystkie pliki (*)",
        )
        if not path:
            return
        try:
            rel = self.project.import_asset(Path(path), "background")
        except OSError as error:
            QMessageBox.critical(self, "Błąd", f"Nie udało się zaimportować tła:\n{error}")
            return
        self.project.background_image = rel
        self.canvas.refresh()
        self._commit()
        self._on_status(f"Ustawiono tło: {Path(path).name}")

    def _element_count_ok(self) -> bool:
        if not self.project.elements:
            QMessageBox.warning(
                self,
                "Pusta tarcza",
                "Dodaj przynajmniej jeden element przed eksportem.",
            )
            return False
        return True

    def _export_path(self, suffix: str, filter_text: str) -> Path | None:
        start = Path(self.settings.value("export_dir", str(C.PROJECTS_DIR)))
        default = start / f"{slugify(self.project.name)}{suffix}"
        path, _ = QFileDialog.getSaveFileName(self, "Eksport", str(default), filter_text)
        if not path:
            return None
        target = Path(path)
        if target.suffix.lower() != suffix:
            target = target.with_suffix(suffix)
        self.settings.setValue("export_dir", str(target.parent))
        return target

    def export_zpk(self) -> None:
        if not self._element_count_ok():
            return
        target = self._export_path(".zpk", "Tarcza ZeppOS (*.zpk)")
        if target is None:
            return
        QGuiApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            export_zpk(self.project, target)
        except Exception as error:  # noqa: BLE001
            QGuiApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Błąd eksportu", f"Nie udało się wyeksportować tarczy:\n{error}")
            return
        QGuiApplication.restoreOverrideCursor()
        self._on_status(f"Wyeksportowano: {target}")
        QMessageBox.information(
            self,
            "Eksport zakończony",
            f"Plik .zpk został zapisany:\n{target}\n\n"
            "Możesz go zainstalować przez Zepp App (tryb deweloperski) lub wysłać na amazfitwatchfaces.",
        )

    def export_zip(self) -> None:
        if not self._element_count_ok():
            return
        target = self._export_path(".zip", "Archiwum ZIP (*.zip)")
        if target is None:
            return
        QGuiApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            export_source_zip(self.project, target)
        except Exception as error:  # noqa: BLE001
            QGuiApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Błąd eksportu", f"Nie udało się wyeksportować ZIP:\n{error}")
            return
        QGuiApplication.restoreOverrideCursor()
        self._on_status(f"Wyeksportowano: {target}")
        QMessageBox.information(
            self,
            "Eksport zakończony",
            f"Archiwum ZIP gotowe:\n{target}\n\nMożesz je wysłać na amazfitwatchfaces.",
        )

    def show_preview(self) -> None:
        dialog = PreviewDialog(
            self.project,
            self,
            samples=self.preview_data.samples(),
            moment=self.preview_data.moment(),
            weather_index=self.preview_data.weather_index(),
        )
        dialog.exec()

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "O programie",
            f"<h3>{C.APP_NAME}</h3>"
            f"<p>Wersja {C.APP_VERSION}</p>"
            f"<p>Edytor tarcz dla <b>{C.DEVICE['name']}</b> "
            f"({C.DEVICE['width']} × {C.DEVICE['height']} px, ZeppOS {C.DEVICE['os_version']}).</p>"
            "<p>Eksport do .zpk oraz ZIP źródłowego. Podgląd można zapisać jako PNG lub animowany GIF.</p>",
        )

    def add_recent(self, folder: Path) -> None:
        items = self._recents()
        value = str(folder)
        items = [item for item in items if item != value]
        items.insert(0, value)
        self.settings.setValue("recent", items[:8])
        self.settings.setValue("last_project", value)
        self._load_recents()

    def _recents(self) -> list[str]:
        value = self.settings.value("recent", [])
        if isinstance(value, str):
            return [value] if value else []
        if value is None:
            return []
        return [str(item) for item in value]

    def _load_recents(self) -> None:
        self.recent_menu.clear()
        items = self._recents()
        if not items:
            action = self.recent_menu.addAction("(brak)")
            action.setEnabled(False)
            return
        for item in items:
            path = Path(item)
            action = self.recent_menu.addAction(f"{path.name}  —  {path}")
            action.triggered.connect(lambda _=False, p=path: self._open_path(p))

    def closeEvent(self, event) -> None:
        if self.dirty:
            answer = QMessageBox.question(
                self,
                "Niezapisane zmiany",
                "Zapisać zmiany przed zamknięciem?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if answer == QMessageBox.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.Save and not self.save_project():
                event.ignore()
                return
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/state", self.saveState())
        event.accept()
