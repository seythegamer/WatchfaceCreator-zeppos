from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import json
import math
import re
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import constants as C
from . import timeformat

SCHEMA_VERSION = 1

SAMPLE_TIME = _dt.datetime(2026, 8, 2, 10, 9, 36)
SAMPLE_DATE = SAMPLE_TIME.date()
SAMPLE_VALUES = {
    "steps": "8670",
    "heart": "86",
    "battery": "75",
    "calories": "280",
    "distance": "5.30",
    "weather": "22",
}

DEFAULT_PROPS: dict[str, dict[str, Any]] = {
    "image": {"src": "", "opacity": 255},
    "text": {
        "text": "TEKST",
        "font": "",
        "size": 32,
        "color": "#FFFFFF",
        "align": "center",
        "valign": "center",
        "spacing": 0,
    },
    "time": {
        "font": "fonts/Rajdhani-Bold.ttf",
        "size": 96,
        "color": "#FFFFFF",
        "align": "center",
        "valign": "center",
        "format": "24",
        "display": timeformat.DEFAULT_DISPLAY,
        "spacing": 0,
    },
    "date": {
        "format": "DD.MM.YYYY",
        "lang": "pl",
        "font": "fonts/Rajdhani-Medium.ttf",
        "size": 24,
        "color": "#FFFFFF",
        "align": "center",
        "spacing": 0,
    },
    "data": {
        "source": "steps",
        "font": "fonts/Rajdhani-Bold.ttf",
        "size": 36,
        "color": "#FFFFFF",
        "align": "center",
        "valign": "center",
        "unit": False,
        "pad": 0,
        "spacing": 0,
    },
    "weather_icon": {
        "size": 72,
        "align": "center",
        "night_variants": True,
        "set": "",
    },
    "progress_ring": {
        "source": "steps",
        "line_width": 8,
        "start_angle": 0,
        "end_angle": 360,
        "color": "#4D9BFF",
        "bg_color": "#22304A",
        "show_bg": True,
        "corner_flag": 0,
        "radius": 0,
    },
    "progress_bar": {
        "source": "battery",
        "style": "solid",
        "color": "#4D9BFF",
        "bg_color": "#22304A",
        "show_bg": True,
        "radius": 6,
        "direction": "h",
        "shape": "bar",
        "curve": 100,
        "line_width": 0,
        "bow": "",
        "corner_flag": 0,
        "reverse": False,
        "src0": "",
        "src100": "",
    },
    "shortcut": {
        "kind": "app",
        "app": "Steps",
        "data": "steps",
        "icon": "",
        "label": "",
        "show_label": False,
    },
    "status": {"status": "bluetooth", "size": 32},
    "analog_hands": {
        "set": "",
        "hour_src": "",
        "minute_src": "",
        "second_src": "",
        "cap_src": "",
        "show_second": True,
        "show_cap": True,
    },
}

# Typy elementów, dla których można skalować zawartość razem z ramką.
CONTENT_SCALE_TYPES = frozenset(
    {"text", "time", "date", "data", "image", "weather_icon", "status", "shortcut"}
)
TEXT_CONTENT_TYPES = frozenset({"text", "time", "date", "data"})
IMAGE_CONTENT_TYPES = frozenset({"image", "shortcut"})


def supports_content_scale(kind: str) -> bool:
    return kind in CONTENT_SCALE_TYPES


# Typy, które zegarek potrafi obrócić. Wszystkie są eksportowane jako widgety
# IMG (także tekst, który przy obrocie jest rasteryzowany do obrazu), więc obrót
# wygląda na urządzeniu tak samo jak w edytorze.
ROTATABLE_TYPES = frozenset(
    {"image", "text", "shortcut", "weather_icon", "analog_hands"}
)
# Tekst dynamiczny (godzina, data, dane) jest widgetem TEXT, którego Zepp OS nie
# obraca - dlatego obrót jest dla niego niedostępny.
ROTATION_BAKED_TYPES = frozenset({"text"})
ROTATION_UNSUPPORTED_HINT = (
    "Zegarek nie obraca widgetów tekstowych ze zmienną treścią "
    "(godzina, data, dane). Obrót jest dostępny dla tekstu stałego, "
    "obrazów, ikon pogody, skrótów i wskazówek."
)


def supports_rotation(kind: str) -> bool:
    return kind in ROTATABLE_TYPES


def normalize_rotation(value: float) -> int:
    """Sprowadza kąt do zakresu -180..180 (stopnie, zgodnie z ruchem wskazówek)."""
    angle = int(round(float(value))) % 360
    if angle > 180:
        angle -= 360
    elif angle <= -180:
        angle += 360
    return int(angle)


def center_element(el: "Element", horizontal: bool = True, vertical: bool = True) -> None:
    """Ustawia element dokładnie na środku tarczy (w osi X, Y albo obu)."""
    if horizontal:
        el.x = int(round((C.DEVICE["width"] - el.w) / 2))
    if vertical:
        el.y = int(round((C.DEVICE["height"] - el.h) / 2))


def rotation_center(el: "Element") -> tuple[float, float]:
    """Punkt obrotu elementu (środek rysowanej zawartości).

    Dla obrazów i skrótów zawartość może być mniejsza od ramki, a zegarek
    obraca widget IMG wokół środka jego obrazu - dlatego tutaj też liczymy
    środek zawartości, a nie ramki.
    """
    if el.type in IMAGE_CONTENT_TYPES:
        x, y, width, height = el.render_rect()
        return (x + width / 2.0, y + height / 2.0)
    return (el.x + el.w / 2.0, el.y + el.h / 2.0)


@dataclass(frozen=True)
class BarArc:
    """Geometria łukowego paska postępu (wspólna dla podglądu i eksportu)."""

    center_x: int
    center_y: int
    radius: int
    line_width: int
    start_angle: float
    end_angle: float
    reverse: bool


def bar_arc_geometry(el: Element) -> BarArc | None:
    """Oblicza łuk mieszczący się w ramce elementu.

    Pasek jest wyginany w jedną stronę, a jego *zewnętrzna* krawędź jest
    wpisana w ramkę. Grubość i strzałka łuku są tak dobrane, aby cały pasek
    (razem z zaokrąglonymi końcami) pozostał w ramce. Dzięki temu podgląd,
    edytor i zegarek używają dokładnie tych samych współrzędnych.
    """
    if str(el.props.get("shape", "bar")) != "arc":
        return None
    curve = max(0, min(100, int(el.props.get("curve", 100) or 0)))
    if curve <= 0:
        return None

    horizontal = str(el.props.get("direction", "h")) != "v"
    along = float(el.w if horizontal else el.h)
    across = float(el.h if horizontal else el.w)
    if along < 2 or across < 2:
        return None

    line_width = int(el.props.get("line_width", 0) or 0)
    if line_width <= 0:
        line_width = max(2, min(16, int(across // 2)))
    line_width = max(1, min(line_width, max(1, int(across) - 1)))
    corner = bool(int(el.props.get("corner_flag", 0) or 0))
    length = max(1.0, along - (line_width if corner else 0))
    half = length / 2.0

    # Strzałka liczona dla zewnętrznej krawędzi paska. Przy 100% łuk zajmuje
    # całą wysokość ramki, przy mniejszych wartościach jest coraz płaski i
    # pozostaje wyśrodkowany w poprzek ramki.
    sagitta_max = max(0.5, across - line_width)
    sagitta = sagitta_max * curve / 100.0
    if sagitta < 0.05:
        return None
    # Przy bardzo krótkich i grubych paskach łuk nie może być większy niż
    # półkole - inaczej równanie cięciwy przestaje mieć sens.
    if sagitta > half:
        sagitta = half
    outer = (half * half + sagitta * sagitta) / (2.0 * sagitta)
    if outer <= half:
        outer = half + 0.5
    # Kąt końca łuku liczony po cięciwie zewnętrznej krawędzi.
    beta = math.degrees(math.atan2(outer - sagitta, half))
    radius = outer - line_width / 2.0
    # Odległość zewnętrznej krawędzi od bliższej krawędzi ramki.
    offset = (across - line_width) / 2.0 - sagitta / 2.0

    bow = str(el.props.get("bow", "") or "")
    if horizontal:
        if bow not in ("up", "down"):
            bow = "up"
        center_x = el.x + el.w / 2.0
        if bow == "up":
            center_y = el.y + offset + outer
            start_angle, end_angle, reverse = 180.0 + beta, 360.0 - beta, False
        else:
            center_y = el.y + el.h - offset - outer
            start_angle, end_angle, reverse = beta, 180.0 - beta, True
    else:
        if bow not in ("left", "right"):
            bow = "left"
        center_y = el.y + el.h / 2.0
        if bow == "left":
            center_x = el.x + offset + outer
            start_angle, end_angle, reverse = 90.0 + beta, 270.0 - beta, False
        else:
            center_x = el.x + el.w - offset - outer
            start_angle, end_angle, reverse = -90.0 + beta, 90.0 - beta, True

    if end_angle <= start_angle:
        return None
    return BarArc(
        center_x=int(round(center_x)),
        center_y=int(round(center_y)),
        radius=max(1, int(round(radius))),
        line_width=line_width,
        start_angle=round(start_angle, 4),
        end_angle=round(end_angle, 4),
        reverse=reverse,
    )


def bar_arc_fill(
    geometry: BarArc, ratio: float, reverse: bool = False
) -> tuple[float, float]:
    """Zakres kąta wypełnienia dla danego postępu.

    ``reverse`` odwraca kierunek wybrany przez użytkownika względem
    naturalnego kierunku paska (poziomo: od lewej, pionowo: od dołu).
    """
    ratio = max(0.0, min(1.0, float(ratio)))
    start = float(geometry.start_angle)
    end = float(geometry.end_angle)
    span = end - start
    backward = bool(reverse) != bool(geometry.reverse)
    if backward:
        return (round(end - span * ratio, 4), round(end, 4))
    return (round(start, 4), round(start + span * ratio, 4))


def _round_half_up(value: float) -> int:
    """Zaokrąglenie jak ``Math.round`` w JavaScripcie (połówki w górę)."""
    return int(math.floor(float(value) + 0.5))


def bar_reveal_geometry(
    el: Element, ratio: float, reverse: bool = False
) -> tuple[int, int, int, int, int, int]:
    """Prostokąt odsłaniania obrazu 100% wraz z przesunięciem obrazu.

    Zwraca ``x, y, w, h, pos_x, pos_y``. ``pos_x``/``pos_y`` są potrzebne
    tylko przez widget IMG na zegarku; podgląd przycina obraz do ``x/y/w/h``.
    """
    ratio = max(0.0, min(1.0, float(ratio)))
    if str(el.props.get("direction", "h")) == "v":
        height = max(1, _round_half_up(el.h * ratio))
        if reverse:
            return (el.x, el.y, el.w, height, 0, 0)
        shift = el.h - height
        return (el.x, el.y + shift, el.w, height, 0, -shift)
    width = max(1, _round_half_up(el.w * ratio))
    if reverse:
        shift = el.w - width
        return (el.x + shift, el.y, width, el.h, -shift, 0)
    return (el.x, el.y, width, el.h, 0, 0)


def bar_frame_ratio(ratio: float, count: int | None = None) -> float:
    """Zaokrągla postęp do klatki używanej przez zegarek."""
    count = int(count or C.PROGRESS_BAR_FRAMES)
    if count < 2:
        return max(0.0, min(1.0, float(ratio)))
    index = _round_half_up(max(0.0, min(1.0, float(ratio))) * (count - 1))
    return index / (count - 1)


def hand_source(el: Element, role: str) -> str:
    """Ścieżka obrazu pojedynczej wskazówki (bez sprawdzania widoczności).

    Pierwszeństwo ma obraz wybrany dla tej roli. Domyślna, wbudowana ścieżka
    (``hands/hour.png``) jest traktowana jak brak wyboru, więc wybrany zestaw
    nadal działa. Dopiero późniejszy wybór pliku dla roli nadpisuje zestaw.
    """
    default = f"hands/{C.HAND_FILES[role]}"
    chosen = str(el.props.get(f"{role}_src", "") or "")
    if chosen and chosen != default:
        return chosen
    set_name = str(el.props.get("set", "") or "")
    if set_name:
        return f"hand_sets/{set_name}/{C.HAND_FILES[role]}"
    return default


def hand_sources(el: Element) -> dict[str, str]:
    """Ścieżki obrazów wskazówek dla bieżącego zestawu i wyborów pojedynczych ról."""
    result: dict[str, str] = {}
    for role in C.HAND_ROLES:
        if role == "second" and not bool(el.props.get("show_second", True)):
            continue
        if role == "cap" and not bool(el.props.get("show_cap", True)):
            continue
        result[role] = hand_source(el, role)
    return result


def _dominant_ratio(ratio_w: float, ratio_h: float) -> float:
    if abs(ratio_w - 1.0) >= abs(ratio_h - 1.0):
        return ratio_w
    return ratio_h


def ensure_content_base(el: Element) -> dict[str, int]:
    """Punkt odniesienia dla skalowania zawartości (ramka + rozmiar treści)."""
    base = getattr(el, "_content_base", None)
    if base is None:
        width, height = el.render_size()
        base = {
            "w": max(1, int(el.w)),
            "h": max(1, int(el.h)),
            "size": int(el.props.get("size", 0) or 0),
            "content_w": width,
            "content_h": height,
        }
        el._content_base = base  # type: ignore[attr-defined]
    return base


def clear_content_base(el: Element) -> None:
    el._content_base = None  # type: ignore[attr-defined]


def apply_content_scale(el: Element, box_w: int, box_h: int) -> None:
    """Skaluje zawartość względem punktu odniesienia i nowego rozmiaru ramki."""
    if not el.scale_content:
        return
    base = ensure_content_base(el)
    ratio_w = box_w / base["w"] if base["w"] else 1.0
    ratio_h = box_h / base["h"] if base["h"] else 1.0
    limit = 200 if el.type in ("date", "status") else 300
    if el.type in TEXT_CONTENT_TYPES:
        factor = _dominant_ratio(ratio_w, ratio_h)
        el.props["size"] = max(1, min(limit, round(base["size"] * factor)))
    elif el.type in IMAGE_CONTENT_TYPES:
        el.props["content_w"] = max(1, round(base["content_w"] * ratio_w))
        el.props["content_h"] = max(1, round(base["content_h"] * ratio_h))
    elif el.type in ("weather_icon", "status"):
        factor = _dominant_ratio(ratio_w, ratio_h)
        el.props["size"] = max(1, min(limit, round(base["size"] * factor)))


DEFAULT_SIZE: dict[str, tuple[int, int]] = {
    "image": (220, 220),
    "text": (260, 60),
    "time": (320, 120),
    "date": (300, 50),
    "data": (180, 64),
    "weather_icon": (72, 72),
    "progress_ring": (210, 210),
    "progress_bar": (240, 14),
    "shortcut": (110, 110),
    "status": (32, 32),
    "analog_hands": (466, 466),
}

TYPE_LABELS = {
    "image": "Obraz",
    "text": "Tekst",
    "time": "Godzina",
    "date": "Data",
    "data": "Dane",
    "weather_icon": "Ikona pogody",
    "progress_ring": "Postęp (pierścień)",
    "progress_bar": "Postęp (pasek)",
    "shortcut": "Skrót",
    "status": "Status systemowy",
    "analog_hands": "Wskazówki analogowe",
}


def new_id() -> str:
    return uuid.uuid4().hex[:10]


APP_ID_BASE = 4884000
APP_ID_RANGE = 90000


def new_app_id() -> int:
    """Losowy identyfikator aplikacji dla każdej nowej tarczy.

    Zepp OS wymaga unikalnego ``appId`` dla każdej tarczy. Losowanie przy
    każdym utworzeniu projektu zapobiega nadpisaniu poprzedniej tarczy na
    zegarku i konfliktom przy publikacji.
    """
    return APP_ID_BASE + (uuid.uuid4().int % APP_ID_RANGE)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9ąćęłńóśźż]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "tarcza"


def safe_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "plik"
    return value


@dataclass
class Element:
    type: str
    id: str = field(default_factory=new_id)
    name: str = ""
    x: int = 0
    y: int = 0
    w: int = 100
    h: int = 100
    visible: bool = True
    locked: bool = False
    scale_content: bool = False
    rotation: int = 0
    props: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        props = dict(self.props or {})
        if self.type == "time":
            timeformat.migrate_props(props)
        base = copy.deepcopy(DEFAULT_PROPS.get(self.type, {}))
        base.update(props)
        self.props = base
        if not self.name:
            self.name = TYPE_LABELS.get(self.type, self.type)

    def ensure_props(self) -> None:
        props = dict(self.props or {})
        if self.type == "time":
            timeformat.migrate_props(props)
        base = copy.deepcopy(DEFAULT_PROPS.get(self.type, {}))
        base.update(props)
        self.props = base

    def render_size(self) -> tuple[int, int]:
        """Rozmiar rysowanej zawartości (obraz/skrót) niezależny od ramki."""
        if self.type in IMAGE_CONTENT_TYPES:
            width = int(self.props.get("content_w", 0) or 0)
            height = int(self.props.get("content_h", 0) or 0)
            return (
                width if width > 0 else max(1, int(self.w)),
                height if height > 0 else max(1, int(self.h)),
            )
        return (max(1, int(self.w)), max(1, int(self.h)))

    def render_rect(self) -> tuple[int, int, int, int]:
        """Pozycja i rozmiar zawartości wyśrodkowanej w ramce elementu."""
        width, height = self.render_size()
        x = round(self.x + (self.w - width) / 2)
        y = round(self.y + (self.h - height) / 2)
        return (x, y, width, height)

    def freeze_content_size(self) -> None:
        """Utrwala obecny rozmiar obrazu/skrótu, gdy ramka zmienia się bez skalowania."""
        if self.type in IMAGE_CONTENT_TYPES:
            width, height = self.render_size()
            self.props["content_w"] = width
            self.props["content_h"] = height
        clear_content_base(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "id": self.id,
            "name": self.name,
            "x": int(self.x),
            "y": int(self.y),
            "w": int(self.w),
            "h": int(self.h),
            "visible": bool(self.visible),
            "locked": bool(self.locked),
            "scale_content": bool(self.scale_content),
            "rotation": int(self.rotation),
            "props": dict(self.props),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Element:
        props = dict(data.get("props") or {})
        kind = str(data.get("type", "text"))
        rotation = data.get("rotation")
        if rotation is None:
            # Zgodność ze starszymi projektami: obrazy miały kąt w props["angle"].
            rotation = props.pop("angle", 0) if kind == "image" else 0
        else:
            props.pop("angle", None)
        el = cls(
            type=kind,
            id=str(data.get("id") or new_id()),
            name=str(data.get("name") or ""),
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            w=int(data.get("w", 100)),
            h=int(data.get("h", 100)),
            visible=bool(data.get("visible", True)),
            locked=bool(data.get("locked", False)),
            scale_content=bool(data.get("scale_content", False)),
            rotation=normalize_rotation(rotation or 0),
            props=props,
        )
        el.ensure_props()
        return el

    def clone(self) -> Element:
        data = self.to_dict()
        data["id"] = new_id()
        data["name"] = f"{self.name} kopia"
        data["x"] = min(max(0, self.x + 12), C.DEVICE["width"] - self.w)
        data["y"] = min(max(0, self.y + 12), C.DEVICE["height"] - self.h)
        return Element.from_dict(data)


@dataclass
class Project:
    name: str = "Nowa tarcza"
    author: str = "Twoje imię"
    vender: str = "zepp"
    app_id: int = field(default_factory=new_app_id)
    version_name: str = "1.0.0"
    version_code: int = 1
    description: str = ""
    device: dict[str, Any] = field(default_factory=lambda: dict(C.DEVICE))
    background_color: str = "#000000"
    background_image: str = ""
    aod_simple: bool = True
    aod_color: str = "#FFFFFF"
    elements: list[Element] = field(default_factory=list)
    root: Path | None = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_VERSION,
            "name": self.name,
            "author": self.author,
            "vender": self.vender,
            "app_id": int(self.app_id),
            "version_name": self.version_name,
            "version_code": int(self.version_code),
            "description": self.description,
            "background_color": self.background_color,
            "background_image": self.background_image,
            "aod_simple": bool(self.aod_simple),
            "aod_color": self.aod_color,
            "elements": [el.to_dict() for el in self.elements],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], root: Path | None = None) -> Project:
        prj = cls(
            name=str(data.get("name") or "Nowa tarcza"),
            author=str(data.get("author") or ""),
            vender=str(data.get("vender") or "zepp"),
            app_id=int(data.get("app_id") or new_app_id()),
            version_name=str(data.get("version_name") or "1.0.0"),
            version_code=int(data.get("version_code") or 1),
            description=str(data.get("description") or ""),
            background_color=str(data.get("background_color") or "#000000"),
            background_image=str(data.get("background_image") or ""),
            aod_simple=bool(data.get("aod_simple", True)),
            aod_color=str(data.get("aod_color") or "#FFFFFF"),
            elements=[Element.from_dict(item) for item in data.get("elements") or []],
        )
        prj.root = root
        return prj

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.to_dict())

    def restore(self, state: dict[str, Any]) -> None:
        other = Project.from_dict(copy.deepcopy(state), self.root)
        self.name = other.name
        self.author = other.author
        self.vender = other.vender
        self.app_id = other.app_id
        self.version_name = other.version_name
        self.version_code = other.version_code
        self.description = other.description
        self.background_color = other.background_color
        self.background_image = other.background_image
        self.aod_simple = other.aod_simple
        self.aod_color = other.aod_color
        self.elements = other.elements

    @property
    def assets_dir(self) -> Path:
        if self.root is None:
            raise RuntimeError("Projekt nie ma katalogu")
        return self.root / "assets"

    def asset_file(self, rel: str) -> Path | None:
        if not rel or self.root is None:
            return None
        path = self.assets_dir / rel
        return path if path.exists() else None

    def import_asset(self, src: Path, subdir: str = "icons") -> str:
        src = Path(src)
        target_dir = self.assets_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        stem = safe_filename(src.stem)
        suffix = src.suffix.lower() or ".png"
        name = f"{stem}{suffix}"
        i = 2
        while (target_dir / name).exists():
            name = f"{stem}_{i}{suffix}"
            i += 1
        shutil.copy2(src, target_dir / name)
        return f"{subdir}/{name}" if subdir else name

    def import_font(self, src: Path) -> str:
        return self.import_asset(src, "fonts")

    def import_weather_set(self, src: Path) -> str:
        src = Path(src)
        if self.root is None:
            raise RuntimeError("Brak katalogu projektu")
        files = sorted(
            path
            for path in src.iterdir()
            if path.is_file() and path.suffix.lower() == ".png"
        )
        if len(files) < len(C.WEATHER_FILES):
            raise ValueError(
                f"Zestaw musi zawierać {len(C.WEATHER_FILES)} plików PNG "
                f"(znaleziono {len(files)})."
            )
        by_name = {path.name.lower(): path for path in files}
        ordered: list[Path] = []
        for name in C.WEATHER_FILES:
            path = by_name.get(name.lower())
            if path is not None:
                ordered.append(path)
        if len(ordered) != len(C.WEATHER_FILES):
            if len(files) != len(C.WEATHER_FILES):
                raise ValueError(
                    f"Nazwij pliki jak wbudowane albo dostarcz dokładnie "
                    f"{len(C.WEATHER_FILES)} obrazów (jest {len(files)})."
                )
            ordered = files

        base = safe_filename(src.name).lower() or "wlasny"
        name = base
        index = 2
        folder = self.assets_dir / "weather_sets"
        while (folder / name).exists():
            name = f"{base}_{index}"
            index += 1
        target = folder / name
        target.mkdir(parents=True, exist_ok=True)
        for canonical, image in zip(C.WEATHER_FILES, ordered):
            shutil.copy2(image, target / canonical)
        return name

    def import_hand_set(self, src: Path) -> str:
        """Importuje folder ze wskazówkami (hour.png, minute.png + opcjonalne)."""
        src = Path(src)
        if self.root is None:
            raise RuntimeError("Brak katalogu projektu")
        found: dict[str, Path] = {}
        for path in sorted(src.iterdir()):
            if not path.is_file() or path.suffix.lower() != ".png":
                continue
            role = path.stem.lower()
            if role in C.HAND_FILES and role not in found:
                found[role] = path
        missing = [C.HAND_FILES[role] for role in C.HAND_REQUIRED if role not in found]
        if missing:
            raise ValueError(
                "Zestaw wskazówek musi zawierać co najmniej hour.png i minute.png "
                f"(brakuje: {', '.join(missing)})."
            )
        base = safe_filename(src.name).lower() or "wlasny"
        name = base
        index = 2
        folder = self.assets_dir / "hand_sets"
        while (folder / name).exists():
            name = f"{base}_{index}"
            index += 1
        target = folder / name
        target.mkdir(parents=True, exist_ok=True)
        for role, path in found.items():
            shutil.copy2(path, target / C.HAND_FILES[role])
        return name

    def import_hand_image(self, role: str, src: Path) -> str:
        """Kopiuje pojedynczy obraz wskazówki i zwraca ścieżkę względem assets."""
        if role not in C.HAND_FILES:
            raise ValueError(f"Nieznana wskazówka: {role}")
        if self.root is None:
            raise RuntimeError("Brak katalogu projektu")
        src = Path(src)
        from PIL import Image

        try:
            with Image.open(src) as image:
                image.verify()
        except OSError as error:
            raise ValueError(f"Nie można wczytać obrazu: {error}") from error
        data = src.read_bytes()
        digest = hashlib.md5(data).hexdigest()[:8]
        stem = safe_filename(src.stem).lower() or role
        name = f"{role}_{stem}_{digest}.png"
        target = self.assets_dir / "hands" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(src, target)
        return f"hands/{name}"

    def ensure_assets(self) -> None:
        assets = self.assets_dir
        (assets / "fonts").mkdir(parents=True, exist_ok=True)
        (assets / "weather").mkdir(parents=True, exist_ok=True)
        (assets / "status").mkdir(parents=True, exist_ok=True)
        (assets / "icons").mkdir(parents=True, exist_ok=True)
        (assets / "hands").mkdir(parents=True, exist_ok=True)
        for font in C.BUILTIN_FONTS:
            source = C.BUILTIN_FONTS_DIR / font
            target = assets / "fonts" / font
            if source.exists() and not target.exists():
                shutil.copy2(source, target)
        for icon in C.WEATHER_FILES:
            source = C.BUILTIN_WEATHER_DIR / icon
            target = assets / "weather" / icon
            if source.exists() and not target.exists():
                shutil.copy2(source, target)
        for icon in C.STATUS_FILES.values():
            source = C.BUILTIN_DIR / icon
            target = assets / icon
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.exists() and not target.exists():
                shutil.copy2(source, target)
        for name in C.HAND_FILES.values():
            source = C.BUILTIN_HANDS_DIR / name
            target = assets / "hands" / name
            if source.exists() and not target.exists():
                shutil.copy2(source, target)

    def save(self, root: Path | None = None) -> Path:
        if root is not None:
            self.root = Path(root)
        if self.root is None:
            raise RuntimeError("Brak katalogu projektu")
        self.root.mkdir(parents=True, exist_ok=True)
        self.ensure_assets()
        data = self.to_dict()
        (self.root / "project.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.root / "project.json"

    @classmethod
    def load(cls, root: Path) -> Project:
        root = Path(root)
        file = root / "project.json"
        if not file.exists():
            raise FileNotFoundError(f"Brak pliku project.json w {root}")
        data = json.loads(file.read_text(encoding="utf-8"))
        prj = cls.from_dict(data, root)
        prj.ensure_assets()
        return prj

    def add_element(self, kind: str, x: int | None = None, y: int | None = None) -> Element:
        w, h = DEFAULT_SIZE.get(kind, (100, 100))
        if kind == "analog_hands":
            # Oś obrotu wskazówek to środek ramki, więc domyślnie obejmuje cały
            # ekran — inaczej środek wypada poza tarczą i widać tylko kropkę.
            x = 0 if x is None else x
            y = 0 if y is None else y
        if x is None:
            x = int((C.DEVICE["width"] - w) / 2)
        if y is None:
            y = int((C.DEVICE["height"] - h) / 2)
        el = Element(type=kind, name=self.next_name(kind), x=x, y=y, w=w, h=h)
        self.elements.append(el)
        return el

    def next_name(self, kind: str) -> str:
        label = TYPE_LABELS.get(kind, kind)
        count = sum(1 for e in self.elements if e.type == kind) + 1
        return f"{label} {count}"

    def unique_root(self, base: Path | None = None) -> Path:
        base = base or C.PROJECTS_DIR
        base.mkdir(parents=True, exist_ok=True)
        slug = slugify(self.name)
        candidate = base / slug
        i = 2
        while candidate.exists():
            candidate = base / f"{slug}-{i}"
            i += 1
        return candidate


class History:
    def __init__(self, limit: int = 80) -> None:
        self._states: list[dict[str, Any]] = []
        self._index = -1
        self._limit = limit

    def reset(self, state: dict[str, Any]) -> None:
        self._states = [copy.deepcopy(state)]
        self._index = 0

    def push(self, state: dict[str, Any]) -> None:
        if self._index >= 0 and self._states[self._index] == state:
            return
        self._states = self._states[: self._index + 1]
        self._states.append(copy.deepcopy(state))
        if len(self._states) > self._limit:
            self._states.pop(0)
        self._index = len(self._states) - 1

    @property
    def can_undo(self) -> bool:
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        return self._index < len(self._states) - 1

    def undo(self) -> dict[str, Any] | None:
        if not self.can_undo:
            return None
        self._index -= 1
        return copy.deepcopy(self._states[self._index])

    def redo(self) -> dict[str, Any] | None:
        if not self.can_redo:
            return None
        self._index += 1
        return copy.deepcopy(self._states[self._index])


def make_project(name: str, template: str = "Cyfrowa", root: Path | None = None) -> Project:
    prj = Project(name=name, root=root)
    if template == "Pusta":
        return prj
    if template == "Minimal":
        _template_minimal(prj)
    elif template == "Sportowa":
        _template_sport(prj)
    elif template == "Pogodowa":
        _template_weather(prj)
    else:
        _template_digital(prj)
    return prj


def _template_digital(prj: Project) -> None:
    prj.background_color = "#05070D"
    time_el = Element(
        type="time",
        name="Godzina",
        x=73,
        y=150,
        w=320,
        h=120,
        props={"size": 92, "font": "fonts/Rajdhani-Bold.ttf", "color": "#FFFFFF"},
    )
    date_el = Element(
        type="date",
        name="Data",
        x=83,
        y=272,
        w=300,
        h=34,
        props={
            "format": "dddd, DD.MM",
            "size": 22,
            "font": "fonts/Rajdhani-Medium.ttf",
            "color": "#8FA6C8",
        },
    )
    steps = Element(
        type="data",
        name="Kroki",
        x=42,
        y=352,
        w=140,
        h=44,
        props={"source": "steps", "size": 30, "color": "#35C4FF"},
    )
    hr = Element(
        type="data",
        name="Tętno",
        x=284,
        y=352,
        w=140,
        h=44,
        props={"source": "heart", "size": 30, "color": "#FF5252"},
    )
    battery = Element(
        type="progress_ring",
        name="Bateria",
        x=193,
        y=330,
        w=80,
        h=80,
        props={
            "source": "battery",
            "line_width": 5,
            "color": "#2EE66B",
            "bg_color": "#1B2637",
            "start_angle": 0,
            "end_angle": 360,
        },
    )
    prj.elements.extend([time_el, date_el, steps, hr, battery])


def _template_minimal(prj: Project) -> None:
    prj.background_color = "#000000"
    time_el = Element(
        type="time",
        name="Godzina",
        x=53,
        y=173,
        w=360,
        h=120,
        props={"size": 104, "font": "fonts/ChakraPetch-Bold.ttf", "color": "#FFFFFF"},
    )
    date_el = Element(
        type="date",
        name="Data",
        x=83,
        y=290,
        w=300,
        h=28,
        props={
            "format": "DD.MM.YYYY",
            "size": 18,
            "font": "fonts/ChakraPetch-Regular.ttf",
            "color": "#7A8798",
        },
    )
    prj.elements.extend([time_el, date_el])


def _template_sport(prj: Project) -> None:
    prj.background_color = "#080B12"
    prj.elements.append(
        Element(
            type="time",
            name="Godzina",
            x=83,
            y=52,
            w=300,
            h=90,
            props={"size": 72, "font": "fonts/BebasNeue-Regular.ttf", "color": "#FFFFFF"},
        )
    )
    prj.elements.append(
        Element(
            type="progress_ring",
            name="Kroki",
            x=73,
            y=160,
            w=320,
            h=320,
            props={
                "source": "steps",
                "line_width": 10,
                "color": "#35C4FF",
                "bg_color": "#172033",
                "start_angle": 135,
                "end_angle": 405,
            },
        )
    )
    prj.elements.append(
        Element(
            type="data",
            name="Kroki",
            x=153,
            y=250,
            w=160,
            h=80,
            props={"source": "steps", "size": 58, "color": "#FFFFFF"},
        )
    )
    prj.elements.append(
        Element(
            type="data",
            name="Tętno",
            x=92,
            y=356,
            w=130,
            h=36,
            props={"source": "heart", "size": 24, "color": "#FF5252"},
        )
    )
    prj.elements.append(
        Element(
            type="data",
            name="Kalorie",
            x=244,
            y=356,
            w=130,
            h=36,
            props={"source": "calories", "size": 24, "color": "#FFD54A"},
        )
    )


def _template_weather(prj: Project) -> None:
    prj.background_color = "#071320"
    prj.elements.append(
        Element(
            type="time",
            name="Godzina",
            x=93,
            y=96,
            w=280,
            h=110,
            props={"size": 84, "font": "fonts/Rajdhani-Bold.ttf", "color": "#FFFFFF"},
        )
    )
    prj.elements.append(
        Element(
            type="date",
            name="Data",
            x=83,
            y=210,
            w=300,
            h=30,
            props={
                "format": "dddd, DD.MM",
                "size": 20,
                "font": "fonts/Rajdhani-Medium.ttf",
                "color": "#8FA6C8",
            },
        )
    )
    prj.elements.append(
        Element(
            type="data",
            name="Lokalizacja",
            x=83,
            y=242,
            w=300,
            h=24,
            props={
                "source": "city",
                "size": 18,
                "font": "fonts/Rajdhani-Medium.ttf",
                "color": "#8FA6C8",
            },
        )
    )
    prj.elements.append(
        Element(
            type="weather_icon",
            name="Pogoda",
            x=125,
            y=270,
            w=72,
            h=72,
            props={"size": 72},
        )
    )
    prj.elements.append(
        Element(
            type="data",
            name="Temperatura",
            x=205,
            y=280,
            w=140,
            h=60,
            props={"source": "weather_temp", "size": 46, "color": "#FFD54A", "unit": True},
        )
    )
    prj.elements.append(
        Element(
            type="shortcut",
            name="Skrót: pogoda",
            x=323,
            y=278,
            w=48,
            h=48,
            props={"kind": "app", "app": "Weather"},
        )
    )
