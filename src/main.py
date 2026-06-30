"""Orchestrator with language detection and translation support."""
import logging
import yaml
from typing import Dict, List
import numpy as np
from .claim_processor import ClaimParser
from .retrieval.manager import RetrievalManager
from .embedding.embedder import Embedder
from .verification.evidence_extractor import EvidenceExtractor
from .verification.nli import NLIModel
from .verification.scorer import Scorer
from .reporting.report_generator import ReportGenerator
from .translation.language_detector import detect_language
from .translation.translator import Translator

logger = logging.getLogger(__name__)

class ClaimVerificationPipeline:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.embedder = Embedder()
        self.parser = ClaimParser()
        self.retrieval = RetrievalManager(
            embedder=self.embedder,
            top_k=self.config["retrieval_top_k"],
            keep_top_n=self.config["retrieval_keep_top_n"]
        )
        self.extractor = EvidenceExtractor(self.embedder, top_n_sentences=100)
        self.nli = NLIModel(
            confidence_threshold=self.config["nli_confidence_threshold"],
            similarity_threshold=self.config["nli_contradiction_similarity_threshold"],
            embedder=self.embedder
        )
        self.scorer = Scorer()
        self.reporter = ReportGenerator(
            max_supporting=self.config["max_supporting_findings"],
            max_contradicting=self.config["max_contradicting_findings"]
        )
        self.translator = Translator()

    def run(self, claim_text: str, target_lang: str = "auto") -> Dict:
        """
        Run the verification pipeline.
        
        Args:
            claim_text: The claim to verify (can be in any supported language)
            target_lang: Language code ('en', 'fa', or 'auto' for automatic detection)
        
        Returns:
            Dictionary with verification results
        """
        logger.info("Processing claim: %s", claim_text)
        
        # Step 0: Language detection
        if target_lang == "auto":
            detected_lang = detect_language(claim_text)
        else:
            detected_lang = target_lang
        
        logger.info("Detected language: %s", detected_lang)
        
        # Store original claim
        original_claim = claim_text
        english_claim = claim_text
        
        # Translate to English if needed
        if detected_lang == "fa":
            try:
                english_claim = self.translator.translate_fa_to_en(claim_text)
                logger.info("Translated claim FA->EN: '%s' -> '%s'", claim_text, english_claim)
            except Exception as e:
                logger.error("Translation failed: %s", e)
                return self._error_result(
                    original_claim,
                    "Translation failed. Please check your internet connection and try again.",
                    detected_lang
                )
        
        # Step 1: Run the English pipeline
        result = self._run_english_pipeline(english_claim)
        
        # Ensure report key always exists
        if "report" not in result:
            result["report"] = self._generate_fallback_report(english_claim, result)

        # Step 2: Add language metadata
        result["original_claim"] = original_claim
        result["english_claim"] = english_claim
        result["language"] = detected_lang
        
        # Step 3: Translate results back to Persian if needed
        if detected_lang == "fa":
            logger.info("Translating results back to Persian...")
            try:
                result = self._translate_results_to_persian(result, original_claim)
                logger.info("Persian translation complete")
            except Exception as e:
                logger.error("Result translation failed: %s", e)
                
                # Ensure report still exists even if translation fails
                if "report" not in result:
                    result["report"] = self._generate_fallback_report(original_claim, result)
                result["translation_error"] = str(e)
        
        return result

    def _run_english_pipeline(self, claim_text: str) -> Dict:
        """Run the core verification pipeline on an English claim."""
        claim = self.parser.parse(claim_text)

        # 1. Retrieval
        all_papers = self.retrieval.search_all(claim.queries, claim_text)
        papers = []
        seen = set()
        for source_papers in all_papers.values():
            for p in source_papers:
                key = p.title.lower().strip()
                if key not in seen:
                    seen.add(key)
                    papers.append(p)
        logger.info("Total unique papers after retrieval filtering: %d", len(papers))
        
        if not papers:
            return self._empty_result(claim_text, "No relevant papers found.")

        # 2. Evidence extraction
        claim_emb = self.embedder.embed([claim_text])[0]
        evidence = self.extractor.extract(claim_text, papers, claim_emb)
        if not evidence:
            return self._empty_result(claim_text, "No evidence sentences extracted.")

        logger.info("Extracted %d evidence sentences", len(evidence))

        # 3. NLI
        sentences = [e["sentence"] for e in evidence]
        embs = np.array([e["embedding"] for e in evidence])
        nli_results = self.nli.batch_predict(sentences, claim_text, premise_embs=embs)
        for i, (label, conf) in enumerate(nli_results):
            evidence[i]["nli_label"] = label
            evidence[i]["nli_confidence"] = conf

        logger.info("NLI evaluated %d evidence sentences", len(evidence))

        # 4. Ranking
        self._rank_evidence(evidence, claim_emb)

        # 5. Group by paper
        grouped_evidence = self._group_by_paper(evidence)

        # 6. Sort by rank score
        grouped_evidence.sort(key=lambda x: x.get("rank_score", 0), reverse=True)

        # 7. Compute paper-level counts
        paper_counts = {"SUPPORTS": 0, "CONTRADICTS": 0, "NEUTRAL": 0}
        for ev in grouped_evidence:
            paper_counts[ev["nli_label"]] += 1

        # 8. Strength score
        _, strength = self.scorer.compute_scores(evidence)

        # 9. Top findings
        top_support = [e for e in grouped_evidence if e["nli_label"] == "SUPPORTS"]
        top_contra = [e for e in grouped_evidence if e["nli_label"] == "CONTRADICTS"]
        top_support.sort(key=lambda x: x.get("rank_score", 0), reverse=True)
        top_contra.sort(key=lambda x: x.get("rank_score", 0), reverse=True)

        logger.info("Pipeline complete: %d total papers", len(grouped_evidence))

        return {
            "claim": claim_text,
            "evidence": grouped_evidence,
            "counts": paper_counts,
            "strength": strength,
            "top_supporting": top_support,
            "top_contradicting": top_contra
        }

    def _generate_fallback_report(self, claim: str, result: Dict) -> str:
        """Generate a basic report if the normal generation fails."""
        counts = result.get("counts", {"SUPPORTS": 0, "CONTRADICTS": 0, "NEUTRAL": 0})
        strength = result.get("strength", 50.0)
        return self.reporter.generate(
            claim=claim,
            paper_counts=counts,
            strength=strength,
            evidence_items=[],
            top_supporting=result.get("top_supporting", []),
            top_contradicting=result.get("top_contradicting", []),
            language=result.get("language", "en")
        )

    def _translate_results_to_persian(self, result: Dict, original_claim: str) -> Dict:
        """Translate all user-facing text to Persian and regenerate report."""
        
        # Translate evidence sentences
        for ev in result.get("evidence", []):
            if "original_sentence" not in ev:
                ev["original_sentence"] = ev["sentence"]
            try:
                ev["sentence"] = self.translator.translate_en_to_fa(ev["sentence"])
            except Exception as e:
                logger.warning("Failed to translate evidence sentence: %s", e)
        
        # Translate top findings
        for ev in result.get("top_supporting", []):
            if "original_sentence" not in ev:
                ev["original_sentence"] = ev["sentence"]
            try:
                ev["sentence"] = self.translator.translate_en_to_fa(ev["sentence"])
            except Exception as e:
                logger.warning("Failed to translate supporting finding: %s", e)
        
        for ev in result.get("top_contradicting", []):
            if "original_sentence" not in ev:
                ev["original_sentence"] = ev["sentence"]
            try:
                ev["sentence"] = self.translator.translate_en_to_fa(ev["sentence"])
            except Exception as e:
                logger.warning("Failed to translate contradicting finding: %s", e)
        
        # Regenerate report in Persian
        paper_counts = result.get("counts", {"SUPPORTS": 0, "CONTRADICTS": 0, "NEUTRAL": 0})
        strength = result.get("strength", 50.0)
        top_support = result.get("top_supporting", [])
        top_contra = result.get("top_contradicting", [])
        
        try:
            result["report"] = self.reporter.generate(
                claim=original_claim,
                paper_counts=paper_counts,
                strength=strength,
                evidence_items=[],
                top_supporting=top_support,
                top_contradicting=top_contra,
                language="fa"
            )
        except Exception as e:
            logger.error("Failed to generate Persian report: %s", e)
            # Keep the English report as fallback
            if "report" not in result:
                result["report"] = self._generate_fallback_report(original_claim, result)
        
        result["claim"] = original_claim
        
        logger.info("Persian report generated with claim: %s", original_claim)
        return result

    def _group_by_paper(self, evidence: List[Dict]) -> List[Dict]:
        """Group evidence sentences by paper title."""
        from collections import defaultdict
        
        paper_groups = defaultdict(list)
        for ev in evidence:
            title = ev["paper"].title.lower().strip()
            paper_groups[title].append(ev)
        
        grouped = []
        for title, items in paper_groups.items():
            supports = [e for e in items if e["nli_label"] == "SUPPORTS"]
            contradicts = [e for e in items if e["nli_label"] == "CONTRADICTS"]
            neutrals = [e for e in items if e["nli_label"] == "NEUTRAL"]
            
            if supports:
                best = max(supports, key=lambda x: x.get("rank_score", 0))
            elif contradicts:
                best = max(contradicts, key=lambda x: x.get("rank_score", 0))
            elif neutrals:
                best = max(neutrals, key=lambda x: x.get("rank_score", 0))
            else:
                continue
            
            best["total_sentences_from_paper"] = len(items)
            best["all_sentences"] = [e["sentence"] for e in items]
            best["all_labels"] = list(set(e["nli_label"] for e in items))
            
            grouped.append(best)
        
        logger.info("Grouped %d sentences into %d unique papers", len(evidence), len(grouped))
        return grouped

    def _rank_evidence(self, evidence: List[Dict], claim_emb: np.ndarray):
        """Calculate rank score for each evidence item."""
        for ev in evidence:
            relevance = ev["paper"].relevance_score
            nli_conf = ev["nli_confidence"]
            sim = ev["similarity"]
            rank = (self.config["ranking_weight_relevance"] * relevance +
                    self.config["ranking_weight_nli"] * nli_conf +
                    self.config["ranking_weight_similarity"] * sim)
            ev["rank_score"] = rank

    def _empty_result(self, claim: str, message: str) -> Dict:
        """Create an empty result with a message."""
        return {
            "claim": claim,
            "report": f"# Scientific Claim Verification Report\n\n**Claim:** {claim}\n\n**{message}**\n",
            "evidence": [],
            "counts": {"SUPPORTS": 0, "CONTRADICTS": 0, "NEUTRAL": 0},
            "strength": 50.0,
            "top_supporting": [],
            "top_contradicting": []
        }

    def _error_result(self, claim: str, message: str, language: str = "en") -> Dict:
        """Create an error result."""
        return {
            "claim": claim,
            "report": f"# Scientific Claim Verification Report\n\n**Claim:** {claim}\n\n**Error:** {message}\n",
            "evidence": [],
            "counts": {"SUPPORTS": 0, "CONTRADICTS": 0, "NEUTRAL": 0},
            "strength": 50.0,
            "top_supporting": [],
            "top_contradicting": [],
            "error": message,
            "language": language,
            "original_claim": claim
        }