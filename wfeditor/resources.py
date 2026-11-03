from __future__ import annotations

import hashlib
from dataclasses import dataclass

from . import constants as C
from . import imaging
from .model import Element, Project, hand_sources


@dataclass(frozen=True)
class HandAsset:
    """Obraz wskazówki po przycięciu do widocznej treści.

    ``width``/``height`` to rozmiar pliku, ``offset_x``/``offset_y`` to
    położenie przyciętego obrazu na pełnym płótnie zestawu, a
    ``canvas_width``/``canvas_height`` to rozmiar tego płótna. Dzięki temu
    wskazówka jest rysowana i obracana dokładnie w tym samym miejscu, co
    przed przycięciem, ale zajmuje znacznie mniej pamięci na zegarku.
    """

    name: str
    width: int
    height: int
    offset_x: int
    offset_y: int
    canvas_width: int
    canvas_height: int


class Resources:
    def __init__(self, project: Project) -> None:
        self.project = project
        self._plan: dict[str, tuple[str, int, int]] = {}
        self._by_key: dict[tuple[str, int, int], str] = {}
        self._element_names: dict[str, str] = {}
        self._weather_dirs: dict[tuple[str, int], tuple[str, int]] = {}
        self._bar_frames: dict[str, tuple[Element, list[str], list[float]]] = {}
        self._text_images: dict[str, tuple[str, Element]] = {}
        self._crops: dict[str, tuple[int, int, int, int]] = {}
        self._hand_crops: dict[tuple[str, int, int], tuple[int, int, int, int] | None] = {}

    @staticmethod
    def _hash(src: str, w: int, h: int) -> str:
        raw = f"{src}|{int(w)}x{int(h)}".encode()
        return hashlib.md5(raw).hexdigest()[:8]

    def _target(self, src: str, w: int, h: int, prefix: str, ext: str = ".png") -> str:
        key = (src, int(w), int(h))
        if key in self._by_key:
            return self._by_key[key]
        name = f"{prefix}_{self._hash(src, w, h)}{ext}"
        self._plan[name] = (src, int(w), int(h))
        self._by_key[key] = name
        return name

    def image(self, el: Element) -> str:
        src = str(el.props.get("src", "") or "")
        if not src or self.project.asset_file(src) is None:
            return ""
        width, height = el.render_size()
        return self._target(src, width, height, "img")

    def background(self) -> str:
        src = self.project.background_image
        if not src or self.project.asset_file(src) is None:
            return ""
        return self._target(src, C.DEVICE["width"], C.DEVICE["height"], "bg")

    def status(self, el: Element) -> str:
        key = str(el.props.get("status", "bluetooth"))
        src = C.STATUS_FILES.get(key, C.STATUS_FILES["bluetooth"])
        size = int(el.props.get("size", max(el.w, el.h)) or max(el.w, el.h))
        return self._target(src, size, size, "st")

    def shortcut_icon(self, el: Element) -> str:
        src = str(el.props.get("icon", "") or "")
        if not src or self.project.asset_file(src) is None:
            return ""
        width, height = el.render_size()
        return self._target(src, width, height, "ico")

    def _hand_crop(
        self, src: str, width: int, height: int
    ) -> tuple[int, int, int, int] | None:
        """Prostokąt widocznej treści wskazówki na płótnie ``width`` × ``height``."""
        key = (src, int(width), int(height))
        if key in self._hand_crops:
            return self._hand_crops[key]
        path = self.project.asset_file(src)
        image = imaging.load_resized(path, width, height) if path is not None else None
        bbox = imaging.alpha_bbox(image) if image is not None else None
        if bbox is None:
            crop = None
        else:
            # 8 px przezroczystego marginesu zachowuje identyczne próbkowanie
            # krawędzi przy obrocie, a koszt pamięci pozostaje znikomy.
            crop = imaging.pad_rect(bbox, image.width(), image.height(), 8)
        self._hand_crops[key] = crop
        return crop

    def hands(self, el: Element) -> dict[str, HandAsset]:
        """Plan zasobów wskazówek: rola -> obraz przycięty do widocznej treści."""
        natural: dict[str, tuple[str, int, int]] = {}
        for role, src in hand_sources(el).items():
            path = self.project.asset_file(src)
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
        result: dict[str, HandAsset] = {}
        for role, (src, _width, _height) in natural.items():
            width, height = scaled[role]
            crop = self._hand_crop(src, width, height)
            if crop is None:
                # Całkowicie przezroczysta wskazówka nie musi zajmować
                # pamięci na zegarku, a jej wygląd się nie zmienia.
                continue
            target = self._target(src, width, height, "hand")
            self._crops[target] = crop
            offset_x, offset_y, crop_w, crop_h = crop
            result[role] = HandAsset(
                name=target,
                width=crop_w,
                height=crop_h,
                offset_x=offset_x,
                offset_y=offset_y,
                canvas_width=width,
                canvas_height=height,
            )
        return result

    def crop_for(self, target: str) -> tuple[int, int, int, int] | None:
        """Prostokąt przycięcia dla zaplanowanego zasobu (jeśli istnieje)."""
        return self._crops.get(target)

    def weather(self, el: Element) -> tuple[str, list[str]]:
        size = int(el.props.get("size", min(el.w, el.h)) or min(el.w, el.h))
        set_name = str(el.props.get("set", "") or "")
        sources: list[str] = []
        if set_name:
            sources = [
                f"weather_sets/{set_name}/{name}" for name in C.WEATHER_FILES
            ]
            if not all(self.project.asset_file(src) is not None for src in sources):
                sources = []
        cache_key = (set_name, size)
        if cache_key in self._weather_dirs:
            prefix, _ = self._weather_dirs[cache_key]
        else:
            if sources:
                prefix = f"weather_{self._hash(f'set:{set_name}', size, size)}"
            else:
                prefix = f"weather_{self._hash('weather', size, size)}"
                sources = [f"weather/{name}" for name in C.WEATHER_FILES]
            # Ikony trafiają bezpośrednio do katalogu assets/ (bez podkatalogów).
            # Tak robi oficjalny Watchface Maker i dzięki temu ścieżki są bezpieczne
            # dla wszystkich narzędzi pakujących (m.in. amazfitwatchfaces).
            for src, name in zip(sources, C.WEATHER_FILES):
                self._plan[f"{prefix}_{name}"] = (src, size, size)
            self._weather_dirs[cache_key] = (prefix, size)
        return prefix, [f"{prefix}_{name}" for name in C.WEATHER_FILES]

    def bar_image(self, el: Element, key: str) -> str:
        """Plan obrazu 0% lub 100% paska postępu (skalowanego do ramki)."""
        src = str(el.props.get(key, "") or "")
        if not src or self.project.asset_file(src) is None:
            return ""
        return self._target(src, max(1, int(el.w)), max(1, int(el.h)), "bar")

    def bar_frames(self, el: Element) -> list[str]:
        """Plan klatek łukowego paska z obrazami (0%..100%)."""
        count = max(2, int(C.PROGRESS_BAR_FRAMES))
        signature = "|".join(
            str(value)
            for value in (
                el.id,
                el.w,
                el.h,
                el.props.get("direction", "h"),
                el.props.get("curve", 100),
                el.props.get("line_width", 0),
                el.props.get("bow", ""),
                el.props.get("corner_flag", 0),
                el.props.get("bg_color", ""),
                el.props.get("show_bg", True),
                el.props.get("src0", ""),
                el.props.get("src100", ""),
                el.props.get("reverse", False),
            )
        )
        prefix = f"barf_{self._hash(signature, el.w, el.h)}"
        cached = self._bar_frames.get(prefix)
        if cached is not None:
            return cached[1]
        names = [f"{prefix}_{index:03d}.png" for index in range(count)]
        ratios = [index / (count - 1) for index in range(count)]
        self._bar_frames[prefix] = (el, names, ratios)
        return names

    def generated_frames(self) -> list[tuple[str, Element, float]]:
        result: list[tuple[str, Element, float]] = []
        for el, names, ratios in self._bar_frames.values():
            for name, ratio in zip(names, ratios):
                result.append((name, el, ratio))
        return result

    def text_image(self, el: Element) -> str:
        """Nazwa pliku z rasteryzowanym stałym tekstem (obrót na zegarku)."""
        if el.type != "text" or not int(el.rotation or 0):
            return ""
        if not str(el.props.get("text", "")).strip():
            return ""
        signature = "|".join(
            str(value)
            for value in (
                el.id,
                el.w,
                el.h,
                el.props.get("text", ""),
                el.props.get("font", ""),
                el.props.get("size", 32),
                el.props.get("color", "#FFFFFF"),
                el.props.get("align", "center"),
                el.props.get("valign", "center"),
                el.props.get("spacing", 0),
            )
        )
        name = f"txt_{self._hash(signature, el.w, el.h)}.png"
        self._text_images[name] = (name, el)
        return name

    def generated_text_images(self) -> list[tuple[str, Element]]:
        return list(self._text_images.values())

    def fonts(self) -> list[str]:
        found: list[str] = []
        for el in self.project.elements:
            font = str(el.props.get("font", "") or "")
            if font and font not in found and self.project.asset_file(font) is not None:
                found.append(font)
        return found

    def entries(self) -> list[tuple[str, str, int, int]]:
        return [(target, *value) for target, value in self._plan.items()]
