from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QPainter,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..model import Project
from ..render import render_project
from .inspector import ColorButton

TEMPLATES = ["Cyfrowa", "Minimal", "Sportowa", "Pogodowa", "Pusta"]


class NewProjectDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nowa tarcza")
        self.setMinimumWidth(380)
        form = QFormLayout(self)
        self.name = QLineEdit("Moja tarcza")
        self.name.selectAll()
        self.template = QComboBox()
        for template in TEMPLATES:
            self.template.addItem(template)
        self.author = QLineEdit()
        self.author.setPlaceholderText("Twoje imię / nick")
        form.addRow("Nazwa", self.name)
        form.addRow("Szablon", self.template)
        form.addRow("Autor", self.author)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self) -> tuple[str, str, str]:
        return (
            self.name.text().strip() or "Moja tarcza",
            self.template.currentText(),
            self.author.text().strip(),
        )


class ProjectSettingsDialog(QDialog):
    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self._background = project.background_image
        self.setWindowTitle("Ustawienia projektu")
        self.setMinimumWidth(430)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.name = QLineEdit(project.name)
        self.author = QLineEdit(project.author)
        self.vender = QLineEdit(project.vender)
        self.app_id = QSpinBox()
        self.app_id.setRange(1000000, 99999999)
        self.app_id.setValue(int(project.app_id))
        self.version_name = QLineEdit(project.version_name)
        self.version_code = QSpinBox()
        self.version_code.setRange(1, 99999)
        self.version_code.setValue(int(project.version_code))
        self.description = QPlainTextEdit(project.description)
        self.description.setFixedHeight(64)

        form.addRow("Nazwa", self.name)
        form.addRow("Autor", self.author)
        form.addRow("Vender", self.vender)
        form.addRow("App ID", self.app_id)
        form.addRow("Wersja", self.version_name)
        form.addRow("Kod wersji", self.version_code)
        form.addRow("Opis", self.description)

        self.background = ColorButton(project.background_color)
        form.addRow("Kolor tła", self.background)

        bg_row = QWidget()
        bg_layout = QHBoxLayout(bg_row)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        self.bg_label = QLabel(Path(self._background).name or "brak")
        self.bg_label.setObjectName("hint")
        bg_layout.addWidget(self.bg_label, 1)
        pick = QPushButton("Wybierz…")
        pick.clicked.connect(self._pick_background)
        clear = QPushButton("Usuń")
        clear.clicked.connect(self._clear_background)
        bg_layout.addWidget(pick)
        bg_layout.addWidget(clear)
        form.addRow("Tło (obraz)", bg_row)

        self.aod = QCheckBox("Proste AOD (godzina na wygaszonym ekranie)")
        self.aod.setChecked(project.aod_simple)
        form.addRow("", self.aod)
        self.aod_color = ColorButton(project.aod_color)
        form.addRow("Kolor AOD", self.aod_color)

        hint = QLabel(
            "App ID musi być unikalne. Po zmianie tła pamiętaj, że obraz jest rozciągany do 466 × 466 px."
        )
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pick_background(self) -> None:
        if self.project.root is None:
            QMessageBox.warning(self, "Brak projektu", "Najpierw zapisz projekt na dysku.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz tło", "", "Obrazy (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        try:
            self._background = self.project.import_asset(Path(path), "background")
        except OSError as error:
            QMessageBox.critical(self, "Błąd", f"Nie udało się zaimportować tła:\n{error}")
            return
        self.bg_label.setText(Path(path).name)

    def _clear_background(self) -> None:
        self._background = ""
        self.bg_label.setText("brak")

    def apply(self) -> None:
        self.project.name = self.name.text().strip() or "Moja tarcza"
        self.project.author = self.author.text().strip()
        self.project.vender = self.vender.text().strip() or "zepp"
        self.project.app_id = int(self.app_id.value())
        self.project.version_name = self.version_name.text().strip() or "1.0.0"
        self.project.version_code = int(self.version_code.value())
        self.project.description = self.description.toPlainText().strip()
        self.project.background_color = self.background.value()
        self.project.background_image = self._background
        self.project.aod_simple = self.aod.isChecked()
        self.project.aod_color = self.aod_color.value()


class PreviewWidget(QWidget):
    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.live = True
        self.samples: dict[str, tuple[str, float]] | None = None
        self.weather_index: int | None = None
        self.moment = None
        self.setMinimumSize(320, 320)

    def set_live(self, live: bool) -> None:
        self.live = live
        if live:
            self.moment = None
        self.update()

    def randomize(self) -> None:
        import random

        from .. import constants as C
        from ..render import random_moment, random_samples

        rng = random.Random()
        self.samples = random_samples(rng)
        self.weather_index = rng.randrange(len(C.WEATHER_FILES))
        self.moment = random_moment(rng)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#0a0d13"))
        size = min(self.width(), self.height()) - 24
        if size < 40:
            painter.end()
            return
        left = (self.width() - size) / 2
        top = (self.height() - size) / 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1a2130"))
        painter.drawEllipse(int(left - 5), int(top - 5), size + 10, size + 10)
        from PySide6.QtCore import QRectF

        render_project(
            painter,
            self.project,
            QRectF(left, top, size, size),
            live=self.live,
            preview=True,
            clip_circle=True,
            now=self.moment,
            samples=self.samples,
            weather_index=self.weather_index,
        )
        painter.end()

    def sizeHint(self) -> QSize:
        return QSize(466, 466)


class PreviewDialog(QDialog):
    def __init__(
        self,
        project: Project,
        parent: QWidget | None = None,
        *,
        samples: dict[str, tuple[str, float]] | None = None,
        moment: object | None = None,
        weather_index: int | None = None,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(f"Podgląd — {project.name}")
        self.resize(760, 720)

        layout = QVBoxLayout(self)
        self.widget = PreviewWidget(project)
        self.widget.samples = samples
        self.widget.weather_index = weather_index
        layout.addWidget(self.widget, 1)

        controls = QHBoxLayout()
        live = QCheckBox("Czas rzeczywisty")
        live.setChecked(moment is None)
        live.toggled.connect(self.widget.set_live)
        self.live = live
        controls.addWidget(live)
        if moment is not None:
            self.widget.live = False
            self.widget.moment = moment
        randomize = QPushButton("Losuj dane")
        randomize.setToolTip("Wypełnia podgląd losowymi wartościami (godzina, data, kroki, tętno itd.)")
        randomize.clicked.connect(self._randomize)
        controls.addWidget(randomize)
        controls.addStretch(1)
        save = QPushButton("Zapisz PNG…")
        save.clicked.connect(self._save)
        gif = QPushButton("Zapisz GIF…")
        gif.clicked.connect(self._save_gif)
        close = QPushButton("Zamknij")
        close.clicked.connect(self.accept)
        controls.addWidget(save)
        controls.addWidget(gif)
        controls.addWidget(close)
        layout.addLayout(controls)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.widget.update)
        self._timer.start()

    def _randomize(self) -> None:
        self.live.setChecked(False)
        self.widget.randomize()

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz podgląd", f"{self.project.name}.png", "Obraz PNG (*.png)"
        )
        if not path:
            return
        from ..render import make_image

        image = make_image(
            self.project,
            466,
            live=self.widget.live,
            preview=True,
            now=self.widget.moment,
            samples=self.widget.samples,
            weather_index=self.widget.weather_index,
        )
        if image.save(path, "PNG"):
            QMessageBox.information(self, "Zapisano", f"Podgląd zapisany:\n{path}")
        else:
            QMessageBox.critical(self, "Błąd", "Nie udało się zapisać obrazu.")

    def _save_gif(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz animację GIF", f"{self.project.name}.gif", "Animacja GIF (*.gif)"
        )
        if not path:
            return
        from PySide6.QtGui import QGuiApplication

        from ..render import save_gif

        QGuiApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            ok = save_gif(self.project, Path(path), size=466, frames=24, frame_ms=90)
        except Exception as error:  # noqa: BLE001
            QGuiApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Błąd", f"Nie udało się zapisać GIF:\n{error}")
            return
        QGuiApplication.restoreOverrideCursor()
        if ok:
            QMessageBox.information(
                self,
                "Zapisano",
                f"Animowany GIF zapisany:\n{path}\n\n"
                "Klatki pokazują losowe dane przykładowe (godzina, data, kroki, tętno itd.).",
            )
        else:
            QMessageBox.critical(self, "Błąd", "Nie udało się zapisać animacji GIF.")
