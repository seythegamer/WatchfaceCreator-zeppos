"""Format wyświetlania godziny wpisywany przez użytkownika.

Wzorzec składa się z tokenów i dowolnych separatorów::

    HH  godzina z zerem wiodącym        H  godzina bez zera
    MM  minuty z zerem wiodącym         M  minuty bez zera
    SS  sekundy z zerem wiodącym        S  sekundy bez zera
    A   AM/PM

Wszystko inne jest kopiowane dosłownie, więc ``HH:MM`` daje ``10:09``,
``HH`` tylko godzinę, a ``MM`` tylko minuty. Wielkość liter tokenów nie ma
znaczenia (``hh:mm`` działa tak samo jak ``HH:MM``). Zapis ``AM``/``PM`` jest
traktowany jak ``A``; samo ``A`` musi być wielkie, żeby litera „a” w zwykłym
tekście nie zamieniała się w AM/PM.
"""
from __future__ import annotations

from typing import Any

DEFAULT_DISPLAY = "HH:MM"

# Klucze ze starszych wersji edytora, zastąpione przez ``display``.
LEGACY_KEYS = ("seconds", "ampm", "pad")

_HMS_TOKENS = ("HH", "H", "MM", "M", "SS", "S")
_TIME_TOKENS = frozenset(_HMS_TOKENS)


def migrate_props(props: dict[str, Any]) -> None:
    """Uzupełnia ``display`` na podstawie starych pól i usuwa je.

    Wywoływane przy wczytywaniu projektu, także dla plików zapisanych przed
    wprowadzeniem wzorca. Funkcja jest idempotentna.
    """
    pattern = str(props.get("display", "") or "").strip()
    if not pattern:
        pattern = "HH:MM:SS" if bool(props.get("seconds")) else "HH:MM"
        if not bool(props.get("pad", True)):
            pattern = pattern.replace("HH", "H")
        if bool(props.get("ampm")):
            pattern = f"{pattern} A"
        props["display"] = pattern
    for key in LEGACY_KEYS:
        props.pop(key, None)


def split_tokens(pattern: str) -> list[tuple[str, str]]:
    """Dzieli wzorzec na pary ``(token, tekst)``.

    ``token`` jest pusty dla literalnego separatora. Najdłuższe tokeny mają
    pierwszeństwo, więc ``HH`` nie zostanie odczytane jako dwa razy ``H``.
    """
    result: list[tuple[str, str]] = []
    literal: list[str] = []
    index = 0
    while index < len(pattern):
        token = ""
        length = 0
        pair = pattern[index : index + 2].upper()
        if pair in ("AM", "PM"):
            token = "A"
            length = 2
        else:
            for candidate in _HMS_TOKENS:
                chunk = pattern[index : index + len(candidate)]
                if len(chunk) == len(candidate) and chunk.upper() == candidate:
                    token = candidate
                    length = len(candidate)
                    break
            if not token and pattern[index] == "A":
                token = "A"
                length = 1
        if token:
            if literal:
                result.append(("", "".join(literal)))
                literal = []
            result.append((token, ""))
            index += length
        else:
            literal.append(pattern[index])
            index += 1
    if literal:
        result.append(("", "".join(literal)))
    return result


def uses_time_token(pattern: str) -> bool:
    """Czy wzorzec zawiera przynajmniej jeden token godziny/minut/sekund."""
    return any(token in _TIME_TOKENS for token, _text in split_tokens(pattern))


def display_pattern(props: dict[str, Any]) -> str:
    """Zwraca poprawny wzorzec; pusty lub bez czasu zastępuje ``HH:MM``."""
    pattern = str(props.get("display", "") or "").strip()
    if not pattern or not uses_time_token(pattern):
        return DEFAULT_DISPLAY
    return pattern


def format_time(
    hour: int, minute: int, second: int, props: dict[str, Any]
) -> str:
    """Renderuje godzinę według wzorca z ``props["display"]``."""
    pattern = display_pattern(props)
    use12 = str(props.get("format", "24")) == "12"
    display_hour = (hour % 12 or 12) if use12 else hour

    def number(value: int, pad: bool) -> str:
        return f"{value:02d}" if pad else str(value)

    suffix = "AM" if hour < 12 else "PM"
    pieces: list[str] = []
    for token, text in split_tokens(pattern):
        if token == "HH":
            pieces.append(number(display_hour, True))
        elif token == "H":
            pieces.append(number(display_hour, False))
        elif token == "MM":
            pieces.append(number(minute, True))
        elif token == "M":
            pieces.append(number(minute, False))
        elif token == "SS":
            pieces.append(number(second, True))
        elif token == "S":
            pieces.append(number(second, False))
        elif token == "A":
            pieces.append(suffix)
        else:
            pieces.append(text)
    return "".join(pieces)
