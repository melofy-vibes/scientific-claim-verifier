"""Stylesheet generation functions."""
from src.ui.theme.fonts import Fonts


def build_stylesheet(palette: dict) -> str:
    """Generate the global Qt stylesheet from a theme palette dict."""
    return f"""
        QMainWindow {{ background-color: {palette['background']}; color: {palette['text']}; }}
        QWidget {{ background-color: {palette['background']}; color: {palette['text']}; }}

        QLineEdit {{
            background-color: {palette['surface']};
            color: {palette['text']};
            border: 1px solid {palette['border']};
            padding: 10px;
            border-radius: 6px;
            font-size: {Fonts.UI_PT}pt;
        }}
        QLineEdit:focus {{
            border: 1px solid {palette['primary']};
        }}

        QPushButton {{
            background-color: {palette['primary']};
            color: {palette['background']};
            border: none;
            padding: 10px 18px;
            border-radius: 6px;
            font-weight: bold;
            font-size: {Fonts.UI_PT}pt;
        }}
        QPushButton:hover {{ background-color: {palette['accent']}; }}
        QPushButton:disabled {{
            background-color: {palette['border']};
            color: {palette['text_dim']};
        }}

        QTableWidget {{
            background-color: {palette['surface']};
            color: {palette['text']};
            gridline-color: {palette['border']};
            border: 1px solid {palette['border']};
            font-size: {Fonts.TABLE_PT}pt;
            alternate-background-color: {palette['surface_alt']};
        }}
        QTableWidget::item {{ padding: 10px; }}
        QTableWidget::item:selected {{ background-color: {palette['border']}; }}

        QHeaderView::section {{
            background-color: {palette['background']};
            color: {palette['primary']};
            padding: 10px;
            border: 1px solid {palette['border']};
            font-weight: bold;
            font-size: {Fonts.UI_PT}pt;
        }}

        QTextBrowser {{
            background-color: {palette['surface']};
            color: {palette['text']};
            border: 1px solid {palette['border']};
            padding: 24px;
            font-size: {Fonts.REPORT_PX}px;
        }}

        QLabel {{ color: {palette['text_muted']}; }}

        QLabel#statusLabel {{
            font-size: {Fonts.NORMAL}pt;
            font-weight: 600;
            padding: 4px 2px;
        }}

        QTabWidget::pane {{
            border: 1px solid {palette['border']};
            background-color: {palette['surface']};
        }}
        QTabBar::tab {{
            background-color: {palette['background']};
            color: {palette['text_dim']};
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        QTabBar::tab:selected {{
            background-color: {palette['surface']};
            color: {palette['primary']};
        }}
        QTabBar::tab:hover {{ color: {palette['text']}; }}
    """


def build_report_stylesheet(palette: dict) -> str:
    """Stylesheet applied specifically to the report QTextBrowser."""
    return f"""
        QTextBrowser {{
            background-color: {palette['surface']};
            color: {palette['text']};
            border: 1px solid {palette['border']};
            padding: 28px;
            font-size: {Fonts.REPORT_PX}px;
        }}
    """