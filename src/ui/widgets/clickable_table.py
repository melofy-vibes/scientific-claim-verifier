"""Clickable QTableWidget that emits signals on cell click."""
from PyQt5.QtWidgets import QTableWidget
from PyQt5.QtCore import pyqtSignal


class ClickableTableWidget(QTableWidget):
    """Table widget that emits a signal when a cell is clicked."""
    cell_clicked = pyqtSignal(int, int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cellClicked.connect(self._on_cell_clicked)

    def _on_cell_clicked(self, row, col):
        self.cell_clicked.emit(row, col)