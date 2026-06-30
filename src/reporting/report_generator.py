"""Generate structured report – supports Persian and English formatting."""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, max_supporting: int = 5, max_contradicting: int = 5):
        self.max_supporting = max_supporting
        self.max_contradicting = max_contradicting

    def generate(self, claim: str, paper_counts: Dict, strength: float,
                 evidence_items: List[Dict],
                 top_supporting: List[Dict] = None,
                 top_contradicting: List[Dict] = None,
                 language: str = "en") -> str:
        """Generate report. If language='fa', use Persian-friendly formatting."""
        
        if language == "fa":
            return self._generate_persian(claim, paper_counts, strength,
                                          top_supporting, top_contradicting)
        else:
            return self._generate_english(claim, paper_counts, strength,
                                          top_supporting, top_contradicting)

    def _generate_english(self, claim: str, paper_counts: Dict, strength: float,
                          top_supporting: List[Dict] = None,
                          top_contradicting: List[Dict] = None) -> str:
        """English report with bullet points and numbering."""
        lines = []
        lines.append(f"# Scientific Claim Verification Report\n")
        lines.append(f"**Claim:** {claim}\n")
        lines.append(f"## Evidence Summary")
        lines.append(f"- Supporting papers: {paper_counts.get('SUPPORTS', 0)}")
        lines.append(f"- Contradicting papers: {paper_counts.get('CONTRADICTS', 0)}")
        lines.append(f"- Neutral papers: {paper_counts.get('NEUTRAL', 0)}\n")

        # Top supporting findings
        if top_supporting and len(top_supporting) > 0:
            lines.append(f"## Key Supporting Findings\n")
            for i, ev in enumerate(top_supporting[:self.max_supporting], 1):
                snippet = ev["sentence"][:200] + ("..." if len(ev["sentence"]) > 200 else "")
                lines.append(f"{i}. _{snippet}_\n")
        else:
            lines.append("## Key Supporting Findings")
            lines.append("No supporting evidence found.\n")

        # Top contradicting findings
        if top_contradicting and len(top_contradicting) > 0:
            lines.append(f"## Key Contradicting Findings\n")
            for i, ev in enumerate(top_contradicting[:self.max_contradicting], 1):
                snippet = ev["sentence"][:200] + ("..." if len(ev["sentence"]) > 200 else "")
                lines.append(f"{i}. _{snippet}_\n")
        else:
            lines.append("## Key Contradicting Findings")
            lines.append("No contradicting evidence found.\n")

        lines.append(f"## Confidence")
        lines.append(f"**Evidence Strength Score:** {strength}/100\n")
        lines.append("*(Based on weighted supporting vs. contradicting evidence across all sentences)*\n")
        return "\n".join(lines)

    def _generate_persian(self, claim: str, paper_counts: Dict, strength: float,
                          top_supporting: List[Dict] = None,
                          top_contradicting: List[Dict] = None) -> str:
        """Persian report – no bullets, no numbers, RTL-friendly plain text."""
        lines = []
        lines.append(f"# گزارش بررسی ادعای علمی\n")
        lines.append(f"**ادعا:** {claim}\n")
        lines.append(f"## خلاصه شواهد")
        lines.append(f"مقالات تأییدکننده: {paper_counts.get('SUPPORTS', 0)}")
        lines.append(f"مقالات متناقض: {paper_counts.get('CONTRADICTS', 0)}")
        lines.append(f"مقالات خنثی: {paper_counts.get('NEUTRAL', 0)}\n")

        # Top supporting findings (no numbering)
        if top_supporting and len(top_supporting) > 0:
            lines.append(f"## یافته‌های کلیدی تأییدکننده\n")
            for ev in top_supporting[:self.max_supporting]:
                snippet = ev["sentence"][:200] + ("..." if len(ev["sentence"]) > 200 else "")
                lines.append(f"{snippet}\n")
        else:
            lines.append("## یافته‌های کلیدی تأییدکننده")
            lines.append("هیچ شواهد تأییدکننده‌ای یافت نشد.\n")

        # Top contradicting findings (no numbering)
        if top_contradicting and len(top_contradicting) > 0:
            lines.append(f"## یافته‌های کلیدی متناقض\n")
            for ev in top_contradicting[:self.max_contradicting]:
                snippet = ev["sentence"][:200] + ("..." if len(ev["sentence"]) > 200 else "")
                lines.append(f"{snippet}\n")
        else:
            lines.append("## یافته‌های کلیدی متناقض")
            lines.append("هیچ شواهد متناقضی یافت نشد.\n")

        lines.append(f"## میزان اطمینان")
        lines.append(f"**امتیاز درستی ادعا:** {strength}/100\n")
        lines.append("(بر اساس شواهد وزن‌دهی‌شده تأییدکننده در مقابل متناقض در تمام جملات)\n")
        return "\n".join(lines)