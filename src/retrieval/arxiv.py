"""ArXiv API retriever."""
import logging
import time
from typing import List
import requests
import feedparser
from .base import Paper, BaseRetriever

logger = logging.getLogger(__name__)

class ArxivRetriever(BaseRetriever):
    BASE_URL = "http://export.arxiv.org/api/query"
    def __init__(self, delay: float = 0.5):
        self.delay = delay

    def search(self, query: str, top_k: int = 10) -> List[Paper]:
        params = {
            "search_query": query,
            "start": 0,
            "max_results": top_k,
            "sortBy": "relevance"
        }
        logger.info("ArXiv query: %s", query)
        time.sleep(self.delay)  # be polite
        resp = requests.get(self.BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        papers = []
        for entry in feed.entries:
            title = entry.title.strip()
            authors = [a.name for a in entry.authors] if "authors" in entry else []
            year = entry.published_parsed.tm_year if "published_parsed" in entry else None
            abstract = entry.summary.strip() if "summary" in entry else ""
            url = entry.link
            papers.append(Paper(title=title, authors=authors, year=year,
                                abstract=abstract, url=url, source="arxiv"))
        return papers