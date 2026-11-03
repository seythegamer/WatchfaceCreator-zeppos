"""Generuje wbudowane ikony pogody i statusow (PNG) dla edytora.

Wskazówki w ``assets/hands`` są ręcznie dopracowane i trafiają do każdego
nowego projektu, więc domyślnie generator ich **nie nadpisuje**. Aby odtworzyć
wzorcowy zestaw od zera, uruchom skrypt z flagą ``--force``.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
WEATHER_DIR = ROOT / "assets" / "weather"
STATUS_DIR = ROOT / "assets" / "status"
HANDS_DIR = ROOT / "assets" / "hands"

S = 4
SIZE = 96 * S

SUN = (255, 201, 60, 255)
SUN_DIM = (255, 214, 130, 255)
CLOUD = (236, 242, 255, 255)
CLOUD_DARK = (166, 180, 208, 255)
CLOUD_STORM = (120, 134, 163, 255)
RAIN = (86, 168, 255, 255)
SNOW = (255, 255, 255, 255)
BOLT = (255, 214, 64, 255)
FOG = (198, 210, 232, 255)
SAND = (219, 178, 110, 255)
MOON = (226, 235, 255, 255)


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def ellipse(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill) -> None:
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def sun(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color=SUN, rays: int = 8) -> None:
    for i in range(rays):
        a = math.tau * i / rays
        x1 = cx + math.cos(a) * r * 1.45
        y1 = cy + math.sin(a) * r * 1.45
        x2 = cx + math.cos(a) * r * 1.95
        y2 = cy + math.sin(a) * r * 1.95
        d.line([x1, y1, x2, y2], fill=color, width=int(S * 3.2))
    ellipse(d, cx, cy, r, color)


def moon(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float) -> None:
    ellipse(d, cx, cy, r, MOON)
    ellipse(d, cx + r * 0.55, cy - r * 0.35, r * 0.88, (0, 0, 0, 0))
    for dx, dy, s in ((-0.9, -0.5, 0.09), (-0.2, -1.1, 0.07), (-1.1, 0.5, 0.06)):
        ellipse(d, cx + r * dx, cy + r * dy, r * s, MOON)


def cloud(d: ImageDraw.ImageDraw, cx: float, cy: float, w: float, color=CLOUD) -> None:
    r = w * 0.26
    ellipse(d, cx - w * 0.28, cy + r * 0.25, r, color)
    ellipse(d, cx + w * 0.26, cy + r * 0.30, r * 0.95, color)
    ellipse(d, cx - w * 0.02, cy - r * 0.28, r * 1.18, color)
    d.rounded_rectangle(
        [cx - w * 0.52, cy + r * 0.05, cx + w * 0.50, cy + r * 0.75],
        radius=int(r * 0.55),
        fill=color,
    )


def drop(d: ImageDraw.ImageDraw, x: float, y: float, h: float, color=RAIN) -> None:
    w = h * 0.46
    d.polygon([(x, y), (x - w, y + h * 0.72), (x + w, y + h * 0.72)], fill=color)
    ellipse(d, x, y + h * 0.72, w, color)


def snow(d: ImageDraw.ImageDraw, x: float, y: float, r: float, color=SNOW) -> None:
    for i in range(3):
        a = math.tau * i / 3
        dx, dy = math.cos(a) * r, math.sin(a) * r
        d.line([x - dx, y - dy, x + dx, y + dy], fill=color, width=int(S * 2.4))
    ellipse(d, x, y, r * 0.32, color)


def bolt(d: ImageDraw.ImageDraw, x: float, y: float, h: float) -> None:
    w = h * 0.52
    d.polygon(
        [
            (x, y),
            (x - w * 0.75, y + h * 0.56),
            (x - w * 0.12, y + h * 0.56),
            (x - w * 0.5, y + h),
            (x + w * 0.8, y + h * 0.36),
            (x + w * 0.1, y + h * 0.36),
            (x + w * 0.55, y),
        ],
        fill=BOLT,
    )


def wind(d: ImageDraw.ImageDraw, y: float, w: float, color=FOG) -> None:
    d.line([SIZE / 2 - w / 2, y, SIZE / 2 + w / 2, y], fill=color, width=int(S * 3.4))


def make(idx: int) -> Image.Image:
    img, d = canvas()
    c = SIZE / 2
    if idx == 3:
        sun(d, c, c, SIZE * 0.17)
    elif idx == 28:
        moon(d, c, c, SIZE * 0.22)
    elif idx in (0, 26):
        if idx == 26:
            moon(d, c + SIZE * 0.20, c - SIZE * 0.22, SIZE * 0.13)
        cloud(d, c, c + SIZE * 0.06, SIZE * 0.52)
    elif idx in (1, 27):
        cloud(d, c, c - SIZE * 0.04, SIZE * 0.5)
        for i, x in enumerate((-0.16, 0.02, 0.20)):
            drop(d, c + x * SIZE, c + SIZE * 0.20 + (i % 2) * SIZE * 0.03, SIZE * 0.14)
    elif idx == 2:
        cloud(d, c, c - SIZE * 0.04, SIZE * 0.5)
        for i, x in enumerate((-0.14, 0.06)):
            snow(d, c + x * SIZE, c + SIZE * 0.25, SIZE * 0.055)
    elif idx == 4:
        cloud(d, c - SIZE * 0.06, c + SIZE * 0.10, SIZE * 0.46, CLOUD_DARK)
        cloud(d, c + SIZE * 0.10, c - SIZE * 0.06, SIZE * 0.40)
    elif idx in (5, 7, 10, 24):
        drops = {5: 3, 7: 4, 10: 5, 24: 6}[idx]
        cloud(d, c, c - SIZE * 0.08, SIZE * 0.5, CLOUD_STORM if idx >= 10 else CLOUD)
        for i in range(drops):
            x = c + (i - (drops - 1) / 2) * SIZE * 0.13
            drop(d, x, c + SIZE * 0.18, SIZE * (0.15 if idx < 10 else 0.19))
    elif idx in (6, 8, 9, 16):
        flakes = {6: 2, 8: 3, 9: 5, 16: 6}[idx]
        cloud(d, c, c - SIZE * 0.08, SIZE * 0.5, CLOUD_STORM if idx == 16 else CLOUD)
        for i in range(flakes):
            x = c + (i - (flakes - 1) / 2) * SIZE * 0.13
            y = c + SIZE * 0.22 + (i % 2) * SIZE * 0.05
            snow(d, x, y, SIZE * 0.055)
    elif idx == 11 or idx == 22:
        wind(d, c - SIZE * 0.10, SIZE * 0.7, SAND)
        wind(d, c + SIZE * 0.02, SIZE * 0.5, SAND)
        wind(d, c + SIZE * 0.14, SIZE * 0.6, SAND)
    elif idx == 12:
        cloud(d, c, c - SIZE * 0.08, SIZE * 0.5)
        drop(d, c - SIZE * 0.12, c + SIZE * 0.20, SIZE * 0.15)
        snow(d, c + SIZE * 0.12, c + SIZE * 0.28, SIZE * 0.06)
    elif idx == 13:
        for i, w in enumerate((0.68, 0.5, 0.62)):
            wind(d, c + (i - 1) * SIZE * 0.17, SIZE * w, FOG)
    elif idx == 14:
        sun(d, c, c - SIZE * 0.10, SIZE * 0.13, SUN_DIM, 6)
        for i, w in enumerate((0.7, 0.55)):
            wind(d, c + SIZE * (0.05 + i * 0.15), SIZE * w, FOG)
    elif idx == 15:
        cloud(d, c, c - SIZE * 0.10, SIZE * 0.5, CLOUD_STORM)
        bolt(d, c + SIZE * 0.02, c + SIZE * 0.14, SIZE * 0.30)
        drop(d, c - SIZE * 0.24, c + SIZE * 0.20, SIZE * 0.13)
        drop(d, c + SIZE * 0.26, c + SIZE * 0.20, SIZE * 0.13)
    elif idx == 19:
        cloud(d, c, c - SIZE * 0.10, SIZE * 0.5, CLOUD_DARK)
        for x in (-0.22, 0.0, 0.22):
            drop(d, c + x * SIZE, c + SIZE * 0.18, SIZE * 0.14)
        for x in (-0.11, 0.11):
            ellipse(d, c + x * SIZE, c + SIZE * 0.36, SIZE * 0.035, SNOW)
    elif idx == 20:
        cloud(d, c, c - SIZE * 0.10, SIZE * 0.5, CLOUD_STORM)
        bolt(d, c - SIZE * 0.02, c + SIZE * 0.12, SIZE * 0.28)
        for x in (-0.24, 0.24):
            ellipse(d, c + x * SIZE, c + SIZE * 0.34, SIZE * 0.035, SNOW)
    elif idx in (18, 21):
        cloud(d, c, c - SIZE * 0.12, SIZE * 0.54, CLOUD_STORM)
        bolt(d, c + SIZE * 0.05, c + SIZE * 0.10, SIZE * 0.26)
        for i in range(5):
            x = c + (i - 2) * SIZE * 0.12
            drop(d, x, c + SIZE * 0.22, SIZE * 0.17)
    elif idx == 17:
        for i in range(5):
            ellipse(d, c + (i - 2) * SIZE * 0.11, c + (i % 2 - 0.5) * SIZE * 0.14, SIZE * 0.035, SAND)
        wind(d, c + SIZE * 0.18, SIZE * 0.6, SAND)
    elif idx == 23:
        cloud(d, c, c - SIZE * 0.08, SIZE * 0.56, SAND)
        for i in range(3):
            wind(d, c + (i - 1) * SIZE * 0.17, SIZE * (0.55 - i * 0.08), SAND)
    else:
        cloud(d, c, c + SIZE * 0.02, SIZE * 0.5, CLOUD_DARK)
    return img


WEATHER_NAMES = [
    "cloudy",
    "shower",
    "snow_shower",
    "sunny",
    "overcast",
    "light_rain",
    "light_snow",
    "moderate_rain",
    "moderate_snow",
    "heavy_snow",
    "heavy_rain",
    "sandstorm",
    "sleet",
    "fog",
    "haze",
    "thundershower",
    "snowstorm",
    "dust",
    "extraordinary_rainstorm",
    "rain_with_hail",
    "thundershowers_with_hail",
    "heavy_rainstorm",
    "sand_blowing",
    "strong_sandstorm",
    "rainstorm",
    "unknown",
    "cloudy_at_night",
    "shower_at_night",
    "clear_night",
]


def make_status() -> None:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)

    img, d = canvas()
    w = SIZE * 0.055
    d.line(
        [
            (SIZE * 0.34, SIZE * 0.28),
            (SIZE * 0.62, SIZE * 0.5),
            (SIZE * 0.34, SIZE * 0.72),
        ],
        fill=RAIN,
        width=int(w),
        joint="curve",
    )
    d.line(
        [
            (SIZE * 0.66, SIZE * 0.28),
            (SIZE * 0.38, SIZE * 0.5),
            (SIZE * 0.66, SIZE * 0.72),
        ],
        fill=RAIN,
        width=int(w),
        joint="curve",
    )
    d.line([SIZE * 0.5, SIZE * 0.2, SIZE * 0.5, SIZE * 0.8], fill=RAIN, width=int(w * 1.1))
    img.resize((96, 96), Image.LANCZOS).save(STATUS_DIR / "bluetooth.png")

    img, d = canvas()
    ellipse(d, SIZE / 2, SIZE / 2, SIZE * 0.22, (240, 90, 100, 255))
    d.rectangle([SIZE * 0.28, SIZE * 0.46, SIZE * 0.72, SIZE * 0.58], fill=(255, 255, 255, 255))
    img.resize((96, 96), Image.LANCZOS).save(STATUS_DIR / "dnd.png")

    img, d = canvas()
    d.rounded_rectangle(
        [SIZE * 0.34, SIZE * 0.42, SIZE * 0.66, SIZE * 0.76],
        radius=int(SIZE * 0.06),
        fill=(230, 236, 250, 255),
    )
    d.arc([SIZE * 0.36, SIZE * 0.22, SIZE * 0.64, SIZE * 0.52], 180, 360, fill=(230, 236, 250, 255), width=int(SIZE * 0.05))
    img.resize((96, 96), Image.LANCZOS).save(STATUS_DIR / "lock.png")

    img, d = canvas()
    d.ellipse([SIZE * 0.28, SIZE * 0.32, SIZE * 0.54, SIZE * 0.72], fill=(255, 201, 60, 255))
    d.ellipse([SIZE * 0.44, SIZE * 0.44, SIZE * 0.72, SIZE * 0.84], fill=(255, 201, 60, 255))
    d.rectangle([SIZE * 0.46, SIZE * 0.64, SIZE * 0.62, SIZE * 0.86], fill=(255, 201, 60, 255))
    d.rounded_rectangle([SIZE * 0.62, SIZE * 0.56, SIZE * 0.86, SIZE * 0.72], radius=int(SIZE * 0.03), fill=(255, 255, 255, 255))
    img.resize((96, 96), Image.LANCZOS).save(STATUS_DIR / "alarm.png")


def make_hands(force: bool = False) -> bool:
    """Buduje wbudowany zestaw wskazówek (400x400, oś w środku, grot do góry).

    Zwraca ``True``, jeśli pliki zostały zapisane. Bez ``force`` istniejący
    zestaw (np. ręcznie dopracowany) zostaje nietknięty.
    """
    HANDS_DIR.mkdir(parents=True, exist_ok=True)
    names = ("hour.png", "minute.png", "second.png", "cap.png")
    if not force and all((HANDS_DIR / name).exists() for name in names):
        return False
    size = 400
    scale = 4
    center = size * scale / 2

    def new_hand():
        image = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
        return image, ImageDraw.Draw(image)

    def shaft(draw, length: float, width: float, color, tail: float = 0.0) -> None:
        top = center - length * scale
        bottom = center + tail * scale
        half = width * scale / 2
        draw.rounded_rectangle(
            [center - half, top, center + half, bottom],
            radius=half,
            fill=color,
        )

    hand, draw = new_hand()
    shaft(draw, 122, 17, (238, 244, 255, 255), tail=14)
    hand.resize((size, size), Image.LANCZOS).save(HANDS_DIR / "hour.png")

    hand, draw = new_hand()
    shaft(draw, 170, 11, (238, 244, 255, 255), tail=18)
    hand.resize((size, size), Image.LANCZOS).save(HANDS_DIR / "minute.png")

    hand, draw = new_hand()
    shaft(draw, 192, 5, (255, 82, 82, 255), tail=36)
    hand.resize((size, size), Image.LANCZOS).save(HANDS_DIR / "second.png")

    hand, draw = new_hand()
    draw.ellipse(
        [center - 24 * scale, center - 24 * scale, center + 24 * scale, center + 24 * scale],
        fill=(24, 32, 46, 255),
    )
    draw.ellipse(
        [center - 16 * scale, center - 16 * scale, center + 16 * scale, center + 16 * scale],
        fill=(226, 236, 250, 255),
    )
    draw.ellipse(
        [center - 6 * scale, center - 6 * scale, center + 6 * scale, center + 6 * scale],
        fill=(120, 140, 170, 255),
    )
    hand.resize((size, size), Image.LANCZOS).save(HANDS_DIR / "cap.png")
    return True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="nadpisz także ręcznie dopracowane wskazówki w assets/hands",
    )
    args = parser.parse_args(argv)
    WEATHER_DIR.mkdir(parents=True, exist_ok=True)
    for idx, name in enumerate(WEATHER_NAMES):
        img = make(idx)
        img = img.filter(ImageFilter.SMOOTH)
        img.resize((96, 96), Image.LANCZOS).save(WEATHER_DIR / f"{idx:02d}_{name}.png")
    make_status()
    written = make_hands(force=args.force)
    print(f"weather: {len(WEATHER_NAMES)} icon(s) -> {WEATHER_DIR}")
    print(f"status -> {STATUS_DIR}")
    if written:
        print(f"hands -> {HANDS_DIR}")
    else:
        print(f"hands -> {HANDS_DIR} (zachowano istniejące; --force nadpisze)")


if __name__ == "__main__":
    main()
