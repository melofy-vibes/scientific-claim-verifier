"""Factory functions for building UI components."""
import logging
from PyQt5.QtWidgets import (
    QToolBar, QHBoxLayout, QVBoxLayout, QWidget, QLineEdit, QPushButton,
    QLabel, QTabWidget, QTextBrowser, QTableWidgetItem, QHeaderView,
    QSizePolicy, QAction, QSpacerItem,
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor, QBrush

from src.ui.theme.fonts import Fonts
from src.ui.theme.colors import label_color
from src.ui.widgets.clickable_table import ClickableTableWidget

logger = logging.getLogger(__name__)


def create_top_toolbar(parent, theme_action, lang_action) -> QToolBar:
    """Create the top toolbar with fixed button positions."""
    toolbar = QToolBar("Main Toolbar")
    toolbar.setMovable(False)
    toolbar.setIconSize(QSize(18, 18))
    toolbar.setLayoutDirection(Qt.LeftToRight)
    parent.addToolBar(toolbar)

    toolbar.addAction(theme_action)

    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    toolbar.addWidget(spacer)

    toolbar.addAction(lang_action)
    return toolbar


def create_input_row(claim_input: QLineEdit, run_btn: QPushButton) -> QHBoxLayout:
    """Create the claim input row with Verify button."""
    layout = QHBoxLayout()
    layout.setSpacing(10)
    layout.addWidget(claim_input)
    layout.addWidget(run_btn)
    return layout


def create_status_label() -> QLabel:
    """Create the status indicator label."""
    label = QLabel()
    label.setObjectName("statusLabel")
    return label


def create_tabs(report_tab: QTextBrowser, evidence_table: 'ClickableTableWidget',
                supporting_table: 'ClickableTableWidget',
                contradicting_table: 'ClickableTableWidget') -> QTabWidget:
    """Create the tab widget with Report, Evidence, Supporting, Contradicting tabs."""
    tabs = QTabWidget()
    tabs.addTab(report_tab, "📋 Report")
    tabs.addTab(evidence_table, "📊 Evidence")
    tabs.addTab(supporting_table, "✅ Supporting")
    tabs.addTab(contradicting_table, "❌ Contradicting")
    return tabs


def create_bottom_bar(clear_btn: QPushButton, export_btn: QPushButton) -> QWidget:
    """Create the bottom bar with Clear and Export PDF buttons, always on the right."""
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 8, 0, 0)
    layout.setSpacing(10)
    layout.addStretch()
    layout.addWidget(clear_btn)
    layout.addWidget(export_btn)
    return widget


def create_table(headers: list, clickable: bool = False) -> 'ClickableTableWidget':
    """Reusable factory for all tables in the app."""
    table = ClickableTableWidget() if clickable else ClickableTableWidget()
    # For non-clickable tables, just use a regular QTableWidget
    if not clickable:
        from PyQt5.QtWidgets import QTableWidget
        table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.verticalHeader().setDefaultSectionSize(36)
    table.setAlternatingRowColors(True)
    table.setFont(QFont(Fonts.FAMILY, Fonts.TABLE_PT))
    return table


def populate_evidence_table(table, items: list, palette: dict,
                            col_paper: int, col_year: int, col_label: int,
                            col_confidence: int, col_link: int, loc_getter) -> None:
    """Fill the Evidence tab, sorted by paper year (most recent first)."""
    sorted_items = sorted(
        items, key=lambda x: (x["paper"].year is not None, x["paper"].year or 0), reverse=True
    )
    table.setRowCount(0)
    table.setRowCount(len(sorted_items))
    for row, evidence in enumerate(sorted_items):
        set_evidence_row(table, row, evidence, palette,
                        col_paper, col_year, col_label, col_confidence, col_link, loc_getter)


def set_evidence_row(table, row: int, evidence: dict, palette: dict,
                     col_paper: int, col_year: int, col_label: int,
                     col_confidence: int, col_link: int, loc_getter) -> None:
    """Populate a single row of the evidence table."""
    paper = evidence["paper"]

    title_text = paper.title
    if evidence.get("total_sentences_from_paper", 1) > 1:
        title_text += f" [{evidence['total_sentences_from_paper']} sentences]"
    title_item = QTableWidgetItem(title_text)
    title_item.setToolTip(paper.title)
    table.setItem(row, col_paper, title_item)

    year_item = QTableWidgetItem(str(paper.year) if paper.year else "N/A")
    year_item.setTextAlignment(Qt.AlignCenter)
    table.setItem(row, col_year, year_item)

    label = evidence["nli_label"]
    label_item = QTableWidgetItem(label)
    label_item.setTextAlignment(Qt.AlignCenter)
    all_labels = evidence.get("all_labels", [label])
    if len(all_labels) > 1:
        label_item.setToolTip(f"Paper contains multiple stances: {', '.join(all_labels)}")
        label_item.setText(f"{label} *")
    else:
        label_item.setToolTip(f"All evidence from this paper is {label}")
    label_item.setForeground(QBrush(QColor(label_color(label, palette))))
    table.setItem(row, col_label, label_item)

    conf_item = QTableWidgetItem(f"{evidence['nli_confidence']:.2f}")
    conf_item.setTextAlignment(Qt.AlignCenter)
    table.setItem(row, col_confidence, conf_item)

    link_label = loc_getter("open_paper", "🔗 Open Paper")
    link_item = QTableWidgetItem(link_label if paper.url else loc_getter("no_link"))
    link_item.setTextAlignment(Qt.AlignCenter)
    if paper.url:
        link_item.setToolTip(paper.url)
        link_item.setData(Qt.UserRole, paper.url)
        link_item.setForeground(QBrush(QColor(palette["primary"])))
    else:
        link_item.setToolTip("No link available")
    table.setItem(row, col_link, link_item)


def populate_simple_table(table, items: list) -> None:
    """Fill the Supporting/Contradicting tabs."""
    table.setRowCount(0)
    table.setRowCount(len(items))
    for row, evidence in enumerate(items):
        paper = evidence["paper"]
        title_item = QTableWidgetItem(paper.title)
        title_item.setToolTip(paper.title)
        table.setItem(row, 0, title_item)
        table.setItem(row, 1, QTableWidgetItem(evidence["sentence"]))
        conf_item = QTableWidgetItem(f"{evidence['nli_confidence']:.2f}")
        conf_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, 2, conf_item)


def recolor_evidence_table(table, palette: dict,
                           col_label: int, col_link: int) -> None:
    """Recolor label/link text in the evidence table after a theme switch."""
    for row in range(table.rowCount()):
        label_item = table.item(row, col_label)
        if label_item:
            base_label = label_item.text().rstrip(" *")
            label_item.setForeground(QBrush(QColor(label_color(base_label, palette))))
        link_item = table.item(row, col_link)
        if link_item and link_item.data(Qt.UserRole):
            link_item.setForeground(QBrush(QColor(palette["primary"])))