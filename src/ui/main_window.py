"""MainWindow — orchestrates the Scientific Claim Verifier desktop application."""

from src.main import ClaimVerificationPipeline
from src.translation.localization import LocalizationManager
from src.translation.language_detector import detect_language

import logging
import webbrowser

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLineEdit, QPushButton, QTextBrowser, QAction, QApplication,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from src.ui.theme import Fonts, THEMES, STATUS_ICONS
from src.ui.theme.stylesheet import build_stylesheet, build_report_stylesheet
from src.ui.widgets.clickable_table import ClickableTableWidget
from src.ui.threads.verification_thread import VerificationThread
from src.ui.report.renderer import ReportRenderer
from src.ui.report.pdf_export import export_pdf
from src.ui.builders.ui_builders import (
    create_top_toolbar, create_input_row, create_status_label,
    create_tabs, create_bottom_bar, create_table,
    populate_evidence_table, populate_simple_table, recolor_evidence_table,
)
from src.ui.builders.localization import UILocalizer

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Scientific Claim Verifier & Evidence Explorer — main application window."""

    COL_PAPER, COL_YEAR, COL_LABEL, COL_CONFIDENCE, COL_LINK = range(5)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scientific Claim Verifier & Evidence Explorer")
        self.setGeometry(100, 100, 1280, 840)

        self.pipeline = ClaimVerificationPipeline()
        self.current_result = None
        self.dark_mode = True
        self.thread = None
        self.current_lang = "en"

        self.loc = LocalizationManager()
        self.loc.load_language("en")
        self.localizer = UILocalizer(self)

        QApplication.setFont(QFont(Fonts.FAMILY, Fonts.UI_PT))

        self._build_ui()
        self._init_report_renderer()
        self.apply_theme()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Build all widgets and layouts."""
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 12, 16, 16)
        main_layout.setSpacing(12)

        # Create widgets
        self.theme_action = QAction("☀️ Light Mode", self)
        self.lang_action = QAction("فارسی", self)
        self.claim_input = QLineEdit()
        self.run_btn = QPushButton("🔍 Verify")
        self.report_tab = QTextBrowser()
        self.evidence_table = create_table(
            ["Paper", "Year", "Label", "Confidence", "Link"], clickable=True,
        )
        self.supporting_table = create_table(["Paper", "Sentence", "Confidence"])
        self.contradicting_table = create_table(["Paper", "Sentence", "Confidence"])
        self.clear_btn = QPushButton("🗑 Clear")
        self.export_btn = QPushButton("📄 Export PDF")

        # Configure widgets
        self.theme_action.triggered.connect(self.toggle_theme)
        self.lang_action.triggered.connect(self.toggle_language)

        self.claim_input.setPlaceholderText("Enter a scientific claim...")
        self.claim_input.setMinimumHeight(40)
        self.claim_input.returnPressed.connect(self.start_verification)

        self.run_btn.setMinimumHeight(40)
        self.run_btn.setMinimumWidth(120)
        self.run_btn.clicked.connect(self.start_verification)

        self.report_tab.setOpenExternalLinks(True)
        self.report_tab.setFont(QFont(Fonts.FAMILY, 12))

        self.evidence_table.cell_clicked.connect(self._on_evidence_link_clicked)

        self.clear_btn.setMinimumHeight(36)
        self.clear_btn.clicked.connect(self.clear_results)

        self.export_btn.setMinimumHeight(36)
        self.export_btn.clicked.connect(self._export_pdf)

        self.status_label = create_status_label()

        # Assemble layout
        self.toolbar = create_top_toolbar(self, self.theme_action, self.lang_action)
        main_layout.addLayout(create_input_row(self.claim_input, self.run_btn))
        main_layout.addWidget(self.status_label)
        self.tabs = create_tabs(
            self.report_tab, self.evidence_table,
            self.supporting_table, self.contradicting_table,
        )
        main_layout.addWidget(self.tabs)
        main_layout.addWidget(create_bottom_bar(self.clear_btn, self.export_btn))

        self.localizer.retranslate_ui(self.loc)

    def _init_report_renderer(self):
        """Initialize the report renderer with palette and RTL getters."""
        self._renderer = ReportRenderer(
            palette_getter=lambda: THEMES["dark" if self.dark_mode else "light"],
            is_rtl_getter=lambda: self.current_lang == "fa",
        )

    # ------------------------------------------------------------------
    # Button state management
    # ------------------------------------------------------------------

    def _set_all_buttons_enabled(self, enabled: bool):
        """Enable or disable all interactive buttons during processing."""
        self.run_btn.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
        self.export_btn.setEnabled(enabled)
        self.theme_action.setEnabled(enabled)
        self.lang_action.setEnabled(enabled)
        self.claim_input.setEnabled(enabled)
        
        # Force UI update
        QApplication.processEvents()

    # ------------------------------------------------------------------
    # Localization
    # ------------------------------------------------------------------

    def toggle_language(self):
        """Toggle between English and Persian."""
        new_lang = "fa" if self.current_lang == "en" else "en"
        self.switch_language(new_lang)

    def switch_language(self, lang: str):
        """Switch UI language."""
        if lang == self.current_lang:
            return
        self.current_lang = lang
        self.loc.load_language(lang)
        self.localizer.retranslate_ui(self.loc)

        if lang == "fa":
            self.centralWidget().setLayoutDirection(Qt.RightToLeft)
        else:
            self.centralWidget().setLayoutDirection(Qt.LeftToRight)

        if self.current_result is not None and "report" in self.current_result:
            self._render_report(self.current_result["report"])

    # ------------------------------------------------------------------
    # Theming
    # ------------------------------------------------------------------

    @property
    def palette(self) -> dict:
        return THEMES["dark" if self.dark_mode else "light"]

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        if self.dark_mode:
            self.theme_action.setText(self.loc.get("light_mode"))
        else:
            self.theme_action.setText(self.loc.get("dark_mode"))

    def apply_theme(self):
        palette = self.palette
        self.setStyleSheet(build_stylesheet(palette))
        self.report_tab.setStyleSheet(build_report_stylesheet(palette))

        if self.current_result is not None and "report" in self.current_result:
            self._render_report(self.current_result["report"])
            recolor_evidence_table(
                self.evidence_table, palette, self.COL_LABEL, self.COL_LINK,
            )

    def set_status(self, kind: str, message: str):
        icon = STATUS_ICONS.get(kind, "🟢")
        self.status_label.setText(f"{icon} {message}")

    # ------------------------------------------------------------------
    # Verification flow
    # ------------------------------------------------------------------

    def start_verification(self):
        claim = self.claim_input.text().strip()
        if not claim:
            self.set_status("warning", self.loc.get("status_enter_claim"))
            return

        self.set_status("processing", self.loc.get("status_processing"))
        self._set_all_buttons_enabled(False)

        detected_lang = detect_language(claim)
        logger.info("Detected language: %s", detected_lang)

        self.thread = VerificationThread(self.pipeline, claim, target_lang=detected_lang)
        self.thread.result_ready.connect(self._on_pipeline_finished)
        self.thread.error_occurred.connect(self._on_pipeline_error)
        self.thread.finished.connect(self._on_thread_finished)
        self.thread.start()

    def _on_pipeline_finished(self, result: dict):
        """Handle successful pipeline completion."""
        if "error" in result:
            self.set_status("error", f"{self.loc.get('status_error')} {result['error']}")
            return

        self.set_status("success", self.loc.get("status_complete"))
        self.current_result = result

        if "report" in result:
            self._render_report(result["report"])
        else:
            logger.warning("Result missing 'report' key. Keys: %s", list(result.keys()))

        if "evidence" in result:
            populate_evidence_table(
                self.evidence_table, result["evidence"], self.palette,
                self.COL_PAPER, self.COL_YEAR, self.COL_LABEL,
                self.COL_CONFIDENCE, self.COL_LINK, self.loc.get,
            )
            supports = [e for e in result["evidence"] if e["nli_label"] == "SUPPORTS"]
            populate_simple_table(self.supporting_table, supports)
            contradicts = [e for e in result["evidence"] if e["nli_label"] == "CONTRADICTS"]
            populate_simple_table(self.contradicting_table, contradicts)

    def _on_pipeline_error(self, msg: str):
        """Handle pipeline errors."""
        self.set_status("error", f"{self.loc.get('status_error')} {msg}")

    def _on_thread_finished(self):
        """Re-enable all buttons when the pipeline thread finishes (success or error)."""
        self._set_all_buttons_enabled(True)
        self.thread = None

    def clear_results(self):
        self.current_result = None
        self.claim_input.clear()
        self.report_tab.clear()
        for table in (self.evidence_table, self.supporting_table, self.contradicting_table):
            table.setRowCount(0)
        self.set_status("ready", self.loc.get("status_ready"))

    def _export_pdf(self):
        export_pdf(
            self, self.current_result, self.loc.get,
            self.set_status, self.COL_LINK,
        )

    # ------------------------------------------------------------------
    # Report rendering
    # ------------------------------------------------------------------

    def _render_report(self, markdown_text: str):
        html = self._renderer.render(markdown_text)
        self.report_tab.setHtml(html)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_evidence_link_clicked(self, row: int, col: int):
        if col != self.COL_LINK:
            return
        item = self.evidence_table.item(row, col)
        if not item:
            return
        url = item.data(Qt.UserRole)
        if url:
            logger.info("Opening URL: %s", url)
            webbrowser.open(url)