from __future__ import annotations

import datetime as _dt
import io
import math
import random
import re
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRawFont,
    QTransform,
)

from . import constants as C
from . import imaging, timeformat
from .model import (
    SAMPLE_TIME,
    BarArc,
    Element,
    Project,
    bar_arc_fill,
    bar_arc_geometry,
    bar_frame_ratio,
    bar_reveal_geometry,
    hand_sources,
    rotation_center,
    supports_rotation,
)

POLISH_CHARS = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"
_font_families: dict[str, str] = {}
_font_faces: dict[str, tuple[str, str, int]] = {}
_pixmap_cache: dict[tuple[str, int, int, int], QPixmap] = {}
_polish_cache: dict[str, tuple[str, ...]] = {}


def font_missing_polish(path: Path) -> tuple[str, ...]:
    key = str(path).lower()
    cached = _polish_cache.get(key)
    if cached is not None:
        return cached
    raw = QRawFont(str(path), 16)
    if not raw.isValid():
        missing: tuple[str, ...] = ()
    else:
        indexes = raw.glyphIndexesForString(POLISH_CHARS)
        missing = tuple(c for c, index in zip(POLISH_CHARS, indexes) if index == 0)
    _polish_cache[key] = missing
    return missing


def register_font(path: Path) -> str:
    key = str(path).lower()
    if key in _font_families:
        return _font_families[key]
    family = ""
    if path.exists():
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id >= 0:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                family = families[0]
    _font_families[key] = family
    return family


def register_project_fonts(project: Project) -> None:
    if project.root is None:
        return
    for path in (project.root / "assets" / "fonts").glob("*"):
        if path.suffix.lower() in (".ttf", ".otf"):
            register_font(path)


def _weight_style(family: str, weight: int) -> str:
    """Wybiera styl rodziny o wadze najbliższej podanej (np. 700 -> Bold)."""
    best = ""
    best_diff = 1 << 30
    for candidate in QFontDatabase.styles(family):
        font = QFontDatabase.font(family, candidate, 10)
        diff = abs(int(font.weight()) - int(weight))
        if diff < best_diff:
            best = candidate
            best_diff = diff
    return best


def _match_style(family: str, style: str, weight: int = 400) -> str:
    if not family:
        return style
    styles = QFontDatabase.styles(family)
    if not styles:
        return style
    if style and style in styles:
        return style
    target = style.replace(" ", "").replace("-", "").lower()
    for candidate in styles:
        normalized = candidate.replace(" ", "").replace("-", "").lower()
        if normalized == target:
            return candidate
    # Nie ma stylu o dokładnie tej nazwie - wybierz wariant po wadze.
    return _weight_style(family, weight) or style


def font_face(path: Path) -> tuple[str, str, int]:
    """Zwraca rodzinę, dokładny styl i wagę pliku czcionki (np. Rajdhani + Bold + 700).

    Samo QFont(rodzina) wybiera styl Regular, nawet jeśli element wskazuje
    plik Bold/Medium. Dlatego nazwa stylu i waga są ustawiane jawnie, aby
    podgląd i edytor rysowały dokładnie ten sam krój, którego użyje zegarek.
    """
    key = str(path).lower()
    if key in _font_faces:
        return _font_faces[key]
    family = register_font(path)
    style = ""
    weight = 400
    if path.exists():
        raw = QRawFont(str(path), 16)
        if raw.isValid():
            family = raw.familyName() or family
            style = raw.styleName() or ""
            weight = int(raw.weight())
    style = _match_style(family, style, weight)
    _font_faces[key] = (family, style, weight)
    return family, style, weight


def font_for(project: Project, rel: str, size: int) -> QFont:
    family = ""
    style = ""
    weight = 400
    if rel and project.root is not None:
        family, style, weight = font_face(project.root / "assets" / rel)
    font = QFont(family) if family else QFont()
    if style:
        font.setStyleName(style)
    if family:
        # QFont.Weight ma wartości 100..900; zaokrąglenie chroni przed
        # nietypowymi wagami z plików OTF.
        step = max(100, min(900, int(round(weight / 100.0) * 100)))
        font.setWeight(QFont.Weight(step))
    font.setPixelSize(max(1, int(size)))
    font.setStyleStrategy(QFont.PreferAntialias)
    return font


def qcolor(value: str, alpha: int = 255) -> QColor:
    color = QColor(value)
    if not color.isValid():
        color = QColor("#FFFFFF")
    color.setAlpha(max(0, min(255, int(alpha))))
    return color


def pixmap_for(project: Project, rel: str, width: int = 0, height: int = 0) -> QPixmap | None:
    path = project.asset_file(rel)
    if path is None:
        return None
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        stamp = 0
    key = (str(path).lower(), int(width), int(height), int(stamp))
    if key in _pixmap_cache:
        return _pixmap_cache[key]
    image = imaging.load_resized(path, width, height)
    if image is None:
        return None
    pix = QPixmap.fromImage(image)
    if pix.isNull():
        return None
    _pixmap_cache[key] = pix
    return pix


def sample_value(source: str, element: Element | None = None) -> tuple[str, float]:
    info = C.DATA_SOURCES.get(source, {})
    sample = str(info.get("sample", "0"))
    ratio = 0.0
    source_ratios = {
        "steps": 8670 / 10000,
        "steps_target": 1.0,
        "calories": 280 / 2000,
        "calories_target": 1.0,
        "distance": 5.30 / 10,
        "heart": 86 / 200,
        "pai": 45 / 100,
        "stand": 8 / 12,
        "battery": 75 / 100,
        "stress": 35 / 100,
        "spo2": 98 / 100,
        "sleep": 452 / 480,
        "weather_temp": 0.6,
        "weather_low": 0.4,
        "weather_high": 0.75,
        "humidity": 42 / 100,
        "uvi": 4 / 11,
        "aqi": 26 / 500,
        "floor": 0.4,
        "training_load": 0.55,
        "vo2max": 0.6,
        "readiness": 0.82,
        "recovery_time": 0.3,
        "bio_charge": 0.7,
        "body_temp": 0.6,
    }
    ratio = source_ratios.get(source, 0.0)
    return sample, max(0.0, min(1.0, ratio))


_RATIO_TARGET: dict[str, float] = {
    "steps": 10000.0,
    "steps_target": 10000.0,
    "calories": 2000.0,
    "calories_target": 2000.0,
    "distance": 10.0,
    "heart": 200.0,
    "pai": 75.0,
    "stand": 12.0,
    "battery": 100.0,
    "stress": 100.0,
    "spo2": 100.0,
    "sleep": 480.0,
    "floor": 30.0,
    "training_load": 1000.0,
    "vo2max": 65.0,
    "readiness": 100.0,
    "recovery_time": 97.0,
    "bio_charge": 100.0,
    "body_temp": 40.0,
    "weather_temp": 40.0,
    "weather_low": 40.0,
    "weather_high": 40.0,
    "humidity": 100.0,
    "uvi": 11.0,
    "aqi": 500.0,
    "pressure": 1200.0,
    "altitude": 1200.0,
    "countdown": 60.0,
    "stopwatch": 60.0,
}

_RANDOM_RANGES: dict[str, tuple[int, int]] = {
    "steps": (2000, 16000),
    "calories": (80, 900),
    "heart": (55, 150),
    "pai": (5, 75),
    "stand": (2, 12),
    "battery": (15, 100),
    "stress": (5, 90),
    "spo2": (92, 100),
    "floor": (0, 28),
    "fat_burning": (0, 120),
    "training_load": (100, 900),
    "vo2max": (35, 60),
    "readiness": (30, 100),
    "recovery_time": (1, 72),
    "bio_charge": (20, 100),
    "humidity": (20, 95),
    "uvi": (0, 11),
    "aqi": (5, 200),
    "pressure": (980, 1040),
    "altitude": (0, 1200),
    "countdown": (1, 60),
    "stopwatch": (1, 60),
}

_TIME_WINDOWS = {
    "sleep": (5, 9),
    "sun_rise": (4, 8),
    "sun_set": (16, 21),
    "alarm_time": (5, 9),
}

_CITY_SAMPLES = ("Warszawa", "Kraków", "Gdańsk", "Wrocław", "Poznań", "Łódź", "Katowice", "Szczecin")
_WEATHER_SOURCES = ("weather_temp", "weather_low", "weather_high")


def _ratio_for(source: str, value: float) -> float:
    target = _RATIO_TARGET.get(source)
    if target:
        return max(0.0, min(1.0, value / target))
    info = C.DATA_SOURCES.get(source, {})
    low, high = info.get("range", (0, 1))
    if high <= low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def sample_entry(source: str, text: str) -> tuple[str, float]:
    """Zamienia wpisaną wartość na parę (tekst, udział 0..1) dla podglądu.

    Obsługuje liczby (także z przecinkiem), wartości z jednostką oraz godziny
    zapisane jako ``HH:MM`` (np. sen, wschód słońca).
    """
    text = str(text).strip()
    info = C.DATA_SOURCES.get(source, {})
    unit = str(info.get("unit", "") or "")
    raw = text
    if unit and raw.endswith(unit):
        raw = raw[: -len(unit)].strip()
    if ":" in raw:
        parts = raw.split(":")
        try:
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            seconds = int(parts[2]) if len(parts) > 2 else 0
        except ValueError:
            return (text, 0.0)
        minutes = max(0, min(59, minutes))
        total = hours * 60 + minutes + seconds / 60.0
        suffix = f":{seconds:02d}" if len(parts) > 2 else ""
        return (f"{hours:02d}:{minutes:02d}{suffix}", _ratio_for(source, total))
    raw = raw.replace(",", ".")
    try:
        value = float(raw)
    except ValueError:
        return (text, 0.0)
    if source == "distance":
        formatted = f"{value:.2f}"
    elif source == "body_temp":
        formatted = f"{value:.1f}"
    elif abs(value - round(value)) < 1e-9:
        formatted = str(int(round(value)))
    else:
        formatted = f"{value:g}"
    return (formatted, _ratio_for(source, value))


def random_samples(rng: random.Random | None = None) -> dict[str, tuple[str, float]]:
    """Losowe, ale realistyczne wartości przykładowe dla wszystkich źródeł danych."""
    rng = rng or random.Random()
    result: dict[str, tuple[str, float]] = {}
    for source, info in C.DATA_SOURCES.items():
        if source in _WEATHER_SOURCES:
            continue
        if source.endswith("_target"):
            value = float(str(info.get("sample", "0")) or 0)
            result[source] = (str(int(value)), _ratio_for(source, value))
            continue
        if source in _TIME_WINDOWS:
            start_hour, end_hour = _TIME_WINDOWS[source]
            hour = rng.randint(start_hour, end_hour)
            minute = rng.randrange(60)
            value = float(hour * 60 + minute)
            text = f"{hour:02d}:{minute:02d}"
        elif source == "city":
            result[source] = (rng.choice(_CITY_SAMPLES), 0.0)
            continue
        elif source == "distance":
            value = rng.uniform(0.5, 12.0)
            text = f"{value:.2f}"
        elif source == "body_temp":
            value = rng.uniform(35.5, 38.0)
            text = f"{value:.1f}"
        else:
            low, high = _RANDOM_RANGES.get(source, info.get("range", (0, 100)))
            value = float(rng.randint(int(low), int(high)))
            text = str(int(value))
        result[source] = (text, _ratio_for(source, value))

    temperature = rng.randint(-5, 30)
    low = temperature - rng.randint(2, 7)
    high = temperature + rng.randint(2, 7)
    result["weather_temp"] = (str(temperature), _ratio_for("weather_temp", temperature))
    result["weather_low"] = (str(low), _ratio_for("weather_low", low))
    result["weather_high"] = (str(high), _ratio_for("weather_high", high))
    return result


def random_moment(rng: random.Random | None = None) -> _dt.datetime:
    rng = rng or random.Random()
    start = _dt.datetime(_dt.date.today().year, 1, 1)
    moment = start + _dt.timedelta(days=rng.randrange(365))
    return moment.replace(hour=rng.randrange(24), minute=rng.randrange(60), second=rng.randrange(60))


def fmt_time(moment: _dt.datetime, props: dict) -> str:
    return timeformat.format_time(moment.hour, moment.minute, moment.second, props)


_DATE_TOKENS = ("YYYY", "MMMM", "dddd", "MMM", "ddd", "YY", "DD", "MM", "D", "M")
_DATE_TOKEN_RE = re.compile("|".join(_DATE_TOKENS))


def fmt_date(moment: _dt.date, pattern: str, lang: str) -> str:
    weekday = moment.isoweekday()
    days = C.WEEKDAYS.get(lang, C.WEEKDAYS["pl"])
    months = C.MONTHS.get(lang, C.MONTHS["pl"])
    tokens = {
        "YYYY": f"{moment.year:04d}",
        "YY": f"{moment.year % 100:02d}",
        "MMMM": months["full"][moment.month - 1],
        "MMM": months["short"][moment.month - 1],
        "dddd": days["full"][weekday - 1],
        "ddd": days["short"][weekday - 1],
        "DD": f"{moment.day:02d}",
        "D": str(moment.day),
        "MM": f"{moment.month:02d}",
        "M": str(moment.month),
    }
    # Jednorazowe skanowanie wzorca: podstawione nazwy dni/miesięcy nie są już
    # przeszukiwane, więc np. "M" nie zamienia liter w "Monday"/"May" ani
    # "D" w "December".
    return _DATE_TOKEN_RE.sub(lambda match: tokens[match.group(0)], pattern)


DATA_UNITS = {
    "%": "",
    "°C": "°C",
    "bpm": " bpm",
    "kcal": " kcal",
    "km": " km",
    "min": " min",
    "h": " h",
    "hPa": " hPa",
    "m": " m",
}


def _unit_suffix(unit: str) -> str:
    return DATA_UNITS.get(unit, f" {unit}" if unit else "")


ELLIPSIS = "\u2026"


def _line_width(metrics: QFontMetricsF, text: str, spacing: int) -> float:
    """Szerokość linii z odstępem liczonym tylko między znakami.

    Zegarek (`char_space`) dodaje odstęp między kolejnymi znakami, nigdy po
    ostatnim. Qt z `QFont.AbsoluteSpacing` dokłada go również na końcu, co
    przesuwa tekst wyrównany do środka i do prawej - dlatego pozycję liczymy
    sami, a nie przez `Qt.AlignHCenter`/`Qt.AlignRight`.
    """
    width = metrics.horizontalAdvance(text)
    if spacing and len(text) > 1:
        width += spacing * (len(text) - 1)
    return width


def _fit_line(metrics: QFontMetricsF, text: str, spacing: int, max_width: float) -> str:
    """Skraca linię wielokropkiem, jak `hmUI.text_style.ELLIPSIS` na zegarku."""
    if not text or max_width <= 0:
        return ""
    if _line_width(metrics, text, spacing) <= max_width:
        return text
    if _line_width(metrics, ELLIPSIS, spacing) > max_width:
        return ""
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        candidate = text[:mid].rstrip() + ELLIPSIS
        if _line_width(metrics, candidate, spacing) <= max_width:
            low = mid
        else:
            high = mid - 1
    return text[:low].rstrip() + ELLIPSIS


def _draw_text(
    painter: QPainter,
    rect: QRectF,
    text: str,
    font: QFont,
    color: QColor,
    align: str,
    valign: str = "center",
    spacing: int = 0,
    line_space: int = 0,
) -> None:
    """Rysuje tekst tak, jak robi to widget TEXT na zegarku.

    Pozycję liczymy z metryk czcionki zamiast z flag `drawText`, bo wtedy
    podgląd zgadza się z zegarkiem również przy `char_space` i przy tekście
    dłuższym niż ramka (zegarek ustawia wtedy wielokropek).
    """
    text = str(text)
    if not text or rect.width() <= 0 or rect.height() <= 0:
        return
    metrics_font = QFont(font)
    metrics_font.setLetterSpacing(QFont.AbsoluteSpacing, 0.0)
    metrics = QFontMetricsF(metrics_font)
    lines = [_fit_line(metrics, line, spacing, rect.width()) for line in text.split("\n")]

    line_height = metrics.height()
    block_height = line_height * len(lines) + line_space * max(0, len(lines) - 1)
    if valign == "top":
        top = rect.top()
    elif valign == "bottom":
        top = rect.bottom() - block_height
    else:
        top = rect.center().y() - block_height / 2

    if spacing:
        font.setLetterSpacing(QFont.AbsoluteSpacing, float(spacing))
    painter.save()
    painter.setFont(font)
    painter.setPen(color)
    painter.setClipRect(rect)
    for index, line in enumerate(lines):
        if not line:
            continue
        width = _line_width(metrics, line, spacing)
        if align == "left":
            x = rect.left()
        elif align == "right":
            x = rect.right() - width
        else:
            x = rect.center().x() - width / 2
        baseline = top + line_height * index + metrics.ascent()
        painter.drawText(QPointF(round(x), round(baseline)), line)
    painter.restore()


def _draw_placeholder(painter: QPainter, rect: QRectF, text: str) -> None:
    pen = QPen(QColor(120, 140, 170, 140), 1, Qt.DashLine)
    painter.setPen(pen)
    painter.setBrush(QColor(70, 90, 120, 40))
    painter.drawRoundedRect(rect, 4, 4)
    painter.setPen(QColor(160, 180, 210, 200))
    font = QFont()
    font.setPixelSize(max(9, int(min(rect.width(), rect.height()) / 7)))
    painter.setFont(font)
    painter.drawText(rect, int(Qt.AlignCenter | Qt.TextWordWrap), text)


def _draw_ring(painter: QPainter, el: Element, ratio: float, preview: bool) -> None:
    p = el.props
    rect = QRectF(el.x, el.y, el.w, el.h)
    line_width = max(1, int(p.get("line_width", 8)))
    radius_override = int(p.get("radius", 0) or 0)
    radius = radius_override if radius_override > 0 else min(el.w, el.h) / 2 - line_width / 2
    center = rect.center()
    arc_rect = QRectF(
        center.x() - radius,
        center.y() - radius,
        radius * 2,
        radius * 2,
    )
    start_angle = int(p.get("start_angle", 0))
    end_angle = int(p.get("end_angle", 360))
    span = end_angle - start_angle
    pen = QPen(qcolor(p.get("bg_color", "#22304A")), line_width)
    pen.setCapStyle(Qt.RoundCap if int(p.get("corner_flag", 0)) else Qt.FlatCap)
    bg = QColor(p.get("bg_color", "")) if p.get("bg_color") else None
    if bg is not None and bg.isValid() and bool(p.get("show_bg", True)):
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(arc_rect, int(-start_angle * 16), int(-span * 16))
    fg = qcolor(p.get("color", "#4D9BFF"))
    pen = QPen(fg, line_width)
    pen.setCapStyle(Qt.RoundCap if int(p.get("corner_flag", 0)) else Qt.FlatCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawArc(arc_rect, int(-start_angle * 16), int(-span * ratio * 16))
    if not preview:
        painter.setPen(QPen(QColor(120, 150, 200, 70), 1, Qt.DotLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(arc_rect)


def _arc_band_path(
    geometry: BarArc, start: float, span: float, round_cap: bool = False
) -> QPainterPath:
    """Ścieżka grubego odcinka łuku (zewnętrzna + wewnętrzna krawędź)."""
    path = QPainterPath()
    if span <= 0.001:
        return path
    outer_radius = geometry.radius + geometry.line_width / 2.0
    inner_radius = max(0.0, geometry.radius - geometry.line_width / 2.0)
    outer = QRectF(
        geometry.center_x - outer_radius,
        geometry.center_y - outer_radius,
        outer_radius * 2,
        outer_radius * 2,
    )
    inner = QRectF(
        geometry.center_x - inner_radius,
        geometry.center_y - inner_radius,
        inner_radius * 2,
        inner_radius * 2,
    )
    path.arcMoveTo(outer, -start)
    path.arcTo(outer, -start, -span)
    path.arcTo(inner, -(start + span), span)
    path.closeSubpath()
    if round_cap and geometry.line_width > 1:
        cap = geometry.line_width / 2.0
        for angle in (start, start + span):
            rad = math.radians(angle)
            center = QPointF(
                geometry.center_x + geometry.radius * math.cos(rad),
                geometry.center_y + geometry.radius * math.sin(rad),
            )
            path.addEllipse(center, cap, cap)
    return path


def _draw_arc_stroke(
    painter: QPainter,
    geometry: BarArc,
    start: float,
    span: float,
    color: QColor,
    round_cap: bool,
) -> None:
    if span <= 0.001:
        return
    pen = QPen(color, geometry.line_width)
    pen.setCapStyle(Qt.RoundCap if round_cap else Qt.FlatCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    rect = QRectF(
        geometry.center_x - geometry.radius,
        geometry.center_y - geometry.radius,
        geometry.radius * 2,
        geometry.radius * 2,
    )
    painter.drawArc(
        rect,
        int(round(-start * 16)),
        int(round(-span * 16)),
    )


def _draw_bar_solid(
    painter: QPainter, el: Element, ratio: float, reverse: bool
) -> None:
    p = el.props
    rect = QRectF(el.x, el.y, el.w, el.h)
    radius = max(0.0, float(p.get("radius", 0) or 0))
    bg = QColor(str(p.get("bg_color", ""))) if p.get("bg_color") else None
    if bg is not None and bg.isValid() and bool(p.get("show_bg", True)):
        r = min(radius, rect.width() / 2.0, rect.height() / 2.0)
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, r, r)
    if ratio <= 0:
        return
    x, y, width, height, _pos_x, _pos_y = bar_reveal_geometry(el, ratio, reverse)
    fill = QRectF(x, y, width, height)
    r = min(radius, fill.width() / 2.0, fill.height() / 2.0)
    painter.setPen(Qt.NoPen)
    painter.setBrush(qcolor(str(p.get("color", "#4D9BFF"))))
    painter.drawRoundedRect(fill, r, r)


def _draw_bar_image(
    painter: QPainter,
    project: Project,
    el: Element,
    ratio: float,
    reverse: bool,
) -> None:
    p = el.props
    pix0 = pixmap_for(project, str(p.get("src0", "") or ""), el.w, el.h)
    pix1 = pixmap_for(project, str(p.get("src100", "") or ""), el.w, el.h)
    if pix1 is None:
        _draw_bar_solid(painter, el, ratio, reverse)
        return
    show_bg = bool(p.get("show_bg", True))
    if pix0 is not None and show_bg:
        painter.drawPixmap(el.x, el.y, pix0)
    else:
        bg = QColor(str(p.get("bg_color", ""))) if p.get("bg_color") else None
        if bg is not None and bg.isValid() and show_bg:
            rect = QRectF(el.x, el.y, el.w, el.h)
            radius = max(0.0, float(p.get("radius", 0) or 0))
            radius = min(radius, rect.width() / 2.0, rect.height() / 2.0)
            painter.setPen(Qt.NoPen)
            painter.setBrush(bg)
            painter.drawRoundedRect(rect, radius, radius)
    if ratio <= 0:
        return
    x, y, width, height, _pos_x, _pos_y = bar_reveal_geometry(el, ratio, reverse)
    painter.save()
    painter.setClipRect(QRectF(x, y, width, height))
    painter.drawPixmap(el.x, el.y, pix1)
    painter.restore()


def _draw_bar_arc_solid(
    painter: QPainter, el: Element, ratio: float, reverse: bool
) -> None:
    geometry = bar_arc_geometry(el)
    if geometry is None:
        _draw_bar_solid(painter, el, ratio, reverse)
        return
    p = el.props
    round_cap = bool(int(p.get("corner_flag", 0) or 0))
    bg = QColor(str(p.get("bg_color", ""))) if p.get("bg_color") else None
    if bg is not None and bg.isValid() and bool(p.get("show_bg", True)):
        _draw_arc_stroke(
            painter,
            geometry,
            geometry.start_angle,
            geometry.end_angle - geometry.start_angle,
            bg,
            round_cap,
        )
    if ratio <= 0:
        return
    start, end = bar_arc_fill(geometry, ratio, reverse)
    _draw_arc_stroke(
        painter,
        geometry,
        start,
        end - start,
        qcolor(str(p.get("color", "#4D9BFF"))),
        round_cap,
    )


def _draw_bar_arc_image(
    painter: QPainter,
    project: Project,
    el: Element,
    ratio: float,
    reverse: bool,
) -> None:
    geometry = bar_arc_geometry(el)
    if geometry is None:
        _draw_bar_image(painter, project, el, ratio, reverse)
        return
    p = el.props
    round_cap = bool(int(p.get("corner_flag", 0) or 0))
    full_span = geometry.end_angle - geometry.start_angle
    bg = QColor(str(p.get("bg_color", ""))) if p.get("bg_color") else None
    show_bg = bool(p.get("show_bg", True))
    if bg is not None and bg.isValid() and show_bg:
        _draw_arc_stroke(
            painter,
            geometry,
            geometry.start_angle,
            full_span,
            bg,
            round_cap,
        )
    pix0 = pixmap_for(project, str(p.get("src0", "") or ""), el.w, el.h)
    if pix0 is not None and show_bg:
        painter.save()
        painter.setClipPath(
            _arc_band_path(geometry, geometry.start_angle, full_span, round_cap)
        )
        painter.drawPixmap(el.x, el.y, pix0)
        painter.restore()
    if ratio <= 0:
        return
    pix1 = pixmap_for(project, str(p.get("src100", "") or ""), el.w, el.h)
    if pix1 is None:
        start, end = bar_arc_fill(geometry, ratio, reverse)
        _draw_arc_stroke(
            painter,
            geometry,
            start,
            end - start,
            qcolor(str(p.get("color", "#4D9BFF"))),
            round_cap,
        )
        return
    start, end = bar_arc_fill(geometry, ratio, reverse)
    painter.save()
    painter.setClipPath(_arc_band_path(geometry, start, end - start))
    painter.drawPixmap(el.x, el.y, pix1)
    painter.restore()


def _draw_bar(
    painter: QPainter,
    project: Project,
    el: Element,
    ratio: float,
) -> None:
    p = el.props
    reverse = bool(p.get("reverse", False))
    src100 = str(p.get("src100", "") or "")
    image_mode = (
        str(p.get("style", "solid")) == "image"
        and bool(src100)
        and project.asset_file(src100) is not None
    )
    geometry = bar_arc_geometry(el)
    if geometry is not None:
        if image_mode:
            # Zegarek ma tylko 51 klatek obrazu, więc podgląd i edytor
            # zaokrąglają postęp do tej samej klatki.
            ratio = bar_frame_ratio(ratio)
            _draw_bar_arc_image(painter, project, el, ratio, reverse)
        else:
            _draw_bar_arc_solid(painter, el, ratio, reverse)
    elif image_mode:
        _draw_bar_image(painter, project, el, ratio, reverse)
    else:
        _draw_bar_solid(painter, el, ratio, reverse)


def render_bar_frame(
    project: Project, el: Element, ratio: float, path: Path
) -> None:
    """Renderuje pojedynczą klatkę paska (0%..100%) do pliku PNG."""
    width = max(1, int(el.w))
    height = max(1, int(el.h))
    image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    painter.translate(-el.x, -el.y)
    _draw_bar(painter, project, el, ratio)
    painter.end()
    imaging.write_png(image.convertToFormat(QImage.Format_ARGB32), Path(path))


def render_text_image(project: Project, el: Element, path: Path) -> None:
    """Rasteryzuje stały tekst do PNG (obrót tekstu na zegarku).

    Zegarek nie obraca widgetów TEXT, więc tekst z obrotem jest wysyłany jako
    obraz w ramce elementu. Obraz jest rysowany bez obrotu - kąt ustawia widget
    IMG - dzięki temu edytor i zegarek pokazują to samo.
    """
    width = max(1, int(el.w))
    height = max(1, int(el.h))
    image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.translate(-el.x, -el.y)
    p = el.props
    font = font_for(project, str(p.get("font", "")), int(p.get("size", 32)))
    _draw_text(
        painter,
        QRectF(el.x, el.y, el.w, el.h),
        str(p.get("text", "")),
        font,
        qcolor(p.get("color", "#FFFFFF")),
        str(p.get("align", "center")),
        str(p.get("valign", "center")),
        int(p.get("spacing", 0) or 0),
    )
    painter.end()
    imaging.write_png(image.convertToFormat(QImage.Format_ARGB32), Path(path))


def render_project(
    painter: QPainter,
    project: Project,
    target: QRectF,
    *,
    live: bool = False,
    preview: bool = False,
    now: _dt.datetime | None = None,
    clip_circle: bool = True,
    samples: dict[str, tuple[str, float]] | None = None,
    weather_index: int | None = None,
) -> None:
    register_project_fonts(project)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    transform = QTransform()
    transform.translate(target.x(), target.y())
    scale = target.width() / C.DEVICE["width"]
    transform.scale(scale, scale)
    painter.setTransform(transform, True)

    if clip_circle:
        path = QPainterPath()
        path.addEllipse(QRectF(0, 0, C.DEVICE["width"], C.DEVICE["height"]))
        painter.setClipPath(path)

    painter.fillRect(QRectF(0, 0, C.DEVICE["width"], C.DEVICE["height"]), qcolor(project.background_color))
    bg = pixmap_for(project, project.background_image, C.DEVICE["width"], C.DEVICE["height"])
    if bg is not None:
        painter.drawPixmap(0, 0, bg)

    moment = now or (_dt.datetime.now() if live else SAMPLE_TIME)
    day = moment.date()

    for el in project.elements:
        if not el.visible:
            continue
        rotation = int(el.rotation) if supports_rotation(el.type) else 0
        if rotation:
            center_x, center_y = rotation_center(el)
            painter.save()
            painter.translate(center_x, center_y)
            painter.rotate(rotation)
            painter.translate(-center_x, -center_y)
            _draw_element(painter, project, el, moment, day, preview, samples, weather_index)
            painter.restore()
        else:
            _draw_element(painter, project, el, moment, day, preview, samples, weather_index)

    painter.restore()


def _draw_element(
    painter: QPainter,
    project: Project,
    el: Element,
    moment: _dt.datetime,
    day: _dt.date,
    preview: bool,
    samples: dict[str, tuple[str, float]] | None = None,
    weather_index: int | None = None,
) -> None:
    p = el.props
    rect = QRectF(el.x, el.y, el.w, el.h)
    kind = el.type

    if kind == "image":
        content_x, content_y, content_w, content_h = el.render_rect()
        pix = pixmap_for(project, str(p.get("src", "")), content_w, content_h)
        if pix is None:
            if not preview:
                _draw_placeholder(painter, rect, "Obraz")
            return
        painter.save()
        painter.setOpacity(max(0, min(255, int(p.get("opacity", 255)))) / 255)
        painter.drawPixmap(content_x, content_y, pix)
        painter.restore()
    elif kind == "text":
        font = font_for(project, str(p.get("font", "")), int(p.get("size", 32)))
        _draw_text(
            painter,
            rect,
            str(p.get("text", "")),
            font,
            qcolor(p.get("color", "#FFFFFF")),
            str(p.get("align", "center")),
            str(p.get("valign", "center")),
            int(p.get("spacing", 0) or 0),
        )

    elif kind == "time":
        font = font_for(project, str(p.get("font", "")), int(p.get("size", 96)))
        text = fmt_time(moment, p)
        _draw_text(
            painter,
            rect,
            text,
            font,
            qcolor(p.get("color", "#FFFFFF")),
            str(p.get("align", "center")),
            str(p.get("valign", "center")),
            int(p.get("spacing", 0) or 0),
        )

    elif kind == "date":
        font = font_for(project, str(p.get("font", "")), int(p.get("size", 24)))
        text = fmt_date(day, str(p.get("format", "DD.MM.YYYY")), str(p.get("lang", "pl")))
        _draw_text(
            painter,
            rect,
            text,
            font,
            qcolor(p.get("color", "#FFFFFF")),
            str(p.get("align", "center")),
            str(p.get("valign", "center")),
            int(p.get("spacing", 0) or 0),
        )

    elif kind == "data":
        source = str(p.get("source", "steps"))
        if samples and source in samples:
            value, _ = samples[source]
        else:
            value, _ = sample_value(source)
        pad = int(p.get("pad", 0) or 0)
        if pad:
            value = value.zfill(pad)
        unit = C.DATA_SOURCES.get(source, {}).get("unit", "")
        if p.get("unit") and unit:
            value += _unit_suffix(unit)
        font = font_for(project, str(p.get("font", "")), int(p.get("size", 36)))
        _draw_text(
            painter,
            rect,
            value,
            font,
            qcolor(p.get("color", "#FFFFFF")),
            str(p.get("align", "center")),
            str(p.get("valign", "center")),
            int(p.get("spacing", 0) or 0),
        )

    elif kind == "weather_icon":
        size = int(p.get("size", min(el.w, el.h)))
        index = weather_index if weather_index is not None else 3
        index = max(0, min(len(C.WEATHER_FILES) - 1, int(index)))
        set_name = str(p.get("set", "") or "")
        rel = (
            f"weather_sets/{set_name}/{C.WEATHER_FILES[index]}"
            if set_name
            else f"weather/{C.WEATHER_FILES[index]}"
        )
        pix = pixmap_for(project, rel, size, size)
        if pix is None and set_name:
            pix = pixmap_for(project, f"weather/{C.WEATHER_FILES[index]}", size, size)
        if pix is None:
            if not preview:
                _draw_placeholder(painter, rect, "Pogoda")
            return
        painter.drawPixmap(int(rect.center().x() - size / 2), int(rect.center().y() - size / 2), pix)

    elif kind == "progress_ring":
        source = str(p.get("source", "steps"))
        ratio = samples[source][1] if samples and source in samples else sample_value(source)[1]
        _draw_ring(painter, el, ratio, preview)

    elif kind == "analog_hands":
        _draw_hands(painter, project, el, moment, preview)

    elif kind == "progress_bar":
        source = str(p.get("source", "battery"))
        ratio = samples[source][1] if samples and source in samples else sample_value(source)[1]
        _draw_bar(painter, project, el, ratio)

    elif kind == "shortcut":
        _draw_shortcut(painter, project, el, preview)

    elif kind == "status":
        key = str(p.get("status", "bluetooth"))
        rel = C.STATUS_FILES.get(key, C.STATUS_FILES["bluetooth"])
        size = int(p.get("size", max(el.w, el.h)))
        pix = pixmap_for(project, rel, size, size)
        if pix is not None:
            painter.drawPixmap(int(rect.center().x() - size / 2), int(rect.center().y() - size / 2), pix)
        elif not preview:
            _draw_placeholder(painter, rect, "Status")


def hand_angles(moment: _dt.datetime) -> dict[str, float]:
    """Kąty wskazówek w stopniach (0° = godzina 12, obrót zgodnie z zegarem)."""
    minute = moment.minute + moment.second / 60.0
    hour = (moment.hour % 12) + minute / 60.0
    return {
        "hour": hour * 30.0,
        "minute": minute * 6.0,
        "second": moment.second * 6.0,
    }


def hand_sizes(project: Project, el: Element) -> dict[str, tuple[str, int, int]]:
    """Źródło i docelowy rozmiar każdej wskazówki (wspólna skala dla całego zestawu)."""
    sources = hand_sources(el)
    natural: dict[str, tuple[str, int, int]] = {}
    for role, src in sources.items():
        path = project.asset_file(src)
        if path is None:
            continue
        size = imaging.image_size(path)
        if size is None:
            continue
        natural[role] = (src, size[0], size[1])
    scaled = imaging.scale_to_box(
        {role: (width, height) for role, (_src, width, height) in natural.items()},
        el.w,
        el.h,
    )
    result: dict[str, tuple[str, int, int]] = {}
    for role, (src, _width, _height) in natural.items():
        width, height = scaled[role]
        result[role] = (src, width, height)
    return result


def _draw_hands(
    painter: QPainter,
    project: Project,
    el: Element,
    moment: _dt.datetime,
    preview: bool,
) -> None:
    sizes = hand_sizes(project, el)
    if not sizes:
        if not preview:
            _draw_placeholder(painter, QRectF(el.x, el.y, el.w, el.h), "Wskazówki")
        return
    center = QRectF(el.x, el.y, el.w, el.h).center()
    angles = hand_angles(moment)
    for role in ("hour", "minute", "second", "cap"):
        if role not in sizes:
            continue
        src, width, height = sizes[role]
        pix = pixmap_for(project, src, width, height)
        if pix is None:
            continue
        painter.save()
        if role != "cap":
            painter.translate(center)
            painter.rotate(angles.get(role, 0.0))
            painter.drawPixmap(round(-width / 2), round(-height / 2), pix)
        else:
            painter.drawPixmap(
                round(center.x() - width / 2),
                round(center.y() - height / 2),
                pix,
            )
        painter.restore()


def _draw_shortcut(painter: QPainter, project: Project, el: Element, preview: bool) -> None:
    p = el.props
    rect = QRectF(el.x, el.y, el.w, el.h)
    icon = str(p.get("icon", ""))
    if icon:
        content_x, content_y, content_w, content_h = el.render_rect()
        pix = pixmap_for(project, icon, content_w, content_h)
        if pix is not None:
            painter.drawPixmap(content_x, content_y, pix)
    if preview:
        return
    painter.save()
    painter.setPen(QPen(QColor(90, 200, 255, 190), 1, Qt.DashLine))
    painter.setBrush(QColor(70, 170, 255, 26))
    painter.drawRoundedRect(rect, 6, 6)
    label = str(p.get("label", "") or "")
    if not label:
        if p.get("kind") == "app":
            label = C.SHORTCUT_BY_KEY.get(str(p.get("app", "")), {}).get("label", "Skrót")
        else:
            label = C.DATA_SOURCES.get(str(p.get("data", "")), {}).get("label", "Skrót")
    font = QFont()
    font.setPixelSize(max(9, int(min(rect.width(), rect.height()) / 5)))
    painter.setFont(font)
    painter.setPen(QColor(150, 220, 255, 220))
    painter.drawText(rect, int(Qt.AlignCenter | Qt.TextWordWrap), f"SKRÓT\n{label}")
    painter.restore()


def make_image(
    project: Project,
    size: int,
    *,
    live: bool = False,
    preview: bool = False,
    now: _dt.datetime | None = None,
    transparent: bool = False,
    samples: dict[str, tuple[str, float]] | None = None,
    weather_index: int | None = None,
) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent if transparent else QColor(project.background_color))
    painter = QPainter(image)
    render_project(
        painter,
        project,
        QRectF(0, 0, size, size),
        live=live,
        preview=preview,
        now=now,
        clip_circle=transparent,
        samples=samples,
        weather_index=weather_index,
    )
    painter.end()
    return image


def save_gif(
    project: Project,
    path: Path,
    *,
    size: int = 466,
    frames: int = 24,
    frame_ms: int = 90,
    seed: int | None = None,
) -> bool:
    """Zapisuje animowany GIF z losowymi danymi przykładowymi."""
    from PIL import Image

    rng = random.Random(seed)
    path = Path(path)
    moment = random_moment(rng)
    pil_frames: list[Image.Image] = []
    samples: dict[str, tuple[str, float]] | None = None
    weather_index: int | None = None
    for index in range(max(1, int(frames))):
        if index % 4 == 0:
            samples = random_samples(rng)
            weather_index = rng.randrange(len(C.WEATHER_FILES))
        frame_moment = moment + _dt.timedelta(minutes=index * 7, seconds=rng.randrange(60))
        image = make_image(
            project,
            size,
            preview=True,
            now=frame_moment,
            samples=samples,
            weather_index=weather_index,
        )
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        if not image.save(buffer, "PNG"):
            buffer.close()
            return False
        frame = Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGB")
        buffer.close()
        pil_frames.append(frame.convert("P", palette=Image.ADAPTIVE, colors=128))
    if not pil_frames:
        return False
    for frame in pil_frames:
        frame.info["duration"] = frame_ms
    path.parent.mkdir(parents=True, exist_ok=True)
    pil_frames[0].save(
        str(path),
        "GIF",
        save_all=True,
        append_images=pil_frames[1:],
        duration=frame_ms,
        loop=0,
        disposal=2,
        optimize=False,
    )
    return True


def make_preview_png(project: Project, path: Path, size: int | None = None) -> None:
    size = size or C.DEVICE["preview_size"]
    image = make_image(project, size, preview=True, now=SAMPLE_TIME)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(path), "PNG")
