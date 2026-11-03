from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .. import constants as C
from ..model import (
    ROTATION_UNSUPPORTED_HINT,
    TYPE_LABELS,
    Element,
    Project,
    apply_content_scale,
    center_element,
    clear_content_base,
    ensure_content_base,
    normalize_rotation,
    supports_content_scale,
    supports_rotation,
)
from ..render import font_missing_polish


def _font_items(project: Project) -> list[tuple[str, str]]:
    items = list(C.FONT_CHOICES)
    seen = {value for _, value in items}
    if project.root is not None:
        folder = project.root / "assets" / "fonts"
        if folder.exists():
            for path in sorted(folder.iterdir()):
                if path.suffix.lower() in (".ttf", ".otf"):
                    rel = f"fonts/{path.name}"
                    if rel not in seen:
                        label = path.stem
                        if font_missing_polish(path):
                            label += " (brak PL)"
                        items.append((label, rel))
                        seen.add(rel)
    return items


def _add_data_combo(combo: QComboBox, keys: list[str]) -> None:
    for key in keys:
        combo.addItem(C.DATA_SOURCES[key]["label"], key)


def _select_data(combo: QComboBox, value: str) -> None:
    index = combo.findData(value)
    if index < 0:
        combo.addItem(str(value), value)
        index = combo.count() - 1
    combo.setCurrentIndex(index)


class ColorButton(QPushButton):
    colorChanged = Signal(str)

    def __init__(self, value: str = "#FFFFFF", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = value or "#FFFFFF"
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(26)
        self.clicked.connect(self._pick)
        self._update_style()

    def value(self) -> str:
        return self._value

    def set_value(self, value: str) -> None:
        self._value = value or "#FFFFFF"
        self._update_style()

    def _update_style(self) -> None:
        color = QColor(self._value)
        text = "#000000" if color.lightness() > 140 else "#FFFFFF"
        self.setText(self._value.upper())
        self.setStyleSheet(
            "QPushButton {"
            f"background: {self._value}; color: {text};"
            "border: 1px solid #3a4b66; border-radius: 4px; font-weight: 600;"
            "}"
        )

    def _pick(self) -> None:
        color = QColorDialog.getColor(QColor(self._value), self, "Wybierz kolor")
        if color.isValid():
            self._value = color.name().upper()
            self._update_style()
            self.colorChanged.emit(self._value)


class Inspector(QScrollArea):
    live = Signal()
    committed = Signal()
    projectSettingsRequested = Signal()
    statusMessage = Signal(str)

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.element: Element | None = None
        self._loading = False
        self._geom_spins: dict[str, QSpinBox] = {}
        self._prop_spins: dict[str, QSpinBox] = {}
        self._rotation_spin: QSpinBox | None = None
        self._content_label: QLabel | None = None
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._commit_timer = QTimer(self)
        self._commit_timer.setSingleShot(True)
        self._commit_timer.setInterval(350)
        self._commit_timer.timeout.connect(self.committed.emit)
        self._rebuild()

    def set_project(self, project: Project) -> None:
        self.project = project
        self.element = None
        self._rebuild()

    def set_element(self, element: Element | None) -> None:
        if element is None:
            self.element = None
            self._rebuild()
            return
        if self.element is element:
            self.sync_geometry()
            return
        self.element = element
        self._rebuild()

    def _rebuild(self) -> None:
        self._prop_spins = {}
        self._rotation_spin = None
        self._content_label = None
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        if self.element is None:
            layout.addWidget(self._welcome())
            layout.addStretch(1)
            self.setWidget(body)
            return

        layout.addWidget(self._header())
        layout.addWidget(self._common_group())
        specific = self._specific_group()
        if specific is not None:
            layout.addWidget(specific)
        layout.addStretch(1)
        self.setWidget(body)

    def _welcome(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel(self.project.name)
        title.setObjectName("title")
        title.setWordWrap(True)
        layout.addWidget(title)
        author = QLabel(self.project.author or "brak autora")
        author.setObjectName("hint")
        layout.addWidget(author)
        hint = QLabel(
            "Kliknij element na tarczy albo na liście warstw, aby edytować jego właściwości.\n\n"
            "Przeciągaj, aby przesuwać. Uchwyty w narożnikach zmieniają rozmiar. "
            "Strzałki przesuwają o 1 px (Shift + strzałka o 10 px).\n\n"
            "Opcja „Skaluj zawartość razem z ramką” sprawia, że uchwyty zmieniają "
            "także rozmiar tekstu lub obrazu (czerwona ramka)."
        )
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        layout.addWidget(hint)
        settings = QPushButton("Ustawienia projektu…")
        settings.clicked.connect(self.projectSettingsRequested.emit)
        layout.addWidget(settings)
        return box

    def _header(self) -> QWidget:
        el = self.element
        assert el is not None
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(TYPE_LABELS.get(el.type, el.type))
        label.setObjectName("title")
        layout.addWidget(label)
        layout.addStretch(1)
        self._name_edit = QLineEdit(el.name)
        self._name_edit.setPlaceholderText("Nazwa")
        self._name_edit.editingFinished.connect(self._apply_name)
        layout.addWidget(self._name_edit, 1)
        return row

    def _common_group(self) -> QWidget:
        el = self.element
        assert el is not None
        group = QGroupBox("Położenie i rozmiar")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        row = QWidget()
        grid = QHBoxLayout(row)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        self._geom_spins = {}
        for key, label in (("x", "X"), ("y", "Y"), ("w", "Sz"), ("h", "Wy")):
            spin = QSpinBox()
            spin.setRange(0, 1000)
            spin.setMaximumWidth(72)
            value = getattr(el, key)
            spin.setValue(int(value))
            spin.valueChanged.connect(lambda v, k=key: self._apply_geometry(k, v))
            self._geom_spins[key] = spin
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(1)
            caption = QLabel(label)
            caption.setObjectName("hint")
            cell_layout.addWidget(caption)
            cell_layout.addWidget(spin)
            grid.addWidget(cell)
        form.addRow(row)

        center_row = QWidget()
        center_layout = QHBoxLayout(center_row)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(6)
        for label, horizontal, vertical, tip in (
            ("Poziomo", True, False, "Wyśrodkuj element w poziomie"),
            ("Pionowo", False, True, "Wyśrodkuj element w pionie"),
            ("Oba", True, True, "Wyśrodkuj element w obu osiach"),
        ):
            button = QPushButton(label)
            button.setToolTip(tip)
            button.setMinimumHeight(28)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(
                lambda _=False, h=horizontal, v=vertical: self._center_element(h, v)
            )
            center_layout.addWidget(button)
        form.addRow("Wyśrodkuj", center_row)

        flags = QWidget()
        flags_layout = QHBoxLayout(flags)
        flags_layout.setContentsMargins(0, 0, 0, 0)
        visible = QCheckBox("Widoczny")
        visible.setChecked(el.visible)
        visible.toggled.connect(self._apply_visible)
        locked = QCheckBox("Zablokowany")
        locked.setChecked(el.locked)
        locked.toggled.connect(self._apply_locked)
        flags_layout.addWidget(visible)
        flags_layout.addWidget(locked)
        flags_layout.addStretch(1)
        form.addRow(flags)

        scale = QCheckBox("Skaluj zawartość razem z ramką")
        scale.setChecked(bool(el.scale_content))
        scale.setEnabled(supports_content_scale(el.type))
        scale.setToolTip(
            "Gdy zaznaczone, ramka jest czerwona, a uchwyty zmieniają rozmiar "
            "tekstu lub obrazu. Gdy odznaczone, zmienia się tylko obszar widgetu."
        )
        scale.toggled.connect(self._apply_scale_content)
        form.addRow(scale)
        if supports_rotation(el.type):
            rotation = self._spin(int(el.rotation or 0), -180, 180, "°")
            rotation.setToolTip(
                "Obrót elementu wokół jego środka (Shift przy uchwycie = co 15°). "
                "Dodatnie wartości obracają zgodnie z ruchem wskazówek zegara."
            )
            rotation.valueChanged.connect(self._apply_rotation)
            self._rotation_spin = rotation
            form.addRow("Obrót", rotation)
            if el.type == "text":
                hint = QLabel(
                    "Tekst z obrotem jest zapisywany na zegarku jako obraz "
                    "(wygląda tak samo jak w edytorze)."
                )
                hint.setWordWrap(True)
                hint.setObjectName("hint")
                form.addRow("", hint)
        else:
            self._rotation_spin = None
            if el.type in ("time", "date", "data"):
                hint = QLabel(ROTATION_UNSUPPORTED_HINT)
                hint.setWordWrap(True)
                hint.setObjectName("hint")
                form.addRow("Obrót", hint)
        if supports_content_scale(el.type):
            hint = QLabel(
                "Czerwona ramka = skalowanie zawartości. Po odznaczeniu "
                "rozmiar tekstu/obrazu pozostaje zapisany."
            )
            hint.setWordWrap(True)
            hint.setObjectName("hint")
            form.addRow("", hint)
        if el.type in ("image", "shortcut"):
            width, height = el.render_size()
            self._content_label = QLabel(f"Zawartość: {width} × {height} px")
            self._content_label.setObjectName("hint")
            form.addRow("", self._content_label)
        return group

    def _specific_group(self) -> QWidget | None:
        el = self.element
        assert el is not None
        builders = {
            "image": self._group_image,
            "text": self._group_text,
            "time": self._group_time,
            "date": self._group_date,
            "data": self._group_data,
            "weather_icon": self._group_weather,
            "progress_ring": self._group_ring,
            "progress_bar": self._group_bar,
            "shortcut": self._group_shortcut,
            "status": self._group_status,
            "analog_hands": self._group_hands,
        }
        builder = builders.get(el.type)
        return builder() if builder else None

    def _form(self, title: str) -> tuple[QGroupBox, QFormLayout]:
        group = QGroupBox(title)
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        return group, form

    def _wide_combo(self, combo: QComboBox) -> QComboBox:
        """Combo, które nie rozpycha panelu i nie wypycha przycisków poza ekran."""
        combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(8)
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return combo

    def _file_picker(
        self,
        button_text: str,
        slot,
        *,
        clear_text: str = "",
        clear_slot=None,
        current: str = "",
    ) -> QWidget:
        """Pole wyboru pliku: opis u góry, przyciski na całą szerokość panelu."""
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        if current:
            label = QLabel(current)
            label.setObjectName("hint")
            label.setWordWrap(True)
            # Długa nazwa pliku nie może rozpychać całego panelu.
            label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            layout.addWidget(label)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        pick = QPushButton(button_text)
        pick.setMinimumHeight(30)
        pick.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pick.clicked.connect(slot)
        row.addWidget(pick, 1)
        if clear_slot is not None:
            clear = QPushButton(clear_text or "Domyślna")
            clear.setMinimumHeight(30)
            clear.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            clear.clicked.connect(clear_slot)
            row.addWidget(clear)
        layout.addLayout(row)
        return box

    def _apply(self, key: str, value, rebuild: bool = False) -> None:
        if self._loading or self.element is None:
            return
        self.element.props[key] = value
        if key == "size":
            # Ręczna zmiana rozmiaru tekstu/ikony jest nowym punktem odniesienia.
            clear_content_base(self.element)
        self.live.emit()
        self._commit_timer.start()
        if rebuild:
            QTimer.singleShot(0, self._rebuild)

    def _apply_geometry(self, key: str, value: int) -> None:
        if self._loading or self.element is None:
            return
        el = self.element
        value = int(value)
        if key in ("w", "h"):
            if el.scale_content:
                ensure_content_base(el)
            else:
                # Utrwal obecny rozmiar zawartości, zanim zmieni się ramka.
                el.freeze_content_size()
        setattr(el, key, value)
        if key in ("w", "h") and el.scale_content:
            apply_content_scale(el, el.w, el.h)
        self.live.emit()
        self._commit_timer.start()

    def _apply_scale_content(self, value: bool) -> None:
        if self._loading or self.element is None:
            return
        self.element.scale_content = bool(value)
        clear_content_base(self.element)
        self.live.emit()
        self.committed.emit()

    def _center_element(self, horizontal: bool, vertical: bool) -> None:
        if self.element is None:
            return
        center_element(self.element, horizontal, vertical)
        self.sync_geometry()
        self.live.emit()
        self.committed.emit()
        self.statusMessage.emit("Wyśrodkowano element")

    def _apply_rotation(self, value: int) -> None:
        if self._loading or self.element is None:
            return
        self.element.rotation = normalize_rotation(value)
        self.live.emit()
        self._commit_timer.start()

    def _apply_name(self) -> None:
        if self.element is None:
            return
        name = self._name_edit.text().strip()
        if name and name != self.element.name:
            self.element.name = name
            self.live.emit()
            self.committed.emit()

    def _apply_visible(self, value: bool) -> None:
        if self._loading or self.element is None:
            return
        self.element.visible = bool(value)
        self.live.emit()
        self.committed.emit()

    def _apply_locked(self, value: bool) -> None:
        if self._loading or self.element is None:
            return
        self.element.locked = bool(value)
        self.live.emit()
        self.committed.emit()

    def sync_geometry(self) -> None:
        if self.element is None:
            return
        self._loading = True
        for key, spin in self._geom_spins.items():
            spin.setValue(int(getattr(self.element, key)))
        if self._rotation_spin is not None:
            self._rotation_spin.setValue(int(self.element.rotation))
        for key, spin in self._prop_spins.items():
            value = self.element.props.get(key)
            if value is not None:
                spin.setValue(int(value))
        if self._content_label is not None and self.element.type in ("image", "shortcut"):
            width, height = self.element.render_size()
            self._content_label.setText(f"Zawartość: {width} × {height} px")
        self._loading = False

    def _spin(self, value: int, low: int, high: int, suffix: str = "") -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(low, high)
        spin.setValue(int(value))
        if suffix:
            spin.setSuffix(suffix)
        return spin

    def _prop_spin(
        self, key: str, value: int, low: int, high: int, suffix: str = ""
    ) -> QSpinBox:
        spin = self._spin(value, low, high, suffix)
        self._prop_spins[key] = spin
        return spin

    def _font_combo(self, value: str) -> QComboBox:
        combo = self._wide_combo(QComboBox())
        for label, key in _font_items(self.project):
            combo.addItem(label, key)
        _select_data(combo, value or "")
        combo.currentIndexChanged.connect(
            lambda _=0, c=combo: self._apply("font", c.currentData() or "")
        )
        return combo

    def _color_button(self, key: str, value: str) -> ColorButton:
        button = ColorButton(value)
        button.colorChanged.connect(lambda color, k=key: self._apply(k, color))
        return button

    def _align_combo(self, key: str, value: str) -> QComboBox:
        combo = self._wide_combo(QComboBox())
        for label, code in (("Lewo", "left"), ("Środek", "center"), ("Prawo", "right")):
            combo.addItem(label, code)
        _select_data(combo, value)
        combo.currentIndexChanged.connect(
            lambda _=0, c=combo, k=key: self._apply(k, c.currentData())
        )
        return combo

    def _valign_combo(self, value: str) -> QComboBox:
        combo = self._wide_combo(QComboBox())
        for label, code in (("Góra", "top"), ("Środek", "center"), ("Dół", "bottom")):
            combo.addItem(label, code)
        _select_data(combo, value)
        combo.currentIndexChanged.connect(
            lambda _=0, c=combo: self._apply("valign", c.currentData())
        )
        return combo

    def _group_image(self) -> QWidget:
        el = self.element
        assert el is not None
        group, form = self._form("Obraz")

        current = Path(str(el.props.get("src", ""))).name or ""
        picker = self._file_picker(
            "Wybierz obraz…",
            self._pick_image,
            clear_text="Usuń",
            clear_slot=lambda: self._apply("src", ""),
            current=current or "brak pliku",
        )
        form.addRow(picker)

        opacity = self._spin(int(el.props.get("opacity", 255)), 0, 255, " / 255")
        opacity.valueChanged.connect(lambda v: self._apply("opacity", int(v)))
        form.addRow("Krycie", opacity)
        return group

    def _group_text(self) -> QWidget:
        el = self.element
        assert el is not None
        group, form = self._form("Tekst")
        text = QPlainTextEdit(str(el.props.get("text", "")))
        text.setFixedHeight(58)
        text.textChanged.connect(lambda: self._apply("text", text.toPlainText()))
        form.addRow("Treść", text)
        form.addRow("Czcionka", self._font_combo(str(el.props.get("font", ""))))

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        size = self._prop_spin("size", int(el.props.get("size", 32)), 4, 300, " px")
        size.valueChanged.connect(lambda v: self._apply("size", int(v)))
        spacing = self._spin(int(el.props.get("spacing", 0)), -20, 60, " px")
        spacing.valueChanged.connect(lambda v: self._apply("spacing", int(v)))
        row_layout.addWidget(size)
        row_layout.addWidget(spacing)
        form.addRow("Rozmiar / odstęp", row)

        form.addRow("Kolor", self._color_button("color", str(el.props.get("color", "#FFFFFF"))))
        form.addRow("Wyrównanie", self._align_combo("align", str(el.props.get("align", "center"))))
        form.addRow("Pion", self._valign_combo(str(el.props.get("valign", "center"))))
        return group

    def _group_time(self) -> QWidget:
        el = self.element
        assert el is not None
        group, form = self._form("Godzina")
        form.addRow("Czcionka", self._font_combo(str(el.props.get("font", ""))))
        size = self._prop_spin("size", int(el.props.get("size", 96)), 8, 300, " px")
        size.valueChanged.connect(lambda v: self._apply("size", int(v)))
        form.addRow("Rozmiar", size)
        form.addRow("Kolor", self._color_button("color", str(el.props.get("color", "#FFFFFF"))))
        form.addRow("Wyrównanie", self._align_combo("align", str(el.props.get("align", "center"))))
        form.addRow("Pion", self._valign_combo(str(el.props.get("valign", "center"))))

        fmt = self._wide_combo(QComboBox())
        fmt.addItem("24 godziny", "24")
        fmt.addItem("12 godzin", "12")
        fmt.addItem("Jak w zegarku", "auto")
        _select_data(fmt, str(el.props.get("format", "24")))
        fmt.currentIndexChanged.connect(lambda _=0, c=fmt: self._apply("format", c.currentData()))
        form.addRow("Format", fmt)

        display = self._wide_combo(QComboBox())
        display.setEditable(True)
        for preset in (
            "HH:MM",
            "HH:MM:SS",
            "HH",
            "MM",
            "HH:MM A",
            "HH.MM",
            "HH:MM:SS A",
        ):
            display.addItem(preset)
        display.setCurrentText(str(el.props.get("display", "HH:MM")))
        display.currentTextChanged.connect(lambda value: self._apply("display", value))
        form.addRow("Wyświetlanie", display)
        hint = QLabel(
            "HH = godzina, MM = minuty, SS = sekundy, A = AM/PM (możesz też "
            "wpisać AM/PM). H, M, S bez zera wiodącego. Separatory wpisujesz "
            "sam, np. HH:MM pokaże tylko godziny i minuty."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        form.addRow("", hint)

        spacing = self._spin(int(el.props.get("spacing", 0)), -20, 60, " px")
        spacing.valueChanged.connect(lambda v: self._apply("spacing", int(v)))
        form.addRow("Odstęp liter", spacing)
        return group

    def _group_date(self) -> QWidget:
        el = self.element
        assert el is not None
        group, form = self._form("Data")
        fmt = self._wide_combo(QComboBox())
        fmt.setEditable(True)
        presets = [
            "DD.MM.YYYY",
            "dddd, DD.MM",
            "DD MMMM YYYY",
            "ddd, DD MMM",
            "DD.MM",
            "MM/DD/YYYY",
        ]
        for preset in presets:
            fmt.addItem(preset)
        fmt.setCurrentText(str(el.props.get("format", "DD.MM.YYYY")))
        fmt.currentTextChanged.connect(lambda v: self._apply("format", v))
        form.addRow("Format", fmt)
        hint = QLabel("YYYY, YY, MMMM, MMM, MM, M, dddd, ddd, DD, D")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        form.addRow("", hint)

        lang = self._wide_combo(QComboBox())
        lang.addItem("Polski", "pl")
        lang.addItem("English", "en")
        _select_data(lang, str(el.props.get("lang", "pl")))
        lang.currentIndexChanged.connect(lambda _=0, c=lang: self._apply("lang", c.currentData()))
        form.addRow("Język", lang)
        form.addRow("Czcionka", self._font_combo(str(el.props.get("font", ""))))
        size = self._prop_spin("size", int(el.props.get("size", 24)), 6, 200, " px")
        size.valueChanged.connect(lambda v: self._apply("size", int(v)))
        form.addRow("Rozmiar", size)
        form.addRow("Kolor", self._color_button("color", str(el.props.get("color", "#FFFFFF"))))
        form.addRow("Wyrównanie", self._align_combo("align", str(el.props.get("align", "center"))))
        form.addRow("Pion", self._valign_combo(str(el.props.get("valign", "center"))))
        spacing = self._spin(int(el.props.get("spacing", 0)), -20, 60, " px")
        spacing.valueChanged.connect(lambda v: self._apply("spacing", int(v)))
        form.addRow("Odstęp liter", spacing)
        return group

    def _group_data(self) -> QWidget:
        el = self.element
        assert el is not None
        group, form = self._form("Dane")
        combo = self._wide_combo(QComboBox())
        for keys in C.DATA_GROUPS.values():
            if combo.count():
                combo.insertSeparator(combo.count())
            for key in keys:
                combo.addItem(C.DATA_SOURCES[key]["label"], key)
        _select_data(combo, str(el.props.get("source", "steps")))
        combo.currentIndexChanged.connect(lambda _=0, c=combo: self._apply("source", c.currentData()))
        form.addRow("Źródło", combo)
        form.addRow("Czcionka", self._font_combo(str(el.props.get("font", ""))))
        size = self._prop_spin("size", int(el.props.get("size", 36)), 6, 300, " px")
        size.valueChanged.connect(lambda v: self._apply("size", int(v)))
        form.addRow("Rozmiar", size)
        form.addRow("Kolor", self._color_button("color", str(el.props.get("color", "#FFFFFF"))))
        form.addRow("Wyrównanie", self._align_combo("align", str(el.props.get("align", "center"))))
        form.addRow("Pion", self._valign_combo(str(el.props.get("valign", "center"))))
        unit = QCheckBox("Pokaż jednostkę")
        unit.setChecked(bool(el.props.get("unit", False)))
        unit.setEnabled(bool(C.DATA_SOURCES.get(str(el.props.get("source", "steps")), {}).get("unit")))
        unit.toggled.connect(lambda v: self._apply("unit", bool(v)))
        combo.currentIndexChanged.connect(
            lambda _=0, c=combo, box=unit: box.setEnabled(
                bool(C.DATA_SOURCES.get(str(c.currentData()), {}).get("unit"))
            )
        )
        form.addRow("", unit)
        spacing = self._spin(int(el.props.get("spacing", 0)), -20, 60, " px")
        spacing.valueChanged.connect(lambda v: self._apply("spacing", int(v)))
        form.addRow("Odstęp liter", spacing)
        return group

    def _group_weather(self) -> QWidget:
        el = self.element
        assert el is not None
        group, form = self._form("Ikona pogody")
        size = self._prop_spin(
            "size", int(el.props.get("size", min(el.w, el.h))), 16, 300, " px"
        )
        size.valueChanged.connect(lambda v: self._apply("size", int(v)))
        form.addRow("Rozmiar", size)

        set_combo = self._wide_combo(QComboBox())
        set_combo.addItem("Wbudowany (domyślny)", "")
        for name in self._weather_sets():
            set_combo.addItem(name, name)
        _select_data(set_combo, str(el.props.get("set", "") or ""))
        set_combo.currentIndexChanged.connect(
            lambda _=0, c=set_combo: self._apply("set", c.currentData() or "")
        )
        form.addRow("Zestaw ikon", set_combo)
        form.addRow(
            self._file_picker(
                f"Importuj zestaw ({len(C.WEATHER_FILES)} PNG)…",
                self._import_weather_set,
                clear_text="Wbudowany",
                clear_slot=lambda: self._apply("set", ""),
            )
        )

        hint = QLabel(
            "Każda ikona pogody może używać innego zestawu. Wbudowany zestaw ma "
            "29 wariantów; własny folder musi zawierać 29 plików PNG."
        )
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        form.addRow("", hint)
        return group

    def _weather_sets(self) -> list[str]:
        if self.project.root is None:
            return []
        folder = self.project.assets_dir / "weather_sets"
        if not folder.exists():
            return []
        return sorted(path.name for path in folder.iterdir() if path.is_dir())

    def _import_weather_set(self) -> None:
        if self.project.root is None:
            QMessageBox.warning(self, "Brak projektu", "Najpierw zapisz projekt na dysku.")
            return
        path = QFileDialog.getExistingDirectory(self, "Wybierz folder z ikonami pogody")
        if not path:
            return
        try:
            name = self.project.import_weather_set(Path(path))
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Błąd importu", str(error))
            return
        self._apply("set", name, rebuild=True)
        self.statusMessage.emit(f"Zaimportowano zestaw ikon: {name}")

    def _source_combo(self, value: str) -> QComboBox:
        combo = self._wide_combo(QComboBox())
        for key in C.PROGRESS_SOURCES:
            info = C.DATA_SOURCES.get(key, {})
            combo.addItem(info.get("label", key), key)
        _select_data(combo, value)
        combo.currentIndexChanged.connect(lambda _=0, c=combo: self._apply("source", c.currentData()))
        return combo

    def _group_ring(self) -> QWidget:
        el = self.element
        assert el is not None
        group, form = self._form("Pierścień postępu")
        form.addRow("Źródło", self._source_combo(str(el.props.get("source", "steps"))))

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        width = self._prop_spin("line_width", int(el.props.get("line_width", 8)), 1, 60, " px")
        width.valueChanged.connect(lambda v: self._apply("line_width", int(v)))
        radius = self._prop_spin("radius", int(el.props.get("radius", 0)), 0, 233, " px")
        radius.valueChanged.connect(lambda v: self._apply("radius", int(v)))
        row_layout.addWidget(width)
        row_layout.addWidget(radius)
        form.addRow("Grubość / promień", row)

        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        start = self._spin(int(el.props.get("start_angle", 0)), -360, 720, "°")
        start.valueChanged.connect(lambda v: self._apply("start_angle", int(v)))
        end = self._spin(int(el.props.get("end_angle", 360)), -360, 720, "°")
        end.valueChanged.connect(lambda v: self._apply("end_angle", int(v)))
        row2_layout.addWidget(start)
        row2_layout.addWidget(end)
        form.addRow("Kąt start / koniec", row2)

        form.addRow("Kolor", self._color_button("color", str(el.props.get("color", "#4D9BFF"))))
        form.addRow("Tło", self._color_button("bg_color", str(el.props.get("bg_color", "#22304A"))))
        show_bg = QCheckBox("Pokaż tło")
        show_bg.setChecked(bool(el.props.get("show_bg", True)))
        show_bg.toggled.connect(lambda v: self._apply("show_bg", bool(v)))
        form.addRow("", show_bg)
        round_caps = QCheckBox("Zaokrąglone końce")
        round_caps.setChecked(bool(int(el.props.get("corner_flag", 0))))
        round_caps.toggled.connect(lambda v: self._apply("corner_flag", 1 if v else 0))
        form.addRow("", round_caps)
        return group

    def _group_bar(self) -> QWidget:
        el = self.element
        assert el is not None
        p = el.props
        group, form = self._form("Pasek postępu")
        form.addRow("Źródło", self._source_combo(str(p.get("source", "battery"))))

        style = self._wide_combo(QComboBox())
        style.addItem("Kolor", "solid")
        style.addItem("Obrazy 0% / 100%", "image")
        _select_data(style, str(p.get("style", "solid")))
        style.currentIndexChanged.connect(
            lambda _=0, c=style: self._apply("style", c.currentData(), rebuild=True)
        )
        form.addRow("Wygląd", style)

        form.addRow("Kolor", self._color_button("color", str(p.get("color", "#4D9BFF"))))
        form.addRow("Tło", self._color_button("bg_color", str(p.get("bg_color", "#22304A"))))
        show_bg = QCheckBox("Pokaż tło")
        show_bg.setChecked(bool(p.get("show_bg", True)))
        show_bg.toggled.connect(lambda v: self._apply("show_bg", bool(v)))
        form.addRow("", show_bg)

        direction = self._wide_combo(QComboBox())
        direction.addItem("Poziomo", "h")
        direction.addItem("Pionowo", "v")
        _select_data(direction, str(p.get("direction", "h")))
        direction.currentIndexChanged.connect(
            lambda _=0, c=direction: self._apply("direction", c.currentData(), rebuild=True)
        )
        form.addRow("Orientacja", direction)

        shape = self._wide_combo(QComboBox())
        shape.addItem("Prosty", "bar")
        shape.addItem("Łuk", "arc")
        _select_data(shape, str(p.get("shape", "bar")))
        shape.currentIndexChanged.connect(
            lambda _=0, c=shape: self._apply("shape", c.currentData(), rebuild=True)
        )
        form.addRow("Kształt", shape)

        curved = str(p.get("shape", "bar")) == "arc"
        if curved:
            curve = self._prop_spin("curve", int(p.get("curve", 100) or 0), 0, 100, " %")
            curve.valueChanged.connect(lambda v: self._apply("curve", int(v)))
            form.addRow("Zakrzywienie", curve)

            thickness = self._prop_spin(
                "line_width", int(p.get("line_width", 0) or 0), 0, 160, " px"
            )
            thickness.setSpecialValueText("auto")
            thickness.valueChanged.connect(lambda v: self._apply("line_width", int(v)))
            form.addRow("Grubość", thickness)

            bow = self._wide_combo(QComboBox())
            if str(p.get("direction", "h")) == "v":
                bow.addItem("W lewo", "left")
                bow.addItem("W prawo", "right")
                default_bow = "left"
            else:
                bow.addItem("W górę", "up")
                bow.addItem("W dół", "down")
                default_bow = "up"
            current_bow = str(p.get("bow", "") or default_bow)
            if bow.findData(current_bow) < 0:
                # Po zmianie orientacji stare wygięcie jest nieprawidłowe.
                current_bow = default_bow
                p["bow"] = default_bow
                self.live.emit()
            _select_data(bow, current_bow)
            bow.currentIndexChanged.connect(
                lambda _=0, c=bow: self._apply("bow", c.currentData())
            )
            form.addRow("Wygięcie", bow)

            round_caps = QCheckBox("Zaokrąglone końce")
            round_caps.setChecked(bool(int(p.get("corner_flag", 0) or 0)))
            round_caps.toggled.connect(
                lambda value: self._apply("corner_flag", 1 if value else 0)
            )
            form.addRow("", round_caps)
            hint = QLabel("Zakrzywienie 0% daje prosty pasek.")
            hint.setObjectName("hint")
            hint.setWordWrap(True)
            form.addRow("", hint)
        else:
            radius = self._spin(int(p.get("radius", 0) or 0), 0, 60, " px")
            radius.valueChanged.connect(lambda v: self._apply("radius", int(v)))
            form.addRow("Zaokrąglenie", radius)

        fill = self._wide_combo(QComboBox())
        fill.addItem("Od początku", 0)
        fill.addItem("Od końca", 1)
        _select_data(fill, 1 if bool(p.get("reverse", False)) else 0)
        fill.currentIndexChanged.connect(
            lambda _=0, c=fill: self._apply("reverse", bool(c.currentData()))
        )
        form.addRow("Wypełnianie", fill)

        if str(p.get("style", "solid")) == "image":
            for key, title in (("src0", "Obraz 0%"), ("src100", "Obraz 100%")):
                current = Path(str(p.get(key, ""))).name or ""
                picker = self._file_picker(
                    "Wybierz obraz…",
                    lambda _=False, k=key: self._pick_bar_image(k),
                    clear_text="Usuń",
                    clear_slot=lambda _=False, k=key: self._apply(k, "", rebuild=True),
                    current=current or "brak pliku",
                )
                form.addRow(title, picker)
            hint = QLabel(
                "Oba obrazy są skalowane do ramki. Obraz 100% jest odsłaniany "
                "wraz z postępem, a obraz 0% pozostaje tłem."
            )
            hint.setObjectName("hint")
            hint.setWordWrap(True)
            form.addRow("", hint)
            src100 = str(p.get("src100", "") or "")
            if not src100 or self.project.asset_file(src100) is None:
                warn = QLabel(
                    "Bez obrazu 100% pasek rysuje się jak zwykły kolorowy "
                    "pasek. Wybierz obraz, aby włączyć stopniowe odsłanianie."
                )
                warn.setObjectName("warn")
                warn.setWordWrap(True)
                form.addRow("", warn)
        return group

    def _group_shortcut(self) -> QWidget:
        el = self.element
        assert el is not None
        group, form = self._form("Skrót")
        kind = self._wide_combo(QComboBox())
        kind.addItem("Aplikacja", "app")
        kind.addItem("Dane / ekran", "data")
        _select_data(kind, str(el.props.get("kind", "app")))
        kind.currentIndexChanged.connect(
            lambda _=0, c=kind: self._apply("kind", c.currentData(), rebuild=True)
        )
        form.addRow("Rodzaj", kind)

        if str(el.props.get("kind", "app")) == "app":
            apps = self._wide_combo(QComboBox())
            apps.setMaxVisibleItems(18)
            for title, items in C.SHORTCUT_CATALOG:
                if apps.count():
                    apps.insertSeparator(apps.count())
                for key, label, _js in items:
                    apps.addItem(label, key)
            _select_data(apps, str(el.props.get("app", "Steps")))
            apps.currentIndexChanged.connect(
                lambda _=0, c=apps: self._apply("app", c.currentData())
            )
            form.addRow("Aplikacja", apps)
        else:
            data = self._wide_combo(QComboBox())
            data.setMaxVisibleItems(18)
            for keys in C.DATA_GROUPS.values():
                if data.count():
                    data.insertSeparator(data.count())
                for key in keys:
                    if not C.DATA_SOURCES[key].get("type"):
                        continue
                    data.addItem(C.DATA_SOURCES[key]["label"], key)
            _select_data(data, str(el.props.get("data", "steps")))
            data.currentIndexChanged.connect(
                lambda _=0, c=data: self._apply("data", c.currentData())
            )
            form.addRow("Dane", data)

        current = Path(str(el.props.get("icon", ""))).name or "brak"
        form.addRow(
            self._file_picker(
                "Wybierz ikonę…",
                self._pick_shortcut_icon,
                clear_text="Usuń",
                clear_slot=lambda: self._apply("icon", ""),
                current=current,
            )
        )

        hint = QLabel("Dotknięcie obszaru skrótu na zegarku otworzy wybrany ekran.")
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        form.addRow("", hint)
        return group

    def _group_status(self) -> QWidget:
        el = self.element
        assert el is not None
        group, form = self._form("Status systemowy")
        combo = self._wide_combo(QComboBox())
        for key, label in C.STATUS_LABELS.items():
            combo.addItem(label, key)
        _select_data(combo, str(el.props.get("status", "bluetooth")))
        combo.currentIndexChanged.connect(
            lambda _=0, c=combo: self._apply("status", c.currentData())
        )
        form.addRow("Wskaźnik", combo)
        size = self._prop_spin("size", int(el.props.get("size", 32)), 8, 200, " px")
        size.valueChanged.connect(lambda v: self._apply("size", int(v)))
        form.addRow("Rozmiar", size)
        return group

    def _group_hands(self) -> QWidget:
        el = self.element
        assert el is not None
        group, form = self._form("Wskazówki analogowe")

        set_combo = self._wide_combo(QComboBox())
        set_combo.addItem("Wbudowany (domyślny)", "")
        for name in self._hand_sets():
            set_combo.addItem(name, name)
        _select_data(set_combo, str(el.props.get("set", "") or ""))
        set_combo.currentIndexChanged.connect(
            lambda _=0, c=set_combo: self._apply("set", c.currentData() or "", rebuild=True)
        )
        form.addRow("Zestaw", set_combo)
        form.addRow(
            self._file_picker(
                "Importuj zestaw…",
                self._import_hand_set,
                clear_text="Wbudowany",
                clear_slot=lambda: self._apply("set", "", rebuild=True),
            )
        )

        for role in C.HAND_ROLES:
            picker = self._file_picker(
                "Wybierz plik…",
                lambda _=False, r=role: self._pick_hand_image(r),
                clear_text="Domyślna",
                clear_slot=lambda _=False, r=role: self._apply(f"{r}_src", "", rebuild=True),
                current=self._hand_source_label(role),
            )
            form.addRow(C.HAND_LABELS[role], picker)

        fit = QPushButton(f"Dopasuj do tarczy ({C.DEVICE['width']} × {C.DEVICE['height']})")
        fit.setMinimumHeight(30)
        fit.setToolTip(
            "Ustawia ramkę na cały ekran, żeby oś obrotu wypadła dokładnie "
            "w środku tarczy, a wskazówki miały pełny rozmiar."
        )
        fit.clicked.connect(self._fit_hands_to_dial)
        form.addRow(fit)

        flags = QWidget()
        flags_layout = QHBoxLayout(flags)
        flags_layout.setContentsMargins(0, 0, 0, 0)
        for key, label in (("show_second", "Sekundowa"), ("show_cap", "Nakładka osi")):
            box = QCheckBox(label)
            box.setChecked(bool(el.props.get(key, True)))
            box.toggled.connect(lambda v, k=key: self._apply(k, bool(v), rebuild=True))
            flags_layout.addWidget(box)
        flags_layout.addStretch(1)
        form.addRow(flags)

        smallest = min(int(el.w), int(el.h))
        if smallest < 200:
            warn = QLabel(
                f"Ramka ma tylko {int(el.w)} × {int(el.h)} px — środek obrotu "
                "wypada poza tarczą, a wskazówki są zmniejszone. Kliknij "
                "„Dopasuj do tarczy”."
            )
            warn.setWordWrap(True)
            warn.setObjectName("warn")
            form.addRow("", warn)

        hint = QLabel(
            "Każdą wskazówkę możesz wybrać osobno („Wybierz plik…”). Wybór "
            "pliku ma pierwszeństwo przed zestawem; „Domyślna” przywraca "
            "ustawienie zestawu. Obraz wskazówki powinien być skierowany do "
            "góry, a oś obrotu znajdować się w środku obrazu."
        )
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        form.addRow("", hint)
        return group

    def _hand_source_label(self, role: str) -> str:
        el = self.element
        if el is None:
            return ""
        default = f"hands/{C.HAND_FILES[role]}"
        chosen = str(el.props.get(f"{role}_src", "") or "")
        if chosen and chosen != default:
            return f"własna: {Path(chosen).name}"
        set_name = str(el.props.get("set", "") or "")
        if set_name:
            return f"zestaw „{set_name}”: {C.HAND_FILES[role]}"
        return f"wbudowana: {C.HAND_FILES[role]}"

    def _fit_hands_to_dial(self) -> None:
        el = self.element
        if self._loading or el is None:
            return
        el.x = 0
        el.y = 0
        el.w = int(C.DEVICE["width"])
        el.h = int(C.DEVICE["height"])
        self.sync_geometry()
        self.live.emit()
        self._commit_timer.start()
        QTimer.singleShot(0, self._rebuild)

    def _pick_hand_image(self, role: str) -> None:
        if self.element is None:
            return
        if self.project.root is None:
            QMessageBox.warning(self, "Brak projektu", "Najpierw zapisz projekt na dysku.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            C.HAND_LABELS.get(role, "Wskazówka"),
            "",
            "Obrazy (*.png);;Wszystkie pliki (*)",
        )
        if not path:
            return
        try:
            rel = self.project.import_hand_image(role, Path(path))
        except (OSError, ValueError) as error:
            QMessageBox.critical(
                self, "Błąd", f"Nie udało się zaimportować wskazówki:\n{error}"
            )
            return
        self._apply(f"{role}_src", rel, rebuild=True)
        self.statusMessage.emit(f"Wybrano {C.HAND_LABELS.get(role, role)}: {Path(path).name}")

    def _hand_sets(self) -> list[str]:
        if self.project.root is None:
            return []
        folder = self.project.assets_dir / "hand_sets"
        if not folder.exists():
            return []
        return sorted(path.name for path in folder.iterdir() if path.is_dir())

    def _import_hand_set(self) -> None:
        if self.project.root is None:
            QMessageBox.warning(self, "Brak projektu", "Najpierw zapisz projekt na dysku.")
            return
        path = QFileDialog.getExistingDirectory(self, "Wybierz folder ze wskazówkami")
        if not path:
            return
        try:
            name = self.project.import_hand_set(Path(path))
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Błąd importu", str(error))
            return
        self._apply("set", name, rebuild=True)
        self.statusMessage.emit(f"Zaimportowano zestaw wskazówek: {name}")

    def _pick_image(self) -> None:
        if self.element is None:
            return
        if self.project.root is None:
            QMessageBox.warning(self, "Brak projektu", "Najpierw zapisz projekt na dysku.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz obraz",
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
        self._apply("src", rel)
        self._rebuild()
        self.statusMessage.emit(f"Zaimportowano {Path(path).name}")

    def _pick_bar_image(self, key: str) -> None:
        if self.element is None or self.element.type != "progress_bar":
            return
        if self.project.root is None:
            QMessageBox.warning(self, "Brak projektu", "Najpierw zapisz projekt na dysku.")
            return
        title = "Obraz 0% paska" if key == "src0" else "Obraz 100% paska"
        path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            "",
            "Obrazy (*.png *.jpg *.jpeg *.bmp *.webp);;Wszystkie pliki (*)",
        )
        if not path:
            return
        try:
            rel = self.project.import_asset(Path(path), "bars")
        except OSError as error:
            QMessageBox.critical(
                self, "Błąd", f"Nie udało się zaimportować obrazu:\n{error}"
            )
            return
        self._apply(key, rel, rebuild=True)
        self.statusMessage.emit(f"Zaimportowano {Path(path).name}")

    def _pick_shortcut_icon(self) -> None:
        if self.element is None:
            return
        if self.project.root is None:
            QMessageBox.warning(self, "Brak projektu", "Najpierw zapisz projekt na dysku.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz ikonę",
            "",
            "Obrazy (*.png *.jpg *.jpeg *.bmp *.webp);;Wszystkie pliki (*)",
        )
        if not path:
            return
        try:
            rel = self.project.import_asset(Path(path), "icons")
        except OSError as error:
            QMessageBox.critical(self, "Błąd", f"Nie udało się zaimportować ikony:\n{error}")
            return
        self._apply("icon", rel)
        self._rebuild()

