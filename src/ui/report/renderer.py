"""Report rendering — converts markdown to styled HTML for the QTextBrowser."""
from src.ui.theme.fonts import Fonts
from src.ui.theme.colors import score_color


class ReportRenderer:
    """Renders pipeline markdown reports as styled HTML."""

    def __init__(self, palette_getter, is_rtl_getter):
        """
        Args:
            palette_getter: Callable that returns the current theme palette dict.
            is_rtl_getter: Callable that returns True if the current language is RTL.
        """
        self._palette = palette_getter
        self._is_rtl = is_rtl_getter

    @property
    def palette(self) -> dict:
        return self._palette()

    @property
    def is_rtl(self) -> bool:
        return self._is_rtl()

    def render(self, markdown_text: str) -> str:
        """Convert the pipeline's markdown report into styled HTML."""
        palette = self.palette
        is_rtl = self.is_rtl
        html_parts = [self._render_line(line, palette, is_rtl) for line in markdown_text.split("\n")]
        return self._wrap_html("".join(html_parts), is_rtl)

    def _render_line(self, line: str, palette: dict, is_rtl: bool) -> str:
        text_align = "text-align: center;"
        direction_style = f"direction: {'rtl' if is_rtl else 'ltr'}; {text_align} unicode-bidi: embed;"

        if line.startswith("# "):
            return self._heading(line[2:], level=1, palette=palette, extra=direction_style)
        if line.startswith("## "):
            return self._heading(line[3:], level=2, palette=palette, extra=direction_style)
        if line.startswith("**") and ":**" in line:
            return self._claim(line, palette, extra=direction_style)
        if "Evidence Strength Score:" in line or "امتیاز درستی ادعا:" in line:
            return self._score(line, palette, extra=direction_style)
        if line.startswith("*(") and line.endswith(")*"):
            return self._score_description(line[2:-2], palette, extra=direction_style)
        if ("No " in line and "evidence found" in line) or "هیچ" in line:
            return self._no_evidence(line, palette, extra=direction_style)
        if not is_rtl and line and line[0].isdigit() and ". " in line[:4]:
            num, rest = line.split(". ", 1)
            return self._numbered_item(num, rest.strip("_"), palette, extra=direction_style)
        if not is_rtl and line.startswith("- "):
            return self._list_item(line[2:], palette, extra=direction_style)
        if not line.strip():
            return self._empty_line()
        if is_rtl and line.strip():
            if any(kw in line for kw in ['مقالات', 'یافته‌های']):
                return self._persian_section_header(line, palette, extra=direction_style)
            return self._persian_evidence(line, palette, extra=direction_style)
        return self._paragraph(line, extra=direction_style)

    @staticmethod
    def _heading(text: str, level: int, palette: dict, extra: str = "") -> str:
        if level == 1:
            return (f'<h1 style="color: {palette["primary"]}; font-size: {Fonts.H1_PX}px; '
                    f'font-weight: bold; margin: 24px 0 12px 0; {extra}">{text}</h1>')
        return (f'<h2 style="color: {palette["primary"]}; font-size: {Fonts.H2_PX}px; '
                f'margin: 20px 0 10px 0; {extra}">{text}</h2>')

    @staticmethod
    def _claim(line: str, palette: dict, extra: str = "") -> str:
        parts = line.split(":**", 1)
        label = parts[0].replace("**", "") + ":"
        content = parts[1].strip() if len(parts) > 1 else ""
        return (f'<p style="font-size: 17px; margin: 10px 0; color: {palette["highlight"]}; {extra}">'
                f'<b>{label}</b> <i>{content}</i></p>')

    @staticmethod
    def _score(line: str, palette: dict, extra: str = "") -> str:
        score_text = line.split(":")[-1].strip().split("/")[0]
        try:
            color = score_color(float(score_text), palette)
        except ValueError:
            color = palette["text"]
        label = line.split(":")[0].strip()
        return (f'<p style="font-size: 17px; margin: 14px 0 4px 0; {extra}"><b>{label}:</b> '
                f'<span style="color: {color}; font-size: {Fonts.SCORE_PX}px; font-weight: bold;">'
                f'{score_text}/100</span></p>')

    @staticmethod
    def _score_description(text: str, palette: dict, extra: str = "") -> str:
        return (f'<p style="font-size: 15px; margin: 2px 0 14px 0; font-style: italic; '
                f'color: {palette["text_muted"]}; {extra}">{text}</p>')

    @staticmethod
    def _no_evidence(line: str, palette: dict, extra: str = "") -> str:
        return (f'<p style="font-size: 16px; margin: 8px 0; color: {palette["warning"]}; '
                f'{extra}"><i>{line}</i></p>')

    @staticmethod
    def _numbered_item(num: str, text: str, palette: dict, extra: str = "") -> str:
        return (f'<p style="color: {palette["highlight"]}; font-size: 16px; margin: 8px 0; '
                f'line-height: 1.6; {extra}"><b>{num}.</b> <i>{text}</i></p>')

    @staticmethod
    def _list_item(text: str, palette: dict, extra: str = "") -> str:
        if "Supporting papers:" in text:
            color = palette["success"]
        elif "Contradicting papers:" in text:
            color = palette["error"]
        elif "Neutral papers:" in text:
            color = palette["warning"]
        else:
            color = palette["text"]
        return f'<p style="color: {color}; font-size: 16px; margin: 6px 0; {extra}">• {text}</p>'

    @staticmethod
    def _persian_section_header(text: str, palette: dict, extra: str = "") -> str:
        if 'تأییدکننده' in text and ':' in text:
            color = palette["success"]
        elif 'متناقض' in text and ':' in text:
            color = palette["error"]
        elif 'خنثی' in text and ':' in text:
            color = palette["warning"]
        else:
            color = palette["text"]
        return f'<p style="color: {color}; font-size: 16px; margin: 6px 0; {extra}">{text}</p>'

    @staticmethod
    def _persian_evidence(text: str, palette: dict, extra: str = "") -> str:
        return (f'<p style="color: {palette["highlight"]}; font-size: 17px; margin: 8px 0; '
                f'line-height: 1.8; {extra}">{text}</p>')

    @staticmethod
    def _paragraph(text: str, extra: str = "") -> str:
        return f'<p style="font-size: 16px; margin: 6px 0; line-height: 1.7; {extra}">{text}</p>'

    @staticmethod
    def _empty_line() -> str:
        return "<br>"

    def _wrap_html(self, body_html: str, is_rtl: bool) -> str:
        rtl_attr = 'dir="rtl"' if is_rtl else ""
        return f"""
        <html>
        <head>
        <style>
            body {{
                font-family: '{Fonts.FAMILY}', sans-serif;
                font-size: {Fonts.REPORT_PX}px;
                line-height: 1.7;
                text-align: center;
            }}
            p {{ margin: 6px 0; }}
        </style>
        </head>
        <body {rtl_attr}>{body_html}</body>
        </html>
        """