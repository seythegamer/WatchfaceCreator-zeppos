from __future__ import annotations

import datetime as _dt
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QMenu, QWidget

from .. import constants as C
from ..model import (
    Element,
    Project,
    apply_content_scale,
    center_element,
    normalize_rotation,
    rotation_center,
    supports_content_scale,
    supports_rotation,
)
from ..render import render_project

HANDLE = 9.0
RING_DOT = 10.0
ROTATE_DOT = 11.0
ROTATE_GAP = 26.0
MIN_SIZE = 8


class Canvas(QWidget):
    selectionChanged = Signal(object)
    liveChanged = Signal()
    editFinished = Signal()
    zoomChanged = Signal(float)
    positionChanged = Signal(int, int)
    statusMessage = Signal(str)
    deleteRequested = Signal()

    def __init__(self, project: Project | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.selected_id: str | None = None
        self.hover_id: str | None = None
        self.show_grid = True
        self.snap = True
        self.live = False
        self.samples: dict[str, tuple[str, float]] | None = None
        self.moment_override: _dt.datetime | None = None
        self.weather_index: int | None = None
        self._scale = 1.0
        self._origin = QPointF(0, 0)
        self._drag: dict | None = None
        self._snap_guides: list[tuple[str, float]] = []
        self._last_zoom = 0.0
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(480, 480)
        self.setCursor(Qt.ArrowCursor)

    def set_project(self, project: Project) -> None:
        self.project = project
        self.selected_id = None
        self.hover_id = None
        self._drag = None
        self.samples = None
        self.moment_override = None
        self.weather_index = None
        self.selectionChanged.emit(None)
        self.update()

    def set_preview_data(
        self,
        samples: dict[str, tuple[str, float]] | None,
        moment: _dt.datetime | None,
        weather_index: int | None,
    ) -> None:
        """Wartości przykładowe używane przez płótno (losowe lub własne)."""
        self.samples = samples
        self.moment_override = moment
        self.weather_index = weather_index
        self.update()

    def refresh(self) -> None:
        self.update()

    def selected_element(self) -> Element | None:
        if self.project is None or not self.selected_id:
            return None
        for el in self.project.elements:
            if el.id == self.selected_id:
                return el
        return None

    def select(self, element_id: str | None) -> None:
        self.selected_id = element_id
        el = self.selected_element()
        self.selectionChanged.emit(el)
        self.update()

    def set_grid(self, enabled: bool) -> None:
        self.show_grid = bool(enabled)
        self.update()

    def set_snap(self, enabled: bool) -> None:
        self.snap = bool(enabled)

    def set_live(self, enabled: bool) -> None:
        self.live = bool(enabled)
        self.update()

    def _layout(self) -> tuple[QPointF, float]:
        margin = 26.0
        width = max(1.0, self.width() - margin * 2)
        height = max(1.0, self.height() - margin * 2)
        size = min(width, height)
        scale = size / C.DEVICE["width"]
        origin = QPointF(
            (self.width() - C.DEVICE["width"] * scale) / 2,
            (self.height() - C.DEVICE["height"] * scale) / 2,
        )
        return origin, scale

    def _screen_rect(self, el: Element) -> QRectF:
        origin, scale = self._layout()
        return QRectF(
            origin.x() + el.x * scale,
            origin.y() + el.y * scale,
            el.w * scale,
            el.h * scale,
        )

    def _design_point(self, pos: QPointF) -> QPointF:
        origin, scale = self._layout()
        return QPointF((pos.x() - origin.x()) / scale, (pos.y() - origin.y()) / scale)

    def _handle_rects(self, rect: QRectF) -> dict[str, QRectF]:
        half = HANDLE / 2
        cx = rect.center().x()
        cy = rect.center().y()
        points = {
            "nw": QPointF(rect.left(), rect.top()),
            "n": QPointF(cx, rect.top()),
            "ne": QPointF(rect.right(), rect.top()),
            "e": QPointF(rect.right(), cy),
            "se": QPointF(rect.right(), rect.bottom()),
            "s": QPointF(cx, rect.bottom()),
            "sw": QPointF(rect.left(), rect.bottom()),
            "w": QPointF(rect.left(), cy),
        }
        return {key: QRectF(p.x() - half, p.y() - half, HANDLE, HANDLE) for key, p in points.items()}

    def _hit_handle(self, pos: QPointF) -> str | None:
        el = self.selected_element()
        if el is None:
            return None
        for key, rect in self._handle_rects(self._screen_rect(el)).items():
            if rect.contains(pos):
                return key
        return None

    def _rotation_center_screen(self, el: Element) -> QPointF:
        origin, scale = self._layout()
        center_x, center_y = rotation_center(el)
        return QPointF(origin.x() + center_x * scale, origin.y() + center_y * scale)

    def _rotate_handle_pos(self, el: Element) -> QPointF:
        rect = self._screen_rect(el)
        offset = ROTATE_GAP * 0.7071067811865476
        return QPointF(rect.right() + offset, rect.top() - offset)

    def _hit_rotate(self, pos: QPointF) -> bool:
        el = self.selected_element()
        if el is None or el.locked or not supports_rotation(el.type):
            return False
        point = self._rotate_handle_pos(el)
        dx = pos.x() - point.x()
        dy = pos.y() - point.y()
        return (dx * dx + dy * dy) ** 0.5 <= ROTATE_DOT / 2 + 3

    def _pointer_angle(self, pos: QPointF, center: QPointF) -> float:
        """Kąt kursora w stopniach; 0° = godzina 12, dodatni zgodnie z zegarem."""
        return math.degrees(math.atan2(pos.y() - center.y(), pos.x() - center.x())) + 90.0

    def _hit_element(self, pos: QPointF) -> Element | None:
        if self.project is None:
            return None
        point = self._design_point(pos)
        for el in reversed(self.project.elements):
            if not el.visible:
                continue
            local = self._unrotate_point(el, point)
            if QRectF(el.x, el.y, el.w, el.h).contains(local):
                return el
        return None

    def _unrotate_point(self, el: Element, point: QPointF) -> QPointF:
        """Punkt w układzie elementu (odwrotny obrót) - trafianie w obróconą treść."""
        angle = int(el.rotation or 0)
        if not angle or not supports_rotation(el.type):
            return point
        center_x, center_y = rotation_center(el)
        radians = math.radians(-angle)
        cos_a = math.cos(radians)
        sin_a = math.sin(radians)
        dx = point.x() - center_x
        dy = point.y() - center_y
        return QPointF(
            center_x + dx * cos_a - dy * sin_a,
            center_y + dx * sin_a + dy * cos_a,
        )

    def _ring_values(self, el: Element) -> tuple[int, int]:
        line_width = max(1, int(el.props.get("line_width", 8) or 8))
        radius = int(el.props.get("radius", 0) or 0)
        if radius <= 0:
            radius = int(min(el.w, el.h) / 2 - line_width / 2)
        return max(1, radius), line_width

    def _ring_dot_centers(self, el: Element) -> dict[str, QPointF]:
        """Środek pierścienia (przeciąganie = promień) i punkt na łuku (grubość)."""
        rect = self._screen_rect(el)
        center = rect.center()
        radius, _width = self._ring_values(el)
        offset = radius * self._scale * 0.7071067811865476
        return {
            "radius": center,
            "width": QPointF(center.x() + offset, center.y() + offset),
        }

    def _hit_ring_dot(self, pos: QPointF) -> str | None:
        el = self.selected_element()
        if el is None or el.type != "progress_ring" or el.locked or not el.visible:
            return None
        for key, point in self._ring_dot_centers(el).items():
            dx = pos.x() - point.x()
            dy = pos.y() - point.y()
            if (dx * dx + dy * dy) ** 0.5 <= RING_DOT / 2 + 2:
                return key
        return None

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#0a0d13"))

        if self.project is None:
            painter.end()
            return

        origin, scale = self._layout()
        self._origin = origin
        self._scale = scale
        if abs(scale - self._last_zoom) > 0.0001:
            self._last_zoom = scale
            self.zoomChanged.emit(scale)

        target = QRectF(
            origin.x(),
            origin.y(),
            C.DEVICE["width"] * scale,
            C.DEVICE["height"] * scale,
        )

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 160))
        painter.drawEllipse(target.adjusted(-9, -9, 9, 9))
        painter.setBrush(QColor("#1a2130"))
        painter.setPen(QPen(QColor("#2b374b"), 1))
        painter.drawEllipse(target.adjusted(-5, -5, 5, 5))

        render_project(
            painter,
            self.project,
            target,
            live=self.live,
            preview=False,
            clip_circle=True,
            now=self.moment_override,
            samples=self.samples,
            weather_index=self.weather_index,
        )

        circle = QPainterPath()
        circle.addEllipse(target)
        painter.save()
        painter.setClipPath(circle)
        if self.show_grid:
            self._paint_grid(painter, target, scale)
        painter.restore()

        painter.setPen(QPen(QColor(255, 255, 255, 40), 1, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        inset = C.SAFE_MARGIN * scale
        painter.drawEllipse(target.adjusted(inset, inset, -inset, -inset))

        selected = self.selected_element()
        if selected is not None and selected.visible:
            rect = self._screen_rect(selected)
            if selected.scale_content and supports_content_scale(selected.type):
                color = QColor("#ff3b30")
            elif selected.locked:
                color = QColor("#ffbf47")
            else:
                color = QColor("#4dd2ff")
            painter.setPen(QPen(color, 1.4, Qt.DashLine))
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 22))
            painter.drawRect(rect)
            if not selected.locked:
                painter.setPen(QPen(QColor("#0a0d13"), 1))
                painter.setBrush(color)
                for handle in self._handle_rects(rect).values():
                    painter.drawRect(handle)
                if selected.type == "progress_ring":
                    self._paint_ring_dots(painter, selected)
                if supports_rotation(selected.type):
                    self._paint_rotate_handle(painter, selected, color)
        elif self.hover_id:
            hover = next((el for el in self.project.elements if el.id == self.hover_id), None)
            if hover is not None and hover.visible:
                painter.setPen(QPen(QColor(120, 200, 255, 120), 1, Qt.DotLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(self._screen_rect(hover))

        if self._drag is not None and self._snap_guides:
            painter.save()
            painter.setPen(QPen(QColor("#ff4d6d"), 1.2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            for orientation, coordinate in self._snap_guides:
                if orientation == "v":
                    x = origin.x() + coordinate * scale
                    painter.drawLine(QPointF(x, target.top()), QPointF(x, target.bottom()))
                else:
                    y = origin.y() + coordinate * scale
                    painter.drawLine(QPointF(target.left(), y), QPointF(target.right(), y))
            painter.restore()

        painter.end()

    def _paint_grid(self, painter: QPainter, target: QRectF, scale: float) -> None:
        step = C.GRID_STEP * scale
        if step < 6:
            return
        minor = QPen(QColor(255, 255, 255, 14), 1)
        major = QPen(QColor(120, 200, 255, 40), 1)
        painter.setPen(minor)
        for i in range(1, int(C.DEVICE["width"] / C.GRID_STEP)):
            value = i * C.GRID_STEP
            painter.setPen(major if value % 50 == 0 else minor)
            x = target.x() + value * scale
            painter.drawLine(QPointF(x, target.top()), QPointF(x, target.bottom()))
            y = target.y() + value * scale
            painter.drawLine(QPointF(target.left(), y), QPointF(target.right(), y))

    def _paint_rotate_handle(
        self, painter: QPainter, el: Element, color: QColor
    ) -> None:
        rect = self._screen_rect(el)
        top = rect.topRight()
        point = self._rotate_handle_pos(el)
        painter.setPen(QPen(color, 1.2, Qt.DashLine))
        painter.drawLine(top, point)
        painter.setPen(QPen(QColor("#0a0d13"), 1.5))
        painter.setBrush(color)
        painter.drawEllipse(point, ROTATE_DOT / 2, ROTATE_DOT / 2)
        # Mały łuk w kółku - czytelny symbol obrotu.
        painter.setPen(QPen(QColor("#0a0d13"), 1.4))
        painter.setBrush(Qt.NoBrush)
        arc = QRectF(point.x() - 3.0, point.y() - 3.0, 6.0, 6.0)
        painter.drawArc(arc, 40 * 16, 280 * 16)
        if int(el.rotation or 0):
            painter.setPen(QPen(QColor(220, 235, 255, 200), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawText(
                QRectF(point.x() + 9, point.y() - 8, 52, 16),
                int(Qt.AlignLeft | Qt.AlignVCenter),
                f"{int(el.rotation)}°",
            )

    def _paint_ring_dots(self, painter: QPainter, el: Element) -> None:
        points = self._ring_dot_centers(el)
        for key, point in points.items():
            color = QColor("#4dd2ff") if key == "radius" else QColor("#ffbf47")
            painter.setPen(QPen(QColor("#0a0d13"), 1.5))
            painter.setBrush(color)
            painter.drawEllipse(point, RING_DOT / 2, RING_DOT / 2)
            painter.setPen(QPen(QColor("#0a0d13"), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(point, RING_DOT / 2 - 3.0, RING_DOT / 2 - 3.0)

    def mousePressEvent(self, event) -> None:
        if self.project is None or event.button() != Qt.LeftButton:
            return
        self.setFocus()
        pos = event.position()
        el = self.selected_element()
        if el is not None and self._hit_rotate(pos):
            center = self._rotation_center_screen(el)
            self._drag = {
                "mode": "rotate",
                "start": pos,
                "start_pointer": self._pointer_angle(pos, center),
                "value": int(el.rotation or 0),
                "id": el.id,
            }
            self.setCursor(Qt.CrossCursor)
            return
        ring_dot = self._hit_ring_dot(pos)
        if ring_dot and el is not None and not el.locked:
            radius, line_width = self._ring_values(el)
            self._drag = {
                "mode": "ring_radius" if ring_dot == "radius" else "ring_width",
                "start": pos,
                "value": radius if ring_dot == "radius" else line_width,
                "id": el.id,
            }
            self.setCursor(Qt.SizeHorCursor)
            return
        handle = self._hit_handle(pos)
        if handle and el is not None and not el.locked:
            self._drag = {
                "mode": "resize",
                "handle": handle,
                "start": pos,
                "rect": (el.x, el.y, el.w, el.h),
                "scale_content": bool(el.scale_content),
                "id": el.id,
            }
            self.setCursor(self._cursor_for_handle(handle))
            return
        hit = self._hit_element(pos)
        if hit is not None and hit.id != self.selected_id:
            self.select(hit.id)
            el = hit
        if hit is not None and not hit.locked:
            self._drag = {
                "mode": "move",
                "start": pos,
                "rect": (hit.x, hit.y, hit.w, hit.h),
                "id": hit.id,
            }
            self.setCursor(Qt.ClosedHandCursor)
        elif hit is None:
            self.select(None)

    def mouseMoveEvent(self, event) -> None:
        if self.project is None:
            return
        pos = event.position()
        point = self._design_point(pos)
        self.positionChanged.emit(round(point.x()), round(point.y()))

        if self._drag is not None:
            self._apply_drag(pos, bool(event.modifiers() & Qt.ControlModifier), event.modifiers())
            return

        if self._hit_rotate(pos):
            if self.hover_id is not None:
                self.hover_id = None
                self.update()
            self.setCursor(Qt.CrossCursor)
            return
        ring_dot = self._hit_ring_dot(pos)
        if ring_dot:
            if self.hover_id is not None:
                self.hover_id = None
                self.update()
            self.setCursor(Qt.SizeHorCursor)
            return
        handle = self._hit_handle(pos)
        if handle:
            self.setCursor(self._cursor_for_handle(handle))
        else:
            el = self._hit_element(pos)
            new_hover = el.id if el is not None else None
            if new_hover != self.hover_id:
                self.hover_id = new_hover
                self.update()
            self.setCursor(Qt.OpenHandCursor if el is not None and not el.locked else Qt.ArrowCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        if self._drag is not None:
            self._drag = None
            self._snap_guides = []
            self.setCursor(Qt.ArrowCursor)
            self.editFinished.emit()
        self.update()

    def leaveEvent(self, event) -> None:
        self.positionChanged.emit(-1, -1)
        if self.hover_id is not None:
            self.hover_id = None
            self.update()

    def keyPressEvent(self, event) -> None:
        el = self.selected_element()
        if el is None or el.locked:
            super().keyPressEvent(event)
            return
        step = 10 if event.modifiers() & Qt.ShiftModifier else 1
        dx = dy = 0
        if event.key() == Qt.Key_Left:
            dx = -step
        elif event.key() == Qt.Key_Right:
            dx = step
        elif event.key() == Qt.Key_Up:
            dy = -step
        elif event.key() == Qt.Key_Down:
            dy = step
        elif event.key() == Qt.Key_Delete:
            self.deleteRequested.emit()
            return
        else:
            super().keyPressEvent(event)
            return
        el.x = max(0, min(C.DEVICE["width"] - el.w, el.x + dx))
        el.y = max(0, min(C.DEVICE["height"] - el.h, el.y + dy))
        self.liveChanged.emit()
        self.editFinished.emit()
        self.update()

    def _apply_drag(self, pos: QPointF, no_snap: bool, modifiers=Qt.NoModifier) -> None:
        if self._drag is None or self.project is None:
            return
        el = self.selected_element()
        if el is None:
            return
        _origin, scale = self._layout()
        start = self._drag["start"]
        dx = (pos.x() - start.x()) / scale
        dy = (pos.y() - start.y()) / scale
        mode = self._drag["mode"]

        if mode == "rotate":
            center = self._rotation_center_screen(el)
            pointer = self._pointer_angle(pos, center)
            value = float(self._drag.get("value", 0)) + (pointer - self._drag["start_pointer"])
            if modifiers & Qt.ShiftModifier:
                value = round(value / 15.0) * 15.0
            angle = normalize_rotation(value)
            el.rotation = angle
            self.statusMessage.emit(f"Obrót: {angle}°")
            self.liveChanged.emit()
            self.update()
            return

        if mode in ("ring_radius", "ring_width"):
            value = float(self._drag.get("value", 0)) + dx
            if mode == "ring_radius":
                radius = max(0, min(233, round(value)))
                el.props["radius"] = radius
                self.statusMessage.emit(f"Promień pierścienia: {radius} px")
            else:
                width = max(1, min(60, round(value)))
                el.props["line_width"] = width
                self.statusMessage.emit(f"Grubość pierścienia: {width} px")
            self.liveChanged.emit()
            self.update()
            return

        rx, ry, rw, rh = self._drag["rect"]
        snap = self.snap and not no_snap

        if mode == "move":
            x = rx + dx
            y = ry + dy
            x = max(0, min(C.DEVICE["width"] - rw, x))
            y = max(0, min(C.DEVICE["height"] - rh, y))
            guides: list[tuple[str, float]] = []
            snapped_x = False
            snapped_y = False
            if snap:
                threshold = 8.0
                x_options: list[tuple[float, float, float]] = []
                x_options.append((abs(x - (C.DEVICE["width"] / 2 - rw / 2)), C.DEVICE["width"] / 2 - rw / 2, C.DEVICE["width"] / 2))
                for other in self.project.elements:
                    if other.id == el.id or not other.visible:
                        continue
                    for guide_coord, candidate in (
                        (other.x, other.x),
                        (other.x + other.w, other.x + other.w - rw),
                        (other.x + other.w / 2, other.x + other.w / 2 - rw / 2),
                    ):
                        x_options.append((abs(x - candidate), candidate, guide_coord))
                best_x = min(x_options, key=lambda item: item[0])
                if best_x[0] <= threshold:
                    x = best_x[1]
                    guides.append(("v", best_x[2]))
                    snapped_x = True

                y_options: list[tuple[float, float, float]] = []
                y_options.append((abs(y - (C.DEVICE["height"] / 2 - rh / 2)), C.DEVICE["height"] / 2 - rh / 2, C.DEVICE["height"] / 2))
                for other in self.project.elements:
                    if other.id == el.id or not other.visible:
                        continue
                    for guide_coord, candidate in (
                        (other.y, other.y),
                        (other.y + other.h, other.y + other.h - rh),
                        (other.y + other.h / 2, other.y + other.h / 2 - rh / 2),
                    ):
                        y_options.append((abs(y - candidate), candidate, guide_coord))
                best_y = min(y_options, key=lambda item: item[0])
                if best_y[0] <= threshold:
                    y = best_y[1]
                    guides.append(("h", best_y[2]))
                    snapped_y = True

                if not snapped_x:
                    x = self._round_to(x, C.GRID_STEP)
                if not snapped_y:
                    y = self._round_to(y, C.GRID_STEP)
            self._snap_guides = guides
            el.x = round(x)
            el.y = round(y)
        else:
            handle = self._drag["handle"]
            x, y, w, h = rx, ry, rw, rh
            if "w" in handle:
                x = rx + dx
                w = rw - dx
            if "e" in handle:
                w = rw + dx
            if "n" in handle:
                y = ry + dy
                h = rh - dy
            if "s" in handle:
                h = rh + dy
            if w < MIN_SIZE:
                if "w" in handle:
                    x = rx + rw - MIN_SIZE
                w = MIN_SIZE
            if h < MIN_SIZE:
                if "n" in handle:
                    y = ry + rh - MIN_SIZE
                h = MIN_SIZE
            if snap:
                x = self._round_to(x, C.GRID_STEP)
                y = self._round_to(y, C.GRID_STEP)
                w = max(MIN_SIZE, self._round_to(w, C.GRID_STEP))
                h = max(MIN_SIZE, self._round_to(h, C.GRID_STEP))
            if self._drag.get("scale_content"):
                apply_content_scale(el, round(w), round(h))
            else:
                el.freeze_content_size()
            el.x = round(x)
            el.y = round(y)
            el.w = round(w)
            el.h = round(h)
        self.liveChanged.emit()
        self.update()

    @staticmethod
    def _round_to(value: float, step: int) -> float:
        return round(value / step) * step

    @staticmethod
    def _cursor_for_handle(handle: str) -> Qt.CursorShape:
        if handle in ("nw", "se"):
            return Qt.SizeFDiagCursor
        if handle in ("ne", "sw"):
            return Qt.SizeBDiagCursor
        if handle in ("n", "s"):
            return Qt.SizeVerCursor
        return Qt.SizeHorCursor

    def contextMenuEvent(self, event) -> None:
        if self.project is None:
            return
        el = self.selected_element()
        if el is None:
            return
        menu = QMenu(self)
        duplicate = menu.addAction("Duplikuj")
        delete = menu.addAction("Usuń")
        menu.addSeparator()
        center_menu = menu.addMenu("Wyśrodkuj na tarczy")
        center_h = center_menu.addAction("W poziomie")
        center_v = center_menu.addAction("W pionie")
        center_both = center_menu.addAction("W obu osiach")
        reset_rotation = None
        if supports_rotation(el.type):
            reset_rotation = menu.addAction("Obrót 0°")
        menu.addSeparator()
        front = menu.addAction("Na wierzch")
        back = menu.addAction("Na spód")
        menu.addSeparator()
        lock = menu.addAction("Odblokuj" if el.locked else "Zablokuj")
        chosen = menu.exec(event.globalPos())
        if chosen is None:
            return
        if chosen == duplicate:
            clone = el.clone()
            self.project.elements.append(clone)
            self.select(clone.id)
        elif chosen == delete:
            self.project.elements = [item for item in self.project.elements if item.id != el.id]
            self.select(None)
        elif chosen in (center_h, center_v, center_both):
            center_element(
                el,
                horizontal=chosen in (center_h, center_both),
                vertical=chosen in (center_v, center_both),
            )
            self.statusMessage.emit("Wyśrodkowano element")
        elif reset_rotation is not None and chosen == reset_rotation:
            el.rotation = 0
            self.statusMessage.emit("Obrót: 0°")
        elif chosen == front:
            self.project.elements.remove(el)
            self.project.elements.append(el)
        elif chosen == back:
            self.project.elements.remove(el)
            self.project.elements.insert(0, el)
        elif chosen == lock:
            el.locked = not el.locked
        self.liveChanged.emit()
        self.editFinished.emit()
        self.update()

    def current_time(self) -> _dt.datetime:
        return _dt.datetime.now() if self.live else _dt.datetime(2026, 8, 2, 10, 9, 36)
