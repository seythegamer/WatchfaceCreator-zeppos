from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C

ELEMENT_BUTTONS = [
    ("time", "Godzina", "Duży, aktualizowany zegar"),
    ("date", "Data", "Data z wybranym formatem"),
    ("text", "Tekst", "Statyczny napis"),
    ("data", "Dane", "Kroki, puls, bateria, pogoda…"),
    ("progress_ring", "Pierścień", "Postęp w formie okręgu"),
    ("progress_bar", "Pasek", "Postęp w formie paska"),
    ("weather_icon", "Pogoda", "Ikona aktualnej pogody"),
    ("analog_hands", "Wskazówki", "Analogowe wskazówki z wymiennymi obrazami"),
    ("status", "Status", "Bluetooth, DND, blokada, alarm"),
    ("image", "Obraz", "Własna grafika PNG"),
    ("shortcut", "Skrót", "Dotknięcie otwiera aplikację"),
]


class Palette(QWidget):
    addRequested = Signal(str)
    importImageRequested = Signal()
    importFontRequested = Signal()
    backgroundRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        elements = QGroupBox("Dodaj element")
        grid = QGridLayout(elements)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(6)
        for index, (kind, label, tip) in enumerate(ELEMENT_BUTTONS):
            button = QPushButton(label)
            button.setToolTip(tip)
            button.setMinimumHeight(34)
            button.clicked.connect(lambda _=False, k=kind: self.addRequested.emit(k))
            grid.addWidget(button, index // 2, index % 2)
        layout.addWidget(elements)

        assets = QGroupBox("Zasoby")
        assets_layout = QVBoxLayout(assets)
        assets_layout.setContentsMargins(8, 8, 8, 8)
        assets_layout.setSpacing(6)
        image = QPushButton("Importuj obraz…")
        image.clicked.connect(self.importImageRequested.emit)
        background = QPushButton("Tło z pliku…")
        background.clicked.connect(self.backgroundRequested.emit)
        font = QPushButton("Importuj czcionkę…")
        font.clicked.connect(self.importFontRequested.emit)
        assets_layout.addWidget(image)
        assets_layout.addWidget(background)
        assets_layout.addWidget(font)
        layout.addWidget(assets)

        hint = QLabel(
            "Wskazówka: przytrzymaj Ctrl podczas przeciągania, aby wyłączyć przyciąganie do siatki. "
            "Shift + strzałki przesuwają o 10 px."
        )
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        layout.addWidget(hint)
        layout.addStretch(1)

        device = QLabel(
            f"{C.DEVICE['name']}\n"
            f"{C.DEVICE['width']} × {C.DEVICE['height']} px  •  ZeppOS {C.DEVICE['os_version']}"
        )
        device.setObjectName("hint")
        layout.addWidget(device)
