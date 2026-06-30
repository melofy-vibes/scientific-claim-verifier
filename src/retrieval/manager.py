"""Retrieval manager with caching and relevance filtering."""
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict
import numpy as np
from .base import Paper
from .arxiv import ArxivRetriever
from .semantic_scholar import SemanticScholarRetriever
from .pubmed import PubMedRetriever
from .openalex import OpenAlexRetriever
from .europe_pmc import EuropePMCRetriever
from .core import CORERetriever
from ..embedding.embedder import Embedder

logger = logging.getLogger(__name__)

class RetrievalManager:
    def __init__(self, embedder: Embedder,
                 cache_dir: Path = Path("data/cache"),
                 top_k: int = 100,
                 keep_top_n: int = 30):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.top_k = top_k
        self.keep_top_n = keep_top_n
        self.embedder = embedder
        self.retrievers = {
            "arxiv": ArxivRetriever(),
            "semantic_scholar": SemanticScholarRetriever(),
            "pubmed": PubMedRetriever(),
            "openalex": OpenAlexRetriever(),
            "europe_pmc": EuropePMCRetriever(),
            "core": CORERetriever()
        }

    def search_all(self, queries: List[str], claim_text: str) -> Dict[str, List[Paper]]:
        """Retrieve and filter papers, returning source‑separated lists."""
        all_papers = {key: [] for key in self.retrievers}
        for query in queries:
            for source, retriever in self.retrievers.items():
                try:
                    papers = self._cached_search(retriever, query, source)
                    all_papers[source].extend(papers)
                except Exception as e:
                    logger.warning("Failed retrieval %s for '%s': %s", source, query, e)

        # Deduplicate per source
        for source in all_papers:
            seen = set()
            unique = []
            for p in all_papers[source]:
                key = p.title.lower().strip()
                if key not in seen:
                    seen.add(key)
                    unique.append(p)
            all_papers[source] = unique

        # Flatten and deduplicate across sources
        flat_papers = []
        seen_titles = set()
        for source, papers in all_papers.items():
            for p in papers:
                key = p.title.lower().strip()
                if key not in seen_titles:
                    seen_titles.add(key)
                    flat_papers.append(p)

        if not flat_papers:
            logger.warning("No papers retrieved")
            return all_papers

        # Compute abstract embeddings and relevance scores
        abstracts = [p.abstract if p.abstract else "" for p in flat_papers]
        claim_emb = self.embedder.embed([claim_text])[0]
        abstract_embs = self.embedder.embed(abstracts)

        from numpy.linalg import norm
        for i, emb in enumerate(abstract_embs):
            sim = float(np.dot(claim_emb, emb) / (norm(claim_emb) * norm(emb) + 1e-8))
            flat_papers[i].relevance_score = sim

        # Sort by relevance and keep top N
        flat_papers.sort(key=lambda x: x.relevance_score, reverse=True)
        flat_papers = flat_papers[:self.keep_top_n]

        logger.info("After relevance filtering: kept %d/%d papers", len(flat_papers), len(abstracts))

        # Re-group by source for consistency
        result = {key: [] for key in self.retrievers}
        for p in flat_papers:
            result[p.source].append(p)

        return result

    def _cached_search(self, retriever, query: str, source: str) -> List[Paper]:
        cache_key = hashlib.md5(f"{source}_{query}_{self.top_k}".encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            logger.info("Cache hit for %s: %s", source, query)
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                return [Paper(**item) for item in data]
            except Exception:
                pass
        logger.info("Fetching from %s: %s", source, query)
        papers = retriever.search(query, self.top_k)
        with open(cache_file, "w") as f:
            json.dump([p.__dict__ for p in papers], f, indent=2)
        return papers