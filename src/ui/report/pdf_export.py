"""PDF export — generates print-optimized HTML and exports to PDF."""
import logging
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QFileDialog, QMessageBox

logger = logging.getLogger(__name__)


def export_pdf(parent, current_result: dict, loc_getter, status_callback, col_link: int) -> None:
    """Export the report + evidence table as a PDF file.

    Args:
        parent: The parent QWidget for dialogs.
        current_result: The pipeline result dict with 'report' and 'evidence' keys.
        loc_getter: Callable that returns a localized string for a given key.
        status_callback: Callable to update the status label (kind, message).
        col_link: Column index for the link column in the evidence table.
    """
    if current_result is None:
        QMessageBox.information(parent, "Nothing to Export", "Run a verification first.")
        return

    default_name = f"claim_report_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    path_str, _ = QFileDialog.getSaveFileName(
        parent, "Export PDF", default_name, "PDF Files (*.pdf)",
    )
    if not path_str:
        return

    path = Path(path_str)
    if path.suffix.lower() != ".pdf":
        path = path.with_suffix(".pdf")

    try:
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(str(path))
        printer.setPageSize(QPrinter.A4)
        printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)

        doc = QTextDocument()
        report_md = current_result.get("report", "")
        evidence_table = parent.evidence_table

        # Detect if the report is in Persian
        is_persian = _is_persian_report(report_md)

        report_html = build_print_report_html(report_md)
        evidence_html = build_print_table_html(evidence_table, col_link)

        combined_html = _build_combined_html(report_html, evidence_html, is_persian)
        doc.setHtml(combined_html)
        doc.print_(printer)

        status_callback("success", loc_getter("export_success", "PDF exported successfully"))
    except Exception as exc:
        logger.exception("Failed to export PDF")
        QMessageBox.warning(parent, "Export Failed", str(exc))


def _is_persian_report(markdown_text: str) -> bool:
    """Detect if the report is in Persian by checking for Persian characters."""
    if not markdown_text:
        return False
    # Check for Persian/Arabic Unicode range characters
    persian_chars = any(
        '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F'
        for char in markdown_text[:500]  # Check first 500 chars
    )
    # Also check for Persian section headers
    persian_keywords = any(
        keyword in markdown_text
        for keyword in ['مقالات', 'یافته‌های', 'ادعا', 'گزارش', 'شواهد']
    )
    return persian_chars or persian_keywords


def build_print_report_html(markdown_text: str) -> str:
    """Convert the report markdown to print-optimized HTML."""
    lines = markdown_text.split('\n')
    html_parts = []

    for line in lines:
        if line.startswith('# '):
            html_parts.append(f'<h1>{line[2:]}</h1>')
        elif line.startswith('## '):
            html_parts.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('**') and ':**' in line:
            parts = line.split(':**', 1)
            label = parts[0].replace('**', '') + ':'
            content = parts[1].strip() if len(parts) > 1 else ''
            html_parts.append(f'<p><b>{label}</b> <span class="claim-text">{content}</span></p>')
        elif 'Evidence Strength Score:' in line or 'امتیاز درستی ادعا:' in line:
            label, score_part = line.split(':', 1)
            score_val = score_part.strip().split('/')[0]
            html_parts.append(
                f'<p><b>{label}:</b> <span class="score-value">{score_val}/100</span></p>'
            )
        elif line.startswith('*(') and line.endswith(')*'):
            html_parts.append(f'<p><i>{line[2:-2]}</i></p>')
        elif 'No ' in line and 'evidence found' in line:
            html_parts.append(f'<p><i>{line}</i></p>')
        elif 'هیچ' in line:
            html_parts.append(f'<p><i>{line}</i></p>')
        elif line and line[0].isdigit() and '. ' in line[:4]:
            num, rest = line.split('. ', 1)
            rest = rest.strip('_')
            html_parts.append(f'<p class="evidence-item"><b>{num}.</b> <i>{rest}</i></p>')
        elif line.startswith('- '):
            line_text = line[2:]
            if 'Supporting papers:' in line_text or 'مقالات تأییدکننده' in line_text:
                html_parts.append(f'<p class="summary-item supporting">• {line_text}</p>')
            elif 'Contradicting papers:' in line_text or 'مقالات متناقض' in line_text:
                html_parts.append(f'<p class="summary-item contradicting">• {line_text}</p>')
            elif 'Neutral papers:' in line_text or 'مقالات خنثی' in line_text:
                html_parts.append(f'<p class="summary-item neutral">• {line_text}</p>')
            else:
                html_parts.append(f'<p class="summary-item">{line_text}</p>')
        elif not line.strip():
            html_parts.append('<br>')
        else:
            html_parts.append(f'<p>{line}</p>')

    return '\n'.join(html_parts)


def build_print_table_html(table, col_link: int) -> str:
    """Convert a QTableWidget to print-optimized HTML with clickable links."""
    rows = table.rowCount()
    cols = table.columnCount()

    html = ['<table>']
    html.append('<thead><tr>')
    for col in range(cols):
        header_item = table.horizontalHeaderItem(col)
        header_text = header_item.text() if header_item else ""
        html.append(f'<th>{header_text}</th>')
    html.append('</tr></thead>')

    html.append('<tbody>')
    for row in range(rows):
        html.append('<tr>')
        for col in range(cols):
            item = table.item(row, col)
            if item:
                text = item.text()
                url = item.data(Qt.UserRole)
                if url and col == col_link:
                    html.append(f'<td><a href="{url}" class="link-cell">{text}</a></td>')
                else:
                    html.append(f'<td>{text}</td>')
            else:
                html.append('<td></td>')
        html.append('</tr>')
    html.append('</tbody>')
    html.append('</table>')
    return '\n'.join(html)


def _build_combined_html(report_html: str, evidence_html: str, is_persian: bool = False) -> str:
    """Wrap report and evidence HTML in a print-optimized document.
    
    Args:
        report_html: The report content as HTML.
        evidence_html: The evidence table as HTML.
        is_persian: If True, applies RTL direction and center alignment.
    """
    # Body styles that change for Persian
    if is_persian:
        body_extra = 'direction: rtl; text-align: center;'
        evidence_align = 'text-align: center;'
    else:
        body_extra = ''
        evidence_align = ''

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        @page {{ size: A4; margin: 15mm; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
            font-size: 11pt; line-height: 1.5; color: #1a1a1a;
            {body_extra}
        }}
        h1 {{ font-size: 18pt; font-weight: bold; color: #2563eb; margin: 20pt 0 10pt 0; page-break-after: avoid; }}
        h2 {{ font-size: 14pt; font-weight: bold; color: #2563eb; margin: 16pt 0 8pt 0; page-break-after: avoid; }}
        p {{ font-size: 11pt; margin: 6pt 0; line-height: 1.5; }}
        i, em {{ font-style: italic; }}
        b, strong {{ font-weight: bold; }}
        a {{ color: #2563eb; text-decoration: underline; }}
        .evidence-item {{ font-size: 11pt; margin: 8pt 0 8pt 15pt; line-height: 1.5; }}
        .score-value {{ font-size: 16pt; font-weight: bold; }}
        .claim-text {{ font-size: 12pt; font-style: italic; color: #4a4a4a; }}
        .summary-item {{ font-size: 11pt; margin: 5pt 0 5pt 15pt; }}
        .supporting {{ color: #16a34a; }}
        .contradicting {{ color: #dc2626; }}
        .neutral {{ color: #d97706; }}
        .page-break {{ page-break-before: always; }}
        .table-title {{ font-size: 14pt; font-weight: bold; color: #2563eb; margin: 20pt 0 10pt 0; }}
        table {{
            border-collapse: collapse; width: 100%; margin-top: 12pt;
            font-size: 9pt; table-layout: auto;
            {evidence_align}
        }}
        th {{
            background-color: #e5e7eb; color: #1a1a1a; padding: 8pt 6pt;
            border: 1px solid #d1d5db; font-weight: bold; font-size: 9pt;
            text-align: left; word-wrap: break-word;
        }}
        td {{
            padding: 6pt 6pt; border: 1px solid #e5e7eb; font-size: 8.5pt;
            line-height: 1.3; vertical-align: top; word-wrap: break-word;
        }}
        tr:nth-child(even) {{ background-color: #f9fafb; }}
        .link-cell {{ color: #2563eb; text-decoration: underline; }}
    </style>
    </head>
    <body>
    {report_html}
    <div class="page-break"></div>
    <div class="table-title">📊 Evidence Table</div>
    {evidence_html}
    </body>
    </html>
    """