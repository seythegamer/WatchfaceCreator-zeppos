from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..model import TYPE_LABELS, Project


class LayersPanel(QWidget):
    selected = Signal(object)
    changed = Signal()
    actionRequested = Signal(str)
    statusMessage = Signal(str)

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self._refreshing = False
        self._current_id: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setAlternatingRowColors(False)
        self.list.setToolTip("Przeciągaj, aby zmienić kolejność rysowania (góra = na wierzchu)")
        self.list.currentItemChanged.connect(self._on_current)
        self.list.itemChanged.connect(self._on_item_changed)
        self.list.model().rowsMoved.connect(lambda *_: self._on_rows_moved())
        layout.addWidget(self.list, 1)

        row = QHBoxLayout()
        row.setSpacing(4)
        for label, action, tip in (
            ("W górę", "up", "Przenieś wyżej"),
            ("W dół", "down", "Przenieś niżej"),
            ("Duplikuj", "duplicate", "Duplikuj element"),
            ("Usuń", "delete", "Usuń element"),
        ):
            button = QPushButton(label)
            button.setToolTip(tip)
            button.clicked.connect(lambda _=False, a=action: self.actionRequested.emit(a))
            if action == "delete":
                button.setObjectName("danger")
            row.addWidget(button)
        layout.addLayout(row)
        self.refresh()

    def set_project(self, project: Project) -> None:
        self.project = project
        self._current_id = None
        self.refresh()

    def set_selected(self, element_id: str | None) -> None:
        if element_id == self._current_id:
            return
        self._current_id = element_id
        self._refreshing = True
        self.list.clearSelection()
        for row in range(self.list.count()):
            item = self.list.item(row)
            if item.data(Qt.UserRole) == element_id:
                item.setSelected(True)
                self.list.setCurrentRow(row)
                break
        self._refreshing = False

    def refresh(self) -> None:
        self._refreshing = True
        self.list.clear()
        for el in reversed(self.project.elements):
            item = QListWidgetItem(el.name)
            item.setData(Qt.UserRole, el.id)
            item.setFlags(
                Qt.ItemIsEnabled
                | Qt.ItemIsSelectable
                | Qt.ItemIsUserCheckable
                | Qt.ItemIsDragEnabled
            )
            item.setCheckState(Qt.Checked if el.visible else Qt.Unchecked)
            tooltip = TYPE_LABELS.get(el.type, el.type)
            if el.locked:
                tooltip += " (zablokowany)"
            item.setToolTip(tooltip)
            if not el.visible:
                item.setForeground(Qt.gray)
            elif el.locked:
                item.setForeground(Qt.darkYellow)
            self.list.addItem(item)
            if el.id == self._current_id:
                item.setSelected(True)
                self.list.setCurrentItem(item)
        self._refreshing = False

    def _on_current(self, current: QListWidgetItem | None, _previous=None) -> None:
        if self._refreshing:
            return
        element_id = current.data(Qt.UserRole) if current is not None else None
        self._current_id = element_id
        self.selected.emit(element_id)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        if self._refreshing:
            return
        element = self._element(item.data(Qt.UserRole))
        if element is None:
            return
        visible = item.checkState() == Qt.Checked
        if element.visible != visible:
            element.visible = visible
            item.setForeground(Qt.gray if not visible else (Qt.darkYellow if element.locked else Qt.white))
            self.changed.emit()

    def _on_rows_moved(self) -> None:
        if self._refreshing:
            return
        ids = [self.list.item(row).data(Qt.UserRole) for row in range(self.list.count())]
        lookup = {el.id: el for el in self.project.elements}
        reordered = [lookup[element_id] for element_id in reversed(ids) if element_id in lookup]
        if len(reordered) == len(self.project.elements):
            self.project.elements = reordered
            self.changed.emit()

    def _element(self, element_id: str | None):
        if not element_id:
            return None
        for el in self.project.elements:
            if el.id == element_id:
                return el
        return None

    def move_selected(self, direction: int) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        row = self.list.row(item)
        target = row + direction
        if target < 0 or target >= self.list.count():
            return
        self._refreshing = True
        self.list.takeItem(row)
        self.list.insertItem(target, item)
        self.list.setCurrentItem(item)
        item.setSelected(True)
        self._refreshing = False
        self._on_rows_moved()
        self.statusMessage.emit("Zmieniono kolejność warstw")

