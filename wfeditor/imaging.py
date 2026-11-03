from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage


def load_image(path: Path) -> QImage | None:
    """Wczytuje obraz jako ARGB32 (bez premultiplied alpha)."""
    image = QImage(str(path))
    if image.isNull():
        return None
    return image.convertToFormat(QImage.Format_ARGB32)


def image_size(path: Path) -> tuple[int, int] | None:
    """Zwraca szerokość i wysokość pliku graficznego bez wczytywania pikseli."""
    from PySide6.QtGui import QImageReader

    reader = QImageReader(str(path))
    size = reader.size()
    if size.isValid() and size.width() > 0 and size.height() > 0:
        return (size.width(), size.height())
    image = load_image(path)
    if image is None:
        return None
    return (image.width(), image.height())


def _mipmap_downscale(source: QImage, width: int, height: int) -> QImage:
    """Stopniowo zmniejsza obraz, aby uniknąć aliasingu i zachować detal."""
    current = source
    while current.width() >= width * 2 and current.height() >= height * 2:
        next_width = max(width, current.width() // 2)
        next_height = max(height, current.height() // 2)
        current = current.scaled(
            next_width,
            next_height,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
    return current.scaled(
        width,
        height,
        Qt.IgnoreAspectRatio,
        Qt.SmoothTransformation,
    )


def _sharp_upscale(source: QImage, width: int, height: int) -> QImage:
    """Skaluje w górę metodą sharp-bilinear.

    Najpierw powiększa piksele całkowitym mnożnikiem (bez rozmycia), a potem
    dopasowuje do dokładnego rozmiaru z wygładzaniem. Krawędzie pozostają
    ostre, ale nie ma schodków charakterystycznych dla zwykłego nearest.
    """
    factor = max(2, int(math.ceil(max(width / source.width(), height / source.height()))))
    if factor <= 32 and source.width() * factor <= 4096 and source.height() * factor <= 4096:
        enlarged = source.scaled(
            source.width() * factor,
            source.height() * factor,
            Qt.IgnoreAspectRatio,
            Qt.FastTransformation,
        )
        return enlarged.scaled(
            width,
            height,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
    return source.scaled(
        width,
        height,
        Qt.IgnoreAspectRatio,
        Qt.FastTransformation,
    )


def resize_image(image: QImage, width: int, height: int) -> QImage:
    """Skaluje obraz w przestrzeni premultiplied alpha.

    Dzięki temu przezroczyste piksele nie wnoszą swojego (często białego)
    koloru RGB do krawędzi, więc na zegarku nie pojawia się jasna obwódka.
    Zmniejszanie używa mipmap (mniej aliasingu), a powiększanie zachowuje
    ostrość przez sharp-bilinear. Ten sam kod obsługuje edytor i eksport,
    więc oba obrazy są identyczne.
    """
    width = max(1, int(width))
    height = max(1, int(height))
    if image.width() == width and image.height() == height:
        return image.convertToFormat(QImage.Format_ARGB32)
    source = image.convertToFormat(QImage.Format_ARGB32_Premultiplied)
    if width >= source.width() and height >= source.height():
        scaled = _sharp_upscale(source, width, height)
    else:
        scaled = _mipmap_downscale(source, width, height)
    return scaled.convertToFormat(QImage.Format_ARGB32)


def load_resized(path: Path, width: int = 0, height: int = 0) -> QImage | None:
    image = load_image(path)
    if image is None:
        return None
    if width > 0 and height > 0:
        image = resize_image(image, width, height)
    return image


def alpha_bbox(image: QImage) -> tuple[int, int, int, int] | None:
    """Zwraca prostokąt nieprzezroczystych pikseli jako (x, y, szerokość, wysokość).

    ``None`` oznacza obraz całkowicie przezroczysty. Prostokąt jest liczony
    na kanale alfa, więc nie zależą od niego kolory ukryte w przezroczystych
    pikselach (częsty biały fringe po skalowaniu).
    """
    if image.isNull() or image.width() <= 0 or image.height() <= 0:
        return None
    alpha = image.convertToFormat(QImage.Format_Alpha8)
    width = alpha.width()
    height = alpha.height()
    stride = alpha.bytesPerLine()
    bits = alpha.constBits()
    left = width
    right = -1
    top = -1
    bottom = -1
    for y in range(height):
        row = bytes(bits[y * stride : y * stride + width])
        first = next((x for x, value in enumerate(row) if value), None)
        if first is None:
            continue
        if top < 0:
            top = y
        bottom = y
        left = min(left, first)
        last = next(x for x in range(width - 1, first - 1, -1) if row[x])
        right = max(right, last)
    if right < 0 or top < 0:
        return None
    return (left, top, right - left + 1, bottom - top + 1)


def pad_rect(
    rect: tuple[int, int, int, int], width: int, height: int, padding: int = 2
) -> tuple[int, int, int, int]:
    """Powiększa prostokąt o przezroczysty margines (bez wychodzenia z obrazu).

    Margines jest potrzebny, aby obrót i próbkowanie krawędzi po przycięciu
    wyglądały identycznie jak na pełnym płótnie.
    """
    x, y, w, h = rect
    x0 = max(0, x - max(0, padding))
    y0 = max(0, y - max(0, padding))
    x1 = min(width, x + w + max(0, padding))
    y1 = min(height, y + h + max(0, padding))
    return (x0, y0, max(1, x1 - x0), max(1, y1 - y0))


def scale_to_box(
    sizes: dict[str, tuple[int, int]], box_width: int, box_height: int
) -> dict[str, tuple[int, int]]:
    """Skaluje cały zestaw obrazów jedną skalą, zachowując proporcje wewnątrz zestawu.

    Największe płótno zestawu jest dopasowane do krótszego boku ramki.
    Wszystkie obrazy (wskazówki i nakładka) dostają tę samą skalę, więc
    wskazówka minutowa pozostaje dłuższa od godzinowej.
    """
    if not sizes:
        return {}
    canvas = max(max(width, height) for width, height in sizes.values())
    if canvas <= 0:
        return {role: (max(1, width), max(1, height)) for role, (width, height) in sizes.items()}
    scale = min(max(1, int(box_width)), max(1, int(box_height))) / canvas
    return {
        role: (max(1, round(width * scale)), max(1, round(height * scale)))
        for role, (width, height) in sizes.items()
    }


def write_png(image: QImage, path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    return bool(image.save(str(path), "PNG"))
