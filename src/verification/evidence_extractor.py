"""Extract candidate evidence sentences."""
import logging
from typing import List, Dict
import numpy as np
from ..embedding.embedder import Embedder
from ..embedding.indexer import Indexer
from ..retrieval.base import Paper

logger = logging.getLogger(__name__)

class EvidenceExtractor:
    def __init__(self, embedder: Embedder, top_n_sentences: int = 20):
        self.embedder = embedder
        self.top_n = top_n_sentences

    def extract(self, claim: str, papers: List[Paper], claim_emb: np.ndarray = None) -> List[Dict]:
        """Return evidence with paper, sentence, similarity, and embedding."""
        if claim_emb is None:
            claim_emb = self.embedder.embed([claim])[0]

        all_sentences = []
        paper_map = []
        for paper in papers:
            if not paper.abstract or not paper.abstract.strip():
                continue
            sents = self._split_sentences(paper.abstract)
            for sent in sents:
                all_sentences.append(sent)
                paper_map.append(paper)

        if not all_sentences:
            return []

        sent_embs = self.embedder.embed(all_sentences)
        indexer = Indexer(dim=claim_emb.shape[0])
        indexer.build(sent_embs, all_sentences)
        hits = indexer.search(claim_emb, k=min(self.top_n, len(all_sentences)))

        evidence = []
        for text, score in hits:
            idx = all_sentences.index(text)
            # Compute actual cosine similarity
            emb = sent_embs[idx]
            cosine = float(np.dot(claim_emb, emb) / (np.linalg.norm(claim_emb) * np.linalg.norm(emb) + 1e-8))
            evidence.append({
                "paper": paper_map[idx],
                "sentence": text,
                "similarity": cosine,
                "embedding": emb
            })
        return evidence

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        import re
        if not text or not text.strip():
            return []
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if len(s.strip()) > 15]