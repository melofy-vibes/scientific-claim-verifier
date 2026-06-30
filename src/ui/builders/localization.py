"""Localization utilities for updating UI text."""
from typing import Callable


class UILocalizer:
    """Handles retranslation of all UI elements when language changes."""

    def __init__(self, window):
        self.window = window

    def retranslate_ui(self, loc) -> None:
        """Update all static UI text from localization files."""
        w = self.window
        w.setWindowTitle(loc.get("app_title"))
        w.claim_input.setPlaceholderText(loc.get("input_placeholder"))
        w.run_btn.setText(loc.get("verify_btn"))

        # Theme toggle button
        if w.dark_mode:
            w.theme_action.setText(loc.get("light_mode"))
        else:
            w.theme_action.setText(loc.get("dark_mode"))

        # Language toggle button
        if w.current_lang == "en":
            w.lang_action.setText("فارسی")
        else:
            w.lang_action.setText("English")

        # Bottom buttons
        w.clear_btn.setText("🗑 " + loc.get("clear", "Clear"))
        w.export_btn.setText("📄 " + loc.get("export_pdf", "Export PDF"))

        # Tabs
        w.tabs.setTabText(0, loc.get("tab_report"))
        w.tabs.setTabText(1, loc.get("tab_evidence"))
        w.tabs.setTabText(2, loc.get("tab_supporting"))
        w.tabs.setTabText(3, loc.get("tab_contradicting"))

        # Table headers
        w.evidence_table.setHorizontalHeaderLabels([
            loc.get("table_paper"), loc.get("table_year"),
            loc.get("table_label"), loc.get("table_confidence"), loc.get("table_link"),
        ])
        w.supporting_table.setHorizontalHeaderLabels([
            loc.get("table_paper"), loc.get("table_sentence"), loc.get("table_confidence"),
        ])
        w.contradicting_table.setHorizontalHeaderLabels([
            loc.get("table_paper"), loc.get("table_sentence"), loc.get("table_confidence"),
        ])

        if w.current_result is None:
            w.set_status("ready", loc.get("status_ready"))

        if w.current_result is not None:
            from src.ui.builders.ui_builders import populate_evidence_table
            populate_evidence_table(
                w.evidence_table, w.current_result.get("evidence", []), w.palette,
                w.COL_PAPER, w.COL_YEAR, w.COL_LABEL, w.COL_CONFIDENCE, w.COL_LINK,
                loc.get
            )