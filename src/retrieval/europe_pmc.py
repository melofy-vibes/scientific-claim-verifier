"""Europe PMC API retriever."""
import logging
import time
from typing import List
import requests
from .base import Paper, BaseRetriever

logger = logging.getLogger(__name__)

class EuropePMCRetriever(BaseRetriever):
    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def __init__(self, delay: float = 0.5):
        self.delay = delay

    def search(self, query: str, top_k: int = 10) -> List[Paper]:
        params = {
            "query": query,
            "resultType": "lite",
            "pageSize": min(top_k, 100),
            "format": "json",
        }
        logger.info("Europe PMC query: %s", query)
        time.sleep(self.delay)

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.warning("Europe PMC request failed: %s", e)
            return []

        data = resp.json()
        papers = []
        for result in data.get("resultList", {}).get("result", []):
            title = result.get("title", "Untitled")
            author_str = result.get("authorString", "")
            authors = [a.strip() for a in author_str.split(",") if a.strip()]
            year = result.get("pubYear")
            if year:
                try:
                    year = int(year)
                except ValueError:
                    year = None
            abstract = result.get("abstractText", "")
            url = result.get("doi", "")
            if url and not url.startswith("http"):
                url = "https://doi.org/" + url
            papers.append(Paper(
                title=title,
                authors=authors,
                year=year,
                abstract=abstract,
                url=url,
                source="europe_pmc",
                citation_count=result.get("citedByCount", 0)
            ))
        logger.info("Europe PMC retrieved %d papers", len(papers))
        return papers