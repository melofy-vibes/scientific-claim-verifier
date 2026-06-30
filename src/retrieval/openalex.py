"""OpenAlex API retriever."""
import logging
import time
from typing import List, Dict, Any
import requests
from .base import Paper, BaseRetriever

logger = logging.getLogger(__name__)

class OpenAlexRetriever(BaseRetriever):
    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, delay: float = 0.5):
        self.delay = delay

    def search(self, query: str, top_k: int = 10) -> List[Paper]:
        params = {
            "search": query,
            "per_page": min(top_k, 200),
            "sort": "relevance",
        }
        logger.info("OpenAlex query: %s", query)
        time.sleep(self.delay)

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.warning("OpenAlex request failed: %s", e)
            return []

        data = resp.json()
        papers = []
        for work in data.get("results", []):
            title = work.get("title", "Untitled")
            authors = []
            for authorship in work.get("authorships", []):
                author = authorship.get("author", {})
                name = author.get("display_name", "")
                if name:
                    authors.append(name)
            year = work.get("publication_year")
            # Reconstruct abstract from inverted index
            abstract = self._reconstruct_abstract(work.get("abstract_inverted_index"))
            url = work.get("primary_location", {}).get("landing_page_url", "")
            papers.append(Paper(
                title=title,
                authors=authors,
                year=year,
                abstract=abstract,
                url=url,
                source="openalex",
                citation_count=work.get("cited_by_count", 0)
            ))
        logger.info("OpenAlex retrieved %d papers", len(papers))
        return papers

    def _reconstruct_abstract(self, inverted_index: Dict[str, List[int]] | None) -> str:
        """Convert OpenAlex inverted index to plain text."""
        if not inverted_index:
            return ""
        # Build a list of (position, word) tuples
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        # Sort by position and join
        word_positions.sort(key=lambda x: x[0])
        return " ".join(word for _, word in word_positions)