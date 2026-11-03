from __future__ import annotations

import json
import time

from . import constants as C
from . import timeformat
from .model import BarArc, Element, Project, bar_arc_geometry, supports_rotation
from .resources import Resources

IND = "        "


def _js(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _num(value) -> str:
    if isinstance(value, float):
        return f"{value:g}"
    return str(int(value))


def _align_h(value: str) -> str:
    return {
        "left": "hmUI.align.LEFT",
        "center": "hmUI.align.CENTER_H",
        "right": "hmUI.align.RIGHT",
    }.get(value, "hmUI.align.CENTER_H")


def _align_v(value: str) -> str:
    return {
        "top": "hmUI.align.TOP",
        "center": "hmUI.align.CENTER_V",
        "bottom": "hmUI.align.BOTTOM",
    }.get(value, "hmUI.align.CENTER_V")


def _color(value: str, alpha: int = 255) -> str:
    return f"0x{C.rgba_to_int(value, alpha):08X}"


def _show(level: str = "ONLY_NORMAL") -> str:
    return f"hmUI.show_level.{level}"


def _arc_angles(start: float, end: float) -> tuple[str, str]:
    """Kąty łuku w układzie zegarka.

    Edytor liczy kąty zgodnie z ruchem wskazówek zegara, od godziny 3
    (0° = 3:00, 90° = 6:00). Zegarek liczy je przeciwnie do ruchu
    wskazówek (0° = 3:00, 90° = 12:00), więc wystarczy zmienić znak.
    Pełny okrąg wysyłamy jako 0..360, żeby uniknąć niejednoznacznego
    zakresu ujemnego.
    """
    span = float(end) - float(start)
    if abs(abs(span) - 360.0) < 0.001 and abs(float(start) % 360.0) < 0.001:
        # Pełny okrąg zaczynający się na godzinie 3 - zakres 0..360 jest
        # najbezpieczniejszy i nie zmienia punktu startu wypełnienia.
        return "0", "360"
    return _num(-float(start)), _num(-float(end))


def _bar_arc_device_angles(el: Element, geometry: BarArc) -> tuple[str, str]:
    """Kąty wypełnienia paska w układzie zegarka.

    Gdy pasek wypełnia się od końca, zamieniamy kąty miejscami, bo zegarek
    zawsze rysuje postęp od ``start_angle`` do ``end_angle``.
    """
    backward = bool(el.props.get("reverse", False)) != bool(geometry.reverse)
    if backward:
        return _arc_angles(geometry.end_angle, geometry.start_angle)
    return _arc_angles(geometry.start_angle, geometry.end_angle)


def _font_line(project: Project, props: dict) -> str | None:
    font = str(props.get("font", "") or "")
    if font and project.asset_file(font) is not None:
        return _js(font)
    return None


class _Emit:
    def __init__(self, project: Project, resources: Resources) -> None:
        self.project = project
        self.res = resources
        self.decls: list[str] = []
        self.body: list[str] = []
        self.time_defs: list[tuple[str, dict]] = []
        self.date_defs: list[tuple[str, dict]] = []
        self.city_defs: list[tuple[str, dict]] = []
        self.weather_defs: list[tuple[str, list[str]]] = []
        self.aod_defs: list[tuple[str, dict]] = []
        self.progress_defs: list[tuple[str, Element]] = []
        self.hand_defs: list[tuple[dict[str, str], Element]] = []
        self.needs_clock = False

    def var(self, el: Element, suffix: str = "") -> str:
        return f"wf_{el.id}{suffix}"

    def declare(self, name: str) -> None:
        self.decls.append(f"let {name} = '';")

    def add(self, *lines: str) -> None:
        self.body.extend(lines)

    def widget(self, var: str, widget: str, params: list[tuple[str, str]], declare: bool = True) -> str:
        if declare:
            self.decls.append(f"let {var} = '';")
        self.add(f"{var} = hmUI.createWidget(hmUI.widget.{widget}, {{")
        for key, value in params:
            self.add(f"    {key}: {value},")
        self.add("});")
        self.add("")
        return var

    def emit_all(self) -> None:
        project = self.project
        self.add("hmUI.createWidget(hmUI.widget.FILL_RECT, {")
        self.add("    x: 0,")
        self.add("    y: 0,")
        self.add(f"    w: {C.DEVICE['width']},")
        self.add(f"    h: {C.DEVICE['height']},")
        self.add(f"    color: {_color(project.background_color)},")
        self.add(f"    show_level: {_show()},")
        self.add("});")
        self.add("")

        background = self.res.background()
        if background:
            self.widget(
                "_wf_background",
                "IMG",
                [
                    ("x", "0"),
                    ("y", "0"),
                    ("w", str(C.DEVICE["width"])),
                    ("h", str(C.DEVICE["height"])),
                    ("src", _js(background)),
                    ("show_level", _show()),
                ],
            )

        for el in project.elements:
            if not el.visible:
                continue
            self.emit_element(el)

        self.emit_aod()
        self.emit_delegate()

    def emit_element(self, el: Element) -> None:
        p = el.props
        var = self.var(el)
        if el.type == "image":
            src = self.res.image(el)
            if not src:
                return
            content_x, content_y, content_w, content_h = el.render_rect()
            params = [
                ("x", _num(content_x)),
                ("y", _num(content_y)),
                ("w", _num(content_w)),
                ("h", _num(content_h)),
                ("src", _js(src)),
                ("show_level", _show()),
            ]
            alpha = int(p.get("opacity", 255))
            if alpha < 255:
                params.insert(5, ("alpha", str(max(0, alpha))))
            angle = int(el.rotation or 0)
            if angle:
                params.insert(5, ("angle", _num(angle)))
            self.widget(var, "IMG", params)

        elif el.type == "text":
            if not str(p.get("text", "")).strip():
                return
            baked = self.res.text_image(el) if supports_rotation(el.type) else ""
            if baked:
                # Tekst z obrotem jest obrazem: TEXT na zegarku nie ma kąta.
                self.widget(
                    var,
                    "IMG",
                    [
                        ("x", _num(el.x)),
                        ("y", _num(el.y)),
                        ("w", _num(el.w)),
                        ("h", _num(el.h)),
                        ("src", _js(baked)),
                        ("angle", _num(int(el.rotation))),
                        ("show_level", _show()),
                    ],
                )
                return
            params = self.base_text_params(el)
            params.append(("text", _js(str(p.get("text", "")))))
            self.widget(var, "TEXT", params)

        elif el.type == "time":
            params = self.base_text_params(el)
            params.append(("text", "''"))
            self.widget(var, "TEXT", params)
            self.time_defs.append((var, dict(p)))
            self.needs_clock = True

        elif el.type == "date":
            params = self.base_text_params(el)
            params.append(("text", "''"))
            self.widget(var, "TEXT", params)
            self.date_defs.append((var, dict(p)))
            self.needs_clock = True

        elif el.type == "data":
            source = str(p.get("source", "steps"))
            info = C.DATA_SOURCES.get(source, C.DATA_SOURCES["steps"])
            params = self.base_text_params(el)
            if source == "city":
                params.append(("text", _js("--")))
                self.widget(var, "TEXT", params)
                self.city_defs.append((var, dict(p)))
                return
            params.append(("type", info["type"]))
            if p.get("unit") and info.get("unit"):
                params.append(("unit_type", "1"))
            self.widget(var, "TEXT_FONT", params)

        elif el.type == "weather_icon":
            _prefix, images = self.res.weather(el)
            # Ikona startowa to wariant "nieznana" (25), więc widget jest widoczny
            # nawet przed synchronizacją pogody z telefonem. Indeks ikony jest
            # później ustawiany ręcznie z czujnika WEATHER (curAirIconIndex).
            fallback = images[25] if len(images) > 25 else images[0]
            size = int(p.get("size", min(el.w, el.h)) or min(el.w, el.h))
            icon_x = round(el.x + (el.w - size) / 2)
            icon_y = round(el.y + (el.h - size) / 2)
            icon_params = [
                ("x", _num(icon_x)),
                ("y", _num(icon_y)),
                ("w", _num(size)),
                ("h", _num(size)),
                ("src", _js(fallback)),
                ("show_level", _show()),
            ]
            if int(el.rotation or 0):
                icon_params.insert(5, ("angle", _num(int(el.rotation))))
            self.widget(var, "IMG", icon_params)
            self.weather_defs.append((var, list(images)))

        elif el.type == "progress_ring":
            self.emit_ring(el, var)
            self.progress_defs.append((var, el))

        elif el.type == "analog_hands":
            self.emit_hands(el, var)

        elif el.type == "progress_bar":
            self.emit_bar(el, var)
            self.progress_defs.append((var, el))

        elif el.type == "shortcut":
            self.emit_shortcut(el, var)

        elif el.type == "status":
            key = str(p.get("status", "bluetooth"))
            src = self.res.status(el)
            if not src:
                return
            size = int(p.get("size", max(el.w, el.h)) or max(el.w, el.h))
            icon_x = round(el.x + (el.w - size) / 2)
            icon_y = round(el.y + (el.h - size) / 2)
            self.widget(
                var,
                "IMG_STATUS",
                [
                    ("x", _num(icon_x)),
                    ("y", _num(icon_y)),
                    ("src", _js(src)),
                    ("type", C.STATUS_TYPES.get(key, C.STATUS_TYPES["bluetooth"])),
                    ("show_level", _show()),
                ],
            )

    def base_text_params(self, el: Element) -> list[tuple[str, str]]:
        p = el.props
        params: list[tuple[str, str]] = [
            ("x", _num(el.x)),
            ("y", _num(el.y)),
            ("w", _num(el.w)),
            ("h", _num(el.h)),
            ("text_size", str(max(1, int(p.get("size", 32))))),
            ("char_space", str(int(p.get("spacing", 0) or 0))),
            ("color", _color(str(p.get("color", "#FFFFFF")))),
            ("line_space", "0"),
            ("align_h", _align_h(str(p.get("align", "center")))),
            ("align_v", _align_v(str(p.get("valign", "center")))),
            ("text_style", "hmUI.text_style.ELLIPSIS"),
        ]
        font = _font_line(self.project, p)
        if font:
            params.append(("font", font))
        params.append(("show_level", _show()))
        return params

    def emit_ring(self, el: Element, var: str) -> None:
        p = el.props
        line_width = max(1, int(p.get("line_width", 8)))
        radius_override = int(p.get("radius", 0) or 0)
        radius = radius_override if radius_override > 0 else int(min(el.w, el.h) / 2 - line_width / 2)
        center_x = int(el.x + el.w / 2)
        center_y = int(el.y + el.h / 2)
        start_angle = int(p.get("start_angle", 0))
        end_angle = int(p.get("end_angle", 360))
        dev_start, dev_end = _arc_angles(start_angle, end_angle)
        corner = int(p.get("corner_flag", 0))
        bg = str(p.get("bg_color", "") or "")
        show_bg = bool(p.get("show_bg", True))
        if bg and show_bg:
            # Tło musi mieć level 100, bo domyślnie łuk ma zerowy postęp
            # i na zegarku w ogóle się nie pojawia.
            self.widget(
                self.var(el, "_bg"),
                "ARC_PROGRESS",
                [
                    ("center_x", str(center_x)),
                    ("center_y", str(center_y)),
                    ("start_angle", dev_start),
                    ("end_angle", dev_end),
                    ("radius", str(radius)),
                    ("line_width", str(line_width)),
                    ("corner_flag", str(corner)),
                    ("color", _color(bg)),
                    ("level", "100"),
                    ("show_level", _show()),
                ],
            )
        self.widget(
            var,
            "ARC_PROGRESS",
            [
                ("center_x", str(center_x)),
                ("center_y", str(center_y)),
                ("start_angle", dev_start),
                ("end_angle", dev_end),
                ("radius", str(radius)),
                ("line_width", str(line_width)),
                ("corner_flag", str(corner)),
                ("color", _color(str(p.get("color", "#4D9BFF")))),
                ("level", "0"),
                ("show_level", _show()),
            ],
        )

    def emit_hands(self, el: Element, var: str) -> None:
        hands = self.res.hands(el)
        if not hands:
            return
        rotation = int(el.rotation or 0)
        center_x = int(el.x + el.w / 2)
        center_y = int(el.y + el.h / 2)
        screen_w = int(C.DEVICE["width"])
        screen_h = int(C.DEVICE["height"])
        variables: dict[str, str] = {}
        for role in ("hour", "minute", "second"):
            if role not in hands:
                continue
            asset = hands[role]
            hand_var = self.var(el, f"_{role}")
            # IMG z kątem jest obsługiwany na wszystkich urządzeniach Zepp OS
            # (IMG_POINTER bywa ignorowany i zostawia samą nakładkę osi).
            # Obraz wskazówki jest przycięty do widocznej treści, więc
            # pos_x/pos_y odtwarzają jego pierwotne miejsce na płótnie,
            # a center_x/y pozostają środkiem tarczy. 0° wskazuje godzinę 12.
            pos_x = center_x - asset.canvas_width / 2 + asset.offset_x
            pos_y = center_y - asset.canvas_height / 2 + asset.offset_y
            self.widget(
                hand_var,
                "IMG",
                [
                    ("x", "0"),
                    ("y", "0"),
                    ("w", str(screen_w)),
                    ("h", str(screen_h)),
                    ("pos_x", _num(pos_x)),
                    ("pos_y", _num(pos_y)),
                    ("center_x", str(center_x)),
                    ("center_y", str(center_y)),
                    ("src", _js(asset.name)),
                    ("angle", _num(rotation)),
                    # Obraz jest już przycięty do widocznej treści i ma
                    # naturalny rozmiar. Wyłączamy skalowanie, żeby żadna
                    # wersja firmware nie rozciągnęła go do 466×466 (to
                    # zepsułoby obrót i zjadło pamięć).
                    ("auto_scale", "false"),
                    ("show_level", _show()),
                ],
            )
            variables[role] = hand_var
        if "cap" in hands:
            asset = hands["cap"]
            pos_x = center_x - asset.canvas_width / 2 + asset.offset_x
            pos_y = center_y - asset.canvas_height / 2 + asset.offset_y
            if rotation:
                # Obrót nakładki musi mieć ten sam punkt obrotu co wskazówki
                # (środek tarczy), także gdy grafika nie jest idealnie
                # symetryczna. Pełnoekranowy widget + jawny center_x/y to
                # gwarantują, a sam obraz pozostaje mały.
                cap_params = [
                    ("x", "0"),
                    ("y", "0"),
                    ("w", str(screen_w)),
                    ("h", str(screen_h)),
                    ("pos_x", _num(pos_x)),
                    ("pos_y", _num(pos_y)),
                    ("center_x", str(center_x)),
                    ("center_y", str(center_y)),
                    ("src", _js(asset.name)),
                    ("angle", _num(rotation)),
                    ("auto_scale", "false"),
                    ("show_level", _show()),
                ]
            else:
                cap_params = [
                    ("x", _num(pos_x)),
                    ("y", _num(pos_y)),
                    ("w", str(asset.width)),
                    ("h", str(asset.height)),
                    ("src", _js(asset.name)),
                    ("auto_scale", "false"),
                    ("show_level", _show()),
                ]
            self.widget(self.var(el, "_cap"), "IMG", cap_params)
        if variables:
            self.hand_defs.append((variables, el))
            self.needs_clock = True

    def _bar_image_mode(self, el: Element) -> bool:
        return (
            str(el.props.get("style", "solid")) == "image"
            and bool(self.res.bar_image(el, "src100"))
        )

    def emit_bar(self, el: Element, var: str) -> None:
        geometry = bar_arc_geometry(el)
        image_mode = self._bar_image_mode(el)
        if geometry is not None:
            if image_mode:
                self.emit_bar_arc_image(el, var)
            else:
                self.emit_bar_arc(el, var, geometry)
        elif image_mode:
            self.emit_bar_image(el, var)
        else:
            self.emit_bar_solid(el, var)

    def emit_bar_solid(self, el: Element, var: str) -> None:
        p = el.props
        radius = max(0, int(p.get("radius", 0) or 0))
        bg = str(p.get("bg_color", "") or "")
        if bg and bool(p.get("show_bg", True)):
            self.widget(
                self.var(el, "_bg"),
                "FILL_RECT",
                [
                    ("x", _num(el.x)),
                    ("y", _num(el.y)),
                    ("w", _num(el.w)),
                    ("h", _num(el.h)),
                    ("radius", str(radius)),
                    ("color", _color(bg)),
                    ("show_level", _show()),
                ],
            )
        self.widget(
            var,
            "FILL_RECT",
            [
                ("x", _num(el.x)),
                ("y", _num(el.y)),
                ("w", _num(el.w)),
                ("h", _num(el.h)),
                ("radius", str(radius)),
                ("color", _color(str(p.get("color", "#4D9BFF")))),
                ("show_level", _show()),
            ],
        )

    def emit_bar_image(self, el: Element, var: str) -> None:
        p = el.props
        image0 = self.res.bar_image(el, "src0")
        image100 = self.res.bar_image(el, "src100")
        show_bg = bool(p.get("show_bg", True))
        if image0 and show_bg:
            self.widget(
                self.var(el, "_bg"),
                "IMG",
                [
                    ("x", _num(el.x)),
                    ("y", _num(el.y)),
                    ("w", _num(el.w)),
                    ("h", _num(el.h)),
                    ("src", _js(image0)),
                    ("show_level", _show()),
                ],
            )
        else:
            bg = str(p.get("bg_color", "") or "")
            if bg and show_bg:
                self.widget(
                    self.var(el, "_bg"),
                    "FILL_RECT",
                    [
                        ("x", _num(el.x)),
                        ("y", _num(el.y)),
                        ("w", _num(el.w)),
                        ("h", _num(el.h)),
                        ("radius", str(max(0, int(p.get("radius", 0) or 0)))),
                        ("color", _color(bg)),
                        ("show_level", _show()),
                    ],
                )
        self.widget(
            var,
            "IMG",
            [
                ("x", _num(el.x)),
                ("y", _num(el.y)),
                ("w", _num(el.w)),
                ("h", _num(el.h)),
                ("src", _js(image100)),
                ("show_level", _show()),
            ],
        )

    def emit_bar_arc(
        self, el: Element, var: str, geometry: BarArc
    ) -> None:
        p = el.props
        common = [
            ("center_x", str(geometry.center_x)),
            ("center_y", str(geometry.center_y)),
            ("radius", str(geometry.radius)),
            ("line_width", str(geometry.line_width)),
            ("corner_flag", str(int(p.get("corner_flag", 0) or 0))),
            ("show_level", _show()),
        ]
        bg = str(p.get("bg_color", "") or "")
        show_bg = bool(p.get("show_bg", True))
        bg_start, bg_end = _arc_angles(geometry.start_angle, geometry.end_angle)
        if bg and show_bg:
            self.widget(
                self.var(el, "_bg"),
                "ARC_PROGRESS",
                common
                + [
                    ("start_angle", bg_start),
                    ("end_angle", bg_end),
                    ("color", _color(bg)),
                    ("level", "100"),
                ],
            )
        fill_start, fill_end = _bar_arc_device_angles(el, geometry)
        self.widget(
            var,
            "ARC_PROGRESS",
            common
            + [
                ("start_angle", fill_start),
                ("end_angle", fill_end),
                ("color", _color(str(p.get("color", "#4D9BFF")))),
                ("level", "0"),
            ],
        )

    def emit_bar_arc_image(self, el: Element, var: str) -> None:
        frames = self.res.bar_frames(el)
        if not frames:
            geometry = bar_arc_geometry(el)
            if geometry is not None:
                self.emit_bar_arc(el, var, geometry)
            else:
                self.emit_bar_solid(el, var)
            return
        self.widget(
            var,
            "IMG",
            [
                ("x", _num(el.x)),
                ("y", _num(el.y)),
                ("w", _num(el.w)),
                ("h", _num(el.h)),
                ("src", _js(frames[0])),
                ("show_level", _show()),
            ],
        )

    def emit_shortcut(self, el: Element, var: str) -> None:
        p = el.props
        icon = self.res.shortcut_icon(el)
        if icon:
            content_x, content_y, content_w, content_h = el.render_rect()
            icon_params = [
                ("x", _num(content_x)),
                ("y", _num(content_y)),
                ("w", _num(content_w)),
                ("h", _num(content_h)),
                ("src", _js(icon)),
                ("show_level", _show()),
            ]
            if int(el.rotation or 0):
                icon_params.insert(5, ("angle", _num(int(el.rotation))))
            self.widget(self.var(el, "_icon"), "IMG", icon_params)
        if str(p.get("kind", "app")) == "app":
            key = str(p.get("app", ""))
            info = C.SHORTCUT_BY_KEY.get(key)
            if info is None:
                return
            self.decls.append(f"let {var} = '';")
            self.add(f"{var} = hmUI.createWidget(hmUI.widget.BUTTON, {{")
            self.add(f"    x: {_num(el.x)},")
            self.add(f"    y: {_num(el.y)},")
            self.add(f"    w: {_num(el.w)},")
            self.add(f"    h: {_num(el.h)},")
            self.add("    text: '',")
            self.add("    normal_src: 'empty.png',")
            self.add("    press_src: 'empty.png',")
            self.add(f"    show_level: {_show()},")
            self.add("    click_func: function() {")
            self.add(f"        {info['js']}")
            self.add("    },")
            self.add("});")
            self.add("")
        else:
            source = str(p.get("data", "steps"))
            info = C.DATA_SOURCES.get(source, C.DATA_SOURCES["steps"])
            if not info.get("type"):
                return
            self.widget(
                var,
                "IMG_CLICK",
                [
                    ("x", _num(el.x)),
                    ("y", _num(el.y)),
                    ("w", _num(el.w)),
                    ("h", _num(el.h)),
                    ("type", info["type"]),
                    ("show_level", _show()),
                ],
            )

    def emit_aod(self) -> None:
        project = self.project
        if not project.aod_simple or not self.time_defs:
            return
        template = next((el for el in project.elements if el.type == "time" and el.visible), None)
        if template is None:
            return
        p = template.props
        self.decls.append("let _aod_time = '';")
        self.add("_aod_time = hmUI.createWidget(hmUI.widget.TEXT, {")
        self.add(f"    x: {_num(template.x)},")
        self.add(f"    y: {_num(template.y)},")
        self.add(f"    w: {_num(template.w)},")
        self.add(f"    h: {_num(template.h)},")
        self.add(f"    text_size: {max(1, int(p.get('size', 96)))},")
        self.add(f"    char_space: {int(p.get('spacing', 0) or 0)},")
        self.add(f"    color: {_color(project.aod_color)},")
        self.add("    line_space: 0,")
        self.add(f"    align_h: {_align_h(str(p.get('align', 'center')))},")
        self.add(f"    align_v: {_align_v(str(p.get('valign', 'center')))},")
        self.add("    text_style: hmUI.text_style.ELLIPSIS,")
        font = _font_line(project, p)
        if font:
            self.add(f"    font: {font},")
        self.add("    text: '',")
        self.add(f"    show_level: {_show('ONAL_AOD')},")
        self.add("});")
        self.add("")
        self.aod_defs.append(("_aod_time", dict(p)))
        self.needs_clock = True

    def emit_delegate(self) -> None:
        self.decls.append("let _clockTimer = undefined;")
        self.decls.append("let _sensors = {};")
        has_weather = bool(self.city_defs or self.weather_defs)
        if has_weather:
            self.decls.append("let _weatherTimer = undefined;")
            self.decls.append("let weatherSensor = '';")
        for var, images in self.weather_defs:
            self.decls.append(f"const {var}_IMGS = {_js(images)};")
        self.add("hmUI.createWidget(hmUI.widget.WIDGET_DELEGATE, {")
        self.add("    resume_call: function() {")
        self.add("        const _screen = hmSetting.getScreenType();")
        self.add("        _updateProgress();")
        if self.needs_clock:
            self.add("        _updateClock();")
            self.add("        if (_screen == hmSetting.screen_type.AOD) {")
            self.add("            const _t = _getTime();")
            self.add("            if (_t && _t.addEventListener && _t.event && _t.event.MINUTEEND) {")
            self.add("                _t.addEventListener(_t.event.MINUTEEND, _updateClock);")
            self.add("            }")
            self.add("        } else if (!_clockTimer) {")
            self.add("            _clockTimer = timer.createTimer(0, 1000, function() {")
            self.add("                _updateClock();")
            self.add("            });")
            self.add("        }")
        if has_weather:
            self.add("        _updateWeather();")
            self.add("        if (_screen != hmSetting.screen_type.AOD && !_weatherTimer) {")
            self.add("            _weatherTimer = timer.createTimer(0, 60000, function() {")
            self.add("                _updateWeather();")
            self.add("            });")
            self.add("        }")
        self.add("    },")
        self.add("    pause_call: function() {")
        self.add("        if (_clockTimer) {")
        self.add("            timer.stopTimer(_clockTimer);")
        self.add("            _clockTimer = undefined;")
        self.add("        }")
        if has_weather:
            self.add("        if (_weatherTimer) {")
            self.add("            timer.stopTimer(_weatherTimer);")
            self.add("            _weatherTimer = undefined;")
            self.add("        }")
        if self.needs_clock:
            self.add("        const _t = _getTime();")
            self.add("        if (_t && _t.removeEventListener && _t.event && _t.event.MINUTEEND) {")
            self.add("            _t.removeEventListener(_t.event.MINUTEEND, _updateClock);")
            self.add("        }")
        self.add("    },")
        self.add("});")
        self.add("")
        if self.needs_clock:
            self.add("_updateClock();")
        if has_weather:
            self.add("_updateWeather();")
        self.add("_updateProgress();")


def _date_expression(pattern: str, lang: str, used_langs: set[str]) -> str:
    used_langs.add(lang)
    suffix = lang.upper()
    tokens: list[tuple[str, str]] = [
        ("YYYY", "String(t.year)"),
        ("MMMM", f"_MON_{suffix}[t.month - 1]"),
        ("dddd", f"_DOW_{suffix}[t.week - 1]"),
        ("MMM", f"_MONS_{suffix}[t.month - 1]"),
        ("ddd", f"_DOWS_{suffix}[t.week - 1]"),
        ("YY", "String(t.year).slice(-2)"),
        ("DD", "_p2(t.day)"),
        ("MM", "_p2(t.month)"),
        ("D", "String(t.day)"),
        ("M", "String(t.month)"),
    ]
    out: list[str] = []
    i = 0
    while i < len(pattern):
        matched = False
        for token, expr in tokens:
            if pattern.startswith(token, i):
                out.append(expr)
                i += len(token)
                matched = True
                break
        if matched:
            continue
        j = i
        while j < len(pattern) and not any(pattern.startswith(token, j) for token, _ in tokens):
            j += 1
        out.append(_js(pattern[i:j]))
        i = j
    if not out:
        return "''"
    if len(out) == 1:
        return out[0]
    return " + ".join(out)


def _hour_var(props: dict, pad: bool = True) -> str:
    fmt = str(props.get("format", "24"))
    if fmt == "12":
        return "_h12p" if pad else "_h12"
    if fmt == "auto":
        return "_hautop" if pad else "_hauto"
    return "_h24p" if pad else "_h24"


def _time_text_expression(props: dict) -> str:
    pattern = timeformat.display_pattern(props)
    parts: list[str] = []
    for token, text in timeformat.split_tokens(pattern):
        if token == "HH":
            parts.append(_hour_var(props, True))
        elif token == "H":
            parts.append(_hour_var(props, False))
        elif token == "MM":
            parts.append("_ms")
        elif token == "M":
            parts.append("_m")
        elif token == "SS":
            parts.append("_ss")
        elif token == "S":
            parts.append("_s")
        elif token == "A":
            parts.append("_ampm")
        elif text:
            parts.append(_js(text))
    if not parts:
        return "''"
    if len(parts) == 1:
        return parts[0]
    return " + ".join(parts)


def build_index_js(project: Project, resources: Resources) -> str:
    emit = _Emit(project, resources)
    emit.emit_all()

    used_langs: set[str] = set()
    date_lines: list[str] = []
    for var, props in emit.date_defs:
        pattern = str(props.get("format", "DD.MM.YYYY"))
        lang = str(props.get("lang", "pl"))
        date_lines.append(f"    {var}.setProperty(hmUI.prop.TEXT, {_date_expression(pattern, lang, used_langs)});")

    lines: list[str] = []
    lines.append("try {")
    lines.append("    (() => {")
    lines.append("        const __$$app$$__ = __$$hmAppManager$$__.currentApp;")
    lines.append("        function getApp() {")
    lines.append("            return __$$app$$__.app;")
    lines.append("        }")
    lines.append("        function getCurrentPage() {")
    lines.append("            return __$$app$$__.current && __$$app$$__.current.module;")
    lines.append("        }")
    lines.append("        const __$$module$$__ = __$$app$$__.current;")
    lines.append(
        "        const h = new DeviceRuntimeCore.WidgetFactory("
        "new DeviceRuntimeCore.HmDomApi(__$$app$$__, __$$module$$__));"
    )
    lines.append("        const {px} = __$$app$$__.__globals__;")
    lines.append("")
    lines.append("        let timeSensor = '';")
    lines.extend(f"        {decl}" for decl in emit.decls)
    lines.append("")

    for lang in sorted(used_langs):
        key = lang.upper()
        days = C.WEEKDAYS.get(lang, C.WEEKDAYS["pl"])
        months = C.MONTHS.get(lang, C.MONTHS["pl"])
        lines.append(f"        const _DOW_{key} = {_js(days['full'])};")
        lines.append(f"        const _DOWS_{key} = {_js(days['short'])};")
        lines.append(f"        const _MON_{key} = {_js(months['full'])};")
        lines.append(f"        const _MONS_{key} = {_js(months['short'])};")
    if used_langs:
        lines.append("")

    lines.append("        function _getTime() {")
    lines.append("            if (!timeSensor) {")
    lines.append("                timeSensor = hmSensor.createSensor(hmSensor.id.TIME);")
    lines.append("            }")
    lines.append("            return timeSensor;")
    lines.append("        }")
    lines.append("")
    lines.append("        function _p2(value) {")
    lines.append("            return String(value).padStart(2, '0');")
    lines.append("        }")
    lines.append("")

    has_weather = bool(emit.city_defs or emit.weather_defs)
    if has_weather:
        lines.append("        function _getWeather() {")
        lines.append("            if (!weatherSensor) {")
        lines.append("                try {")
        lines.append("                    weatherSensor = hmSensor.createSensor(hmSensor.id.WEATHER);")
        lines.append("                } catch (e) {")
        lines.append("                    weatherSensor = null;")
        lines.append("                }")
        lines.append("                if (weatherSensor && weatherSensor.addEventListener) {")
        lines.append("                    try {")
        lines.append("                        weatherSensor.addEventListener(hmSensor.event.CHANGE, function() {")
        lines.append("                            _updateWeather();")
        lines.append("                        });")
        lines.append("                    } catch (e) {")
        lines.append("                    }")
        lines.append("                }")
        lines.append("            }")
        lines.append("            return weatherSensor;")
        lines.append("        }")
        lines.append("")
        lines.append("        function _updateWeather() {")
        lines.append("            let _w = null;")
        lines.append("            try {")
        lines.append("                _w = _getWeather();")
        lines.append("            } catch (e) {")
        lines.append("                _w = null;")
        lines.append("            }")
        lines.append("            let _forecast = null;")
        lines.append("            if (_w) {")
        lines.append("                try {")
        lines.append(
            "                    _forecast = _w.getForecastWeather ? _w.getForecastWeather() : null;"
        )
        lines.append("                } catch (e) {")
        lines.append("                    _forecast = null;")
        lines.append("                }")
        lines.append("            }")
        if emit.weather_defs:
            lines.append("            if (_w) {")
            lines.append("                try {")
            lines.append("                    let _idx = Math.floor(Number(_w.curAirIconIndex));")
            lines.append("                    if (!isFinite(_idx) || _idx < 0) {")
            lines.append(
                "                        const _days = _forecast && _forecast.forecastData "
                "? _forecast.forecastData.data : null;"
            )
            lines.append(
                "                        _idx = _days && _days.length "
                "? Math.floor(Number(_days[0].index)) : -1;"
            )
            lines.append("                    }")
            lines.append("                    if (isFinite(_idx)) {")
            for var, images in emit.weather_defs:
                limit = len(images)
                lines.append(
                    f"                        if (_idx >= 0 && _idx < {limit}) "
                    f"{{ {var}.setProperty(hmUI.prop.SRC, {var}_IMGS[_idx]); }}"
                )
            lines.append("                    }")
            lines.append("                } catch (e) {")
            lines.append("                }")
            lines.append("            }")
        if emit.city_defs:
            lines.append("            let _name = '';")
            lines.append("            if (_forecast && _forecast.cityName) {")
            lines.append("                try {")
            lines.append("                    _name = String(_forecast.cityName).trim();")
            lines.append("                } catch (e) {")
            lines.append("                    _name = '';")
            lines.append("                }")
            lines.append("            }")
            lines.append("            if (!_name) _name = '--';")
            for var, _ in emit.city_defs:
                lines.append(f"            {var}.setProperty(hmUI.prop.TEXT, _name);")
        lines.append("        }")
        lines.append("")
    if emit.needs_clock:
        lines.append("        function _updateClock() {")
        lines.append("            const t = _getTime();")
        lines.append("            if (!t) return;")
        lines.append("            const _h24 = String(t.hour);")
        lines.append("            const _h24p = _p2(t.hour);")
        lines.append("            const _h12 = String(t.hour % 12 || 12);")
        lines.append("            const _h12p = _p2(t.hour % 12 || 12);")
        lines.append("            const _hauto = String(t.format_hour);")
        lines.append("            const _hautop = _p2(t.format_hour);")
        lines.append("            const _ms = _p2(t.minute);")
        lines.append("            const _m = String(t.minute);")
        lines.append("            const _ss = _p2(t.second);")
        lines.append("            const _s = String(t.second);")
        lines.append("            const _ampm = t.hour < 12 ? 'AM' : 'PM';")
        for var, props in emit.time_defs:
            lines.append(f"            {var}.setProperty(hmUI.prop.TEXT, {_time_text_expression(props)});")
        lines.extend(date_lines)
        for var, props in emit.aod_defs:
            lines.append(f"            {var}.setProperty(hmUI.prop.TEXT, {_time_text_expression(props)});")
        if emit.hand_defs:
            lines.append("            const _handMin = t.minute + t.second / 60;")
            lines.append("            const _handHour = (t.hour % 12) + _handMin / 60;")
            for variables, hand_el in emit.hand_defs:
                rotation = int(hand_el.rotation or 0)
                offset = f" + {rotation}" if rotation else ""
                if "hour" in variables:
                    lines.append(
                        f"            {variables['hour']}.setProperty("
                        f"hmUI.prop.MORE, {{ angle: _handHour * 30{offset} }});"
                    )
                if "minute" in variables:
                    lines.append(
                        f"            {variables['minute']}.setProperty("
                        f"hmUI.prop.MORE, {{ angle: _handMin * 6{offset} }});"
                    )
                if "second" in variables:
                    lines.append(
                        f"            {variables['second']}.setProperty("
                        f"hmUI.prop.MORE, {{ angle: t.second * 6{offset} }});"
                    )
        if emit.progress_defs:
            lines.append("            if (t.second % 5 === 0) {")
            lines.append("                _updateProgress();")
            lines.append("            }")
        lines.append("        }")
        lines.append("")

    lines.append("        function _sensor(key, idKey) {")
    lines.append("            if (!_sensors[key]) {")
    lines.append("                try {")
    lines.append("                    const sensor = hmSensor.createSensor(hmSensor.id[idKey]);")
    lines.append("                    if (sensor && sensor.addEventListener) {")
    lines.append("                        sensor.addEventListener(hmSensor.event.CHANGE, function() {")
    lines.append("                            _updateProgress();")
    lines.append("                        });")
    lines.append("                    }")
    lines.append("                    _sensors[key] = sensor || {};")
    lines.append("                } catch (e) {")
    lines.append("                    _sensors[key] = {};")
    lines.append("                }")
    lines.append("            }")
    lines.append("            return _sensors[key];")
    lines.append("        }")
    lines.append("")
    lines.append("        function _updateProgress() {")
    for var, el in emit.progress_defs:
        info = C.PROGRESS_SOURCES.get(str(el.props.get("source", "steps")), C.PROGRESS_SOURCES["steps"])
        name, sensor_id, expr, target = info
        lines.append("            try {")
        lines.append("                {")
        lines.append(f"                    const {name} = _sensor({_js(name)}, {_js(sensor_id)});")
        lines.append(f"                    let _v = Number({expr});")
        lines.append("                    if (!isFinite(_v)) _v = 0;")
        lines.append(f"                    let _t = Number({target});")
        lines.append("                    if (!_t || _t <= 0) _t = 1;")
        lines.append("                    const _r = Math.max(0, Math.min(1, _v / _t));")
        if el.type == "progress_ring":
            # Sam postęp wystarczy ustawić przez LEVEL - ponowne wysyłanie
            # całej geometrii (MORE) nie odświeża łuku na zegarku.
            lines.append(
                f"                    {var}.setProperty("
                "hmUI.prop.LEVEL, Math.round(_r * 100));"
            )
        else:
            p = el.props
            reverse = bool(p.get("reverse", False))
            geometry = bar_arc_geometry(el)
            image_mode = emit._bar_image_mode(el)
            if geometry is not None and image_mode:
                frames = emit.res.bar_frames(el)
                if frames:
                    lines.append(f"                    const _frames = {_js(frames)};")
                    lines.append(
                        "                    const _level = Math.max(0, "
                        "Math.min(_frames.length - 1, "
                        "Math.round(_r * (_frames.length - 1))));"
                    )
                    lines.append(
                        f"                    {var}.setProperty(hmUI.prop.SRC, _frames[_level]);"
                    )
            elif geometry is not None:
                lines.append(
                    f"                    {var}.setProperty(hmUI.prop.VISIBLE, _r > 0.0001);"
                )
                lines.append(
                    f"                    {var}.setProperty("
                    "hmUI.prop.LEVEL, Math.round(_r * 100));"
                )
            elif image_mode:
                vertical = str(p.get("direction", "h")) == "v"
                lines.append(
                    f"                    {var}.setProperty(hmUI.prop.VISIBLE, _r > 0.0001);"
                )
                lines.append("                    if (_r > 0.0001) {")
                if vertical:
                    lines.append(
                        f"                    const _h = Math.max(1, Math.round({el.h} * _r));"
                    )
                    y_expr = str(el.y) if reverse else f"{el.y + el.h} - _h"
                    pos_y = "0" if reverse else "-(%d - _h)" % el.h
                    lines.append(
                        f"                    {var}.setProperty(hmUI.prop.MORE, {{"
                    )
                    lines.append(f"                        x: {el.x},")
                    lines.append(f"                        y: {y_expr},")
                    lines.append(f"                        w: {el.w},")
                    lines.append("                        h: _h,")
                    lines.append("                        pos_x: 0,")
                    lines.append(f"                        pos_y: {pos_y},")
                    lines.append("                    });")
                else:
                    lines.append(
                        f"                    const _w = Math.max(1, Math.round({el.w} * _r));"
                    )
                    x_expr = f"{el.x + el.w} - _w" if reverse else str(el.x)
                    pos_x = "-(%d - _w)" % el.w if reverse else "0"
                    lines.append(
                        f"                    {var}.setProperty(hmUI.prop.MORE, {{"
                    )
                    lines.append(f"                        x: {x_expr},")
                    lines.append(f"                        y: {el.y},")
                    lines.append("                        w: _w,")
                    lines.append(f"                        h: {el.h},")
                    lines.append(f"                        pos_x: {pos_x},")
                    lines.append("                        pos_y: 0,")
                    lines.append("                    });")
                lines.append("                    }")
            else:
                vertical = str(p.get("direction", "h")) == "v"
                lines.append(
                    f"                    {var}.setProperty(hmUI.prop.VISIBLE, _r > 0.0001);"
                )
                lines.append("                    if (_r > 0.0001) {")
                if vertical:
                    lines.append(
                        f"                    const _h = Math.max(1, Math.round({el.h} * _r));"
                    )
                    y_expr = str(el.y) if reverse else f"{el.y + el.h} - _h"
                    lines.append(
                        f"                    {var}.setProperty(hmUI.prop.MORE, {{"
                    )
                    lines.append(f"                        x: {el.x},")
                    lines.append(f"                        y: {y_expr},")
                    lines.append(f"                        w: {el.w},")
                    lines.append("                        h: _h,")
                    lines.append("                    });")
                else:
                    lines.append(
                        f"                    const _w = Math.max(1, Math.round({el.w} * _r));"
                    )
                    x_expr = f"{el.x + el.w} - _w" if reverse else str(el.x)
                    lines.append(
                        f"                    {var}.setProperty(hmUI.prop.MORE, {{"
                    )
                    lines.append(f"                        x: {x_expr},")
                    lines.append(f"                        y: {el.y},")
                    lines.append("                        w: _w,")
                    lines.append(f"                        h: {el.h},")
                    lines.append("                    });")
                lines.append("                    }")
        lines.append("                }")
        lines.append("            } catch (e) {")
        lines.append("            }")
    lines.append("        }")
    lines.append("")

    # Runtime ZeppOS wywołuje build(); bez niego init_view() nie startuje i tarcza
    # pokazuje czarny ekran, mimo że podgląd/miniatura wygląda poprawnie.
    lines.append("        __$$module$$__.module = DeviceRuntimeCore.WatchFace({")
    lines.append("            init_view() {")
    lines.extend(f"                {line}" if line else "" for line in emit.body)
    lines.append("            },")
    lines.append("            onInit() {")
    lines.append("            },")
    lines.append("            build() {")
    lines.append("                this.init_view();")
    lines.append("            },")
    lines.append("            onDestroy() {")
    lines.append("                if (_clockTimer) {")
    lines.append("                    timer.stopTimer(_clockTimer);")
    lines.append("                    _clockTimer = undefined;")
    lines.append("                }")
    if has_weather:
        lines.append("                if (_weatherTimer) {")
        lines.append("                    timer.stopTimer(_weatherTimer);")
        lines.append("                    _weatherTimer = undefined;")
        lines.append("                }")
    lines.append("                _sensors = {};")
    lines.append("            }")
    lines.append("        });")
    lines.append("        ;")
    lines.append("    })();")
    lines.append("} catch (e) {")
    lines.append("    console.log('Mini Program Error', e);")
    lines.append("    e && e.stack && e.stack.split(/\\n/).forEach(i => console.log('error stack', i));")
    lines.append("    ;")
    lines.append("}")
    return "\n".join(lines) + "\n"


def build_app_js() -> str:
    return (C.TEMPLATES_DIR / "app.js").read_text(encoding="utf-8")


def _platforms() -> list[dict]:
    return [
        {"name": C.PLATFORM_NAME, "deviceSource": source}
        for source in C.DEVICE["device_sources"]
    ]


_WEATHER_SOURCES = {
    "city",
    "weather_temp",
    "weather_low",
    "weather_high",
    "humidity",
    "uvi",
    "aqi",
    "pressure",
    "altitude",
    "sun_rise",
    "sun_set",
}


def _needs_location(project: Project) -> bool:
    for el in project.elements:
        if not el.visible:
            continue
        if el.type == "weather_icon":
            return True
        if el.type == "data" and str(el.props.get("source", "")) in _WEATHER_SOURCES:
            return True
    return False


def build_app_json(
    project: Project,
    *,
    package_info: bool = True,
    mode: str = "production",
    preview_name: str = "Preview.png",
    lockscreen: int = 0,
) -> str:
    app = {
        "configVersion": "v2",
        "app": {
            "appIdType": 0,
            "appId": int(project.app_id),
            "appName": project.name,
            "appType": "watchface",
            "version": {
                "code": int(project.version_code),
                "name": project.version_name,
            },
            "vender": project.vender,
            "description": project.description,
            "icon": preview_name,
            "cover": [preview_name],
            "extraInfo": {"madeBy": 1, "fromZoom": False},
        },
        "permissions": ["gps"] if _needs_location(project) else [],
        "runtime": {
            "apiVersion": {
                "compatible": "1.0.0",
                "target": "1.0.1",
                "minVersion": "1.0.0",
            }
        },
        "i18n": {
            "en-US": {"icon": preview_name, "appName": project.name},
        },
        "defaultLanguage": "en-US",
        "debug": False,
        "module": {
            "watchface": {
                "path": "watchface/index",
                "main": 1,
                "editable": 0,
                "lockscreen": int(lockscreen),
                "hightCost": 0,
            }
        },
        "platforms": _platforms(),
        "designWidth": C.DEVICE["design_width"],
    }
    if package_info:
        app["packageInfo"] = {
            "mode": mode,
            "timeStamp": int(time.time()),
            "expiredTime": 172800,
            "zpm": "2.8.2",
        }
    return json.dumps(app, ensure_ascii=False, indent=2)


def build_side_json(project: Project) -> str:
    data = {
        "configVersion": "v2",
        "app": {
            "appIdType": 0,
            "appId": 1008000,
            "appName": "WatchFace",
            "appType": "watchface",
            "version": {"code": 1, "name": "1.0.0"},
            "vender": project.vender,
            "description": "",
            "icon": "",
            "cover": [],
            "extraInfo": {"madeBy": 1, "fromZoom": False},
        },
        "permissions": [],
        "runtime": {
            "apiVersion": {
                "compatible": "1.0.0",
                "target": "1.0.1",
                "minVersion": "1.0",
            }
        },
        "i18n": {"en-US": {"icon": "", "appName": "WatchFace"}},
        "defaultLanguage": "en-US",
        "debug": False,
        "module": {
            "watchface": {
                "path": "watchface/default-target/index",
                "main": 1,
                "editable": 0,
                "lockscreen": 1,
                "hightCost": 0,
            }
        },
        "platforms": _platforms(),
        "designWidth": C.DEVICE["design_width"],
        "packageInfo": {
            "mode": "production",
            "timeStamp": int(time.time()),
            "expiredTime": 172800,
            "zpm": "2.10.6-beta",
        },
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
