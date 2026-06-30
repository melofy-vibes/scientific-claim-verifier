"""Compute evidence strength using weighted scores."""
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

class Scorer:
    @staticmethod
    def compute_scores(evidence_classifications: List[Dict]) -> Tuple[Dict, float]:
        support_total = 0.0
        contradict_total = 0.0
        neutral_total = 0.0
        counts = {"SUPPORTS": 0, "CONTRADICTS": 0, "NEUTRAL": 0}

        for item in evidence_classifications:
            label = item["nli_label"]
            conf = item["nli_confidence"]
            if label == "SUPPORTS":
                support_total += conf
                counts["SUPPORTS"] += 1
            elif label == "CONTRADICTS":
                contradict_total += conf
                counts["CONTRADICTS"] += 1
            else:
                neutral_total += conf
                counts["NEUTRAL"] += 1

        total = support_total + contradict_total
        if total > 0:
            strength = (support_total / total) * 100
        else:
            strength = 50.0  # no opinion

        return counts, round(strength, 2)