"""CORE API retriever."""
import logging
import os
import time
from typing import List
import requests
from .base import Paper, BaseRetriever

logger = logging.getLogger(__name__)

class CORERetriever(BaseRetriever):
    BASE_URL = "https://api.core.ac.uk/v3/search/works"

    def __init__(self, api_key: str = None, delay: float = 0.5):
        self.delay = delay
        self.api_key = api_key or os.environ.get("CORE_API_KEY")
        if not self.api_key:
            logger.warning("No CORE_API_KEY found. CORE API may be limited or unavailable.")
        self.headers = {
            "User-Agent": "ScientificClaimVerifier/1.0"
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    def search(self, query: str, top_k: int = 10) -> List[Paper]:
        params = {
            "q": query,
            "limit": min(top_k, 100),
        }
        logger.info("CORE query: %s", query)
        time.sleep(self.delay)

        try:
            resp = requests.get(self.BASE_URL, params=params, headers=self.headers, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.warning("CORE request failed: %s", e)
            return []

        data = resp.json()
        papers = []
        for work in data.get("results", []):
            title = work.get("title", "Untitled")
            authors = [a.get("name", "") for a in work.get("authors", [])]
            year = work.get("yearPublished")
            abstract = work.get("abstract", "")
            url = work.get("downloadUrl") or work.get("doi", "")
            if url and not url.startswith("http"):
                url = "https://doi.org/" + url
            papers.append(Paper(
                title=title,
                authors=authors,
                year=year,
                abstract=abstract,
                url=url,
                source="core",
                citation_count=work.get("citationCount", 0)
            ))
        logger.info("CORE retrieved %d papers", len(papers))
        return papers