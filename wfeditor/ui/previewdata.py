from __future__ import annotations

import datetime as _dt
import random

from PySide6.QtCore import QTime, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C
from ..model import Project
from ..render import random_moment, random_samples, sample_entry

# Kolejność pól jest stała (grupy z constants), a pokazujemy tylko źródła,
# których projekt faktycznie używa.
_SOURCE_ORDER: list[str] = [key for keys in C.DATA_GROUPS.values() for key in keys]
_ELEMENT_SOURCES = ("data", "progress_ring", "progress_bar")


def used_sources(project: Project) -> list[str]:
    """Źródła danych użyte przez elementy projektu (w kolejności z panelu)."""
    found: set[str] = set()
    for el in project.elements:
        if el.type in _ELEMENT_SOURCES:
            source = str(el.props.get("source", ""))
            if source in C.DATA_SOURCES:
                found.add(source)
    return [key for key in _SOURCE_ORDER if key in found]


class PreviewDataPanel(QWidget):
    """Własne dane podglądu: losowanie, godzina, pogoda i wartości źródeł."""

    changed = Signal()
    statusMessage = Signal(str)

    def __init__(self, project: Project | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self._fields: dict[str, QLineEdit] = {}
        self._rows: dict[str, QWidget] = {}
        self._empty_label: QLabel | None = None
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(8)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        self.random_button = QPushButton("Losuj dane")
        self.random_button.setToolTip(
            "Wypełnia podgląd losowymi wartościami (godzina, data, kroki, tętno itd.)"
        )
        self.random_button.clicked.connect(self.randomize)
        self.clear_button = QPushButton("Wyczyść")
        self.clear_button.setToolTip("Przywraca domyślne wartości przykładowe")
        self.clear_button.clicked.connect(self.clear)
        buttons.addWidget(self.random_button, 1)
        buttons.addWidget(self.clear_button)
        layout.addLayout(buttons)

        top = QFormLayout()
        top.setLabelAlignment(Qt.AlignLeft)
        top.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        self.time_edit.setTime(QTime(0, 0, 0))
        self.time_edit.setToolTip(
            "Godzina pokazywana przez podgląd. Zostaw pole puste, aby użyć "
            "przykładowej godziny lub czasu rzeczywistego."
        )
        self.time_edit.setSpecialValueText(" ")
        self.time_edit.setMinimumTime(QTime(0, 0, 0))
        # 00:00:00 oznacza „brak nadpisania” - pole pokazuje wtedy pustkę.
        self.time_edit.timeChanged.connect(self._on_changed)
        top.addRow("Godzina", self.time_edit)

        self.weather_combo = QComboBox()
        self.weather_combo.addItem("Domyślnie", None)
        for index, label in enumerate(C.WEATHER_LABELS_PL):
            self.weather_combo.addItem(label, index)
        self.weather_combo.currentIndexChanged.connect(self._on_changed)
        top.addRow("Ikona pogody", self.weather_combo)
        layout.addLayout(top)

        box = QGroupBox("Własne wartości")
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(8, 8, 8, 8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._form_host = QWidget()
        self._form = QFormLayout(self._form_host)
        self._form.setContentsMargins(0, 0, 0, 0)
        self._form.setLabelAlignment(Qt.AlignLeft)
        self._form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        scroll.setWidget(self._form_host)
        box_layout.addWidget(scroll)
        layout.addWidget(box, 1)

        self.hint = QLabel(
            "Wpisz własne wartości, aby zobaczyć je na tarczy. Puste pole oznacza "
            "wartość domyślną."
        )
        self.hint.setWordWrap(True)
        self.hint.setObjectName("hint")
        layout.addWidget(self.hint)

        self.refresh_sources()

    def set_project(self, project: Project) -> None:
        self.project = project
        self.refresh_sources()

    def refresh_sources(self) -> None:
        """Odbudowuje pola dla źródeł używanych w projekcie."""
        if self.project is None:
            return
        sources = used_sources(self.project)
        if list(self._fields.keys()) == sources and (sources or self._empty_label is not None):
            return
        for _source, row in list(self._rows.items()):
            self._form.removeRow(row)
        self._rows = {}
        self._fields = {}
        if self._empty_label is not None:
            self._form.removeRow(self._empty_label)
            self._empty_label = None
        if not sources:
            self._empty_label = QLabel("Ten projekt nie używa jeszcze danych z czujników.")
            self._empty_label.setWordWrap(True)
            self._empty_label.setObjectName("hint")
            self._form.addRow(self._empty_label)
            return
        for source in sources:
            info = C.DATA_SOURCES.get(source, {})
            field = QLineEdit()
            unit = str(info.get("unit", "") or "")
            sample = str(info.get("sample", "") or "")
            placeholder = f"np. {sample}" + (f" {unit}" if unit else "")
            field.setPlaceholderText(placeholder)
            field.setClearButtonEnabled(True)
            field.textChanged.connect(self._on_changed)
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            label = QLabel(str(info.get("label", source)))
            label.setMinimumWidth(120)
            row_layout.addWidget(label)
            row_layout.addWidget(field, 1)
            self._fields[source] = field
            self._rows[source] = row
            self._form.addRow(row)

    def randomize(self) -> None:
        rng = random.Random()
        samples = random_samples(rng)
        moment = random_moment(rng)
        if moment.hour == 0 and moment.minute == 0 and moment.second == 0:
            # QTimeEdit traktuje 00:00:00 jako „brak nadpisania”.
            moment = moment.replace(second=1)
        weather = rng.randrange(len(C.WEATHER_FILES))

        self._loading = True
        for source, field in self._fields.items():
            if source in samples:
                field.setText(samples[source][0])
        self.time_edit.setTime(QTime(moment.hour, moment.minute, moment.second))
        index = self.weather_combo.findData(weather)
        if index >= 0:
            self.weather_combo.setCurrentIndex(index)
        self._loading = False
        self.changed.emit()
        self.statusMessage.emit("Wylosowano dane podglądu")

    def clear(self) -> None:
        self._loading = True
        for field in self._fields.values():
            field.clear()
        self.time_edit.setTime(QTime(0, 0, 0))
        self.weather_combo.setCurrentIndex(0)
        self._loading = False
        self.changed.emit()
        self.statusMessage.emit("Przywrócono domyślne dane podglądu")

    def samples(self) -> dict[str, tuple[str, float]] | None:
        result: dict[str, tuple[str, float]] = {}
        for source, field in self._fields.items():
            text = field.text().strip()
            if text:
                result[source] = sample_entry(source, text)
        return result or None

    def moment(self) -> _dt.datetime | None:
        value = self.time_edit.time()
        if value == QTime(0, 0, 0):
            return None
        today = _dt.date.today()
        return _dt.datetime(
            today.year, today.month, today.day, value.hour(), value.minute(), value.second()
        )

    def weather_index(self) -> int | None:
        data = self.weather_combo.currentData()
        return int(data) if data is not None else None

    def _on_changed(self, *_args) -> None:
        if self._loading:
            return
        self.changed.emit()
