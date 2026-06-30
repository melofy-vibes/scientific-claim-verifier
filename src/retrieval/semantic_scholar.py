"""Semantic Scholar API retriever with API key support"""
import logging
import time
import os
from typing import List, Optional
import requests
from .base import Paper, BaseRetriever

logger = logging.getLogger(__name__)

class SemanticScholarRetriever(BaseRetriever):
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    # Alternative: use the older API that might work without key
    ALT_URL = "https://api.semanticscholar.org/v1/paper/search"
    FIELDS = "title,authors,year,abstract,url,citationCount"
    
    def __init__(self, api_key: Optional[str] = None, delay: float = 1.0):
        self.delay = delay
        # Try to get API key from environment variable or parameter
        self.api_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        
        # Better headers to avoid being blocked
        self.headers = {
            "User-Agent": "ScientificClaimVerifier/1.0 (mailto:your.email@example.com)",
            "Accept": "application/json"
        }
        
        if self.api_key:
            self.headers["x-api-key"] = self.api_key
            logger.info("Using Semantic Scholar API key")
        else:
            logger.warning("No Semantic Scholar API key found. Using unauthenticated access (may be rate-limited).")
            logger.warning("Get a free API key at: https://www.semanticscholar.org/product/api")

    def search(self, query: str, top_k: int = 10) -> List[Paper]:
        """
        Search Semantic Scholar for papers.
        Falls back to alternative API if primary fails.
        """
        # First try the graph API
        papers = self._try_search(self.BASE_URL, query, top_k)
        
        # If that fails, try the v1 API
        if papers is None:
            logger.info("Graph API failed, trying v1 API...")
            papers = self._try_search(self.ALT_URL, query, top_k, use_v1=True)
        
        # If both fail, return empty list
        if papers is None:
            logger.error("All Semantic Scholar API attempts failed")
            return []
        
        return papers
    
    def _try_search(self, url: str, query: str, top_k: int, use_v1: bool = False) -> Optional[List[Paper]]:
        """Try to search with given URL, return None if failed."""
        try:
            if use_v1:
                params = {
                    "query": query,
                    "limit": min(top_k, 100),  # v1 API max is 100
                    "offset": 0
                }
            else:
                params = {
                    "query": query,
                    "limit": min(top_k, 100),
                    "fields": self.FIELDS
                }
            
            logger.info("Semantic Scholar query: %s (url: %s)", query, url)
            time.sleep(self.delay)  # Rate limiting
            
            resp = requests.get(url, params=params, headers=self.headers, timeout=30)
            
            # Check for rate limiting
            if resp.status_code == 429:
                logger.warning("Rate limited by Semantic Scholar. Waiting 5 seconds...")
                time.sleep(5)
                resp = requests.get(url, params=params, headers=self.headers, timeout=30)
            
            # If still forbidden, return None to trigger fallback
            if resp.status_code in (401, 403):
                logger.warning("Access denied (status %d). %s", resp.status_code, 
                             "Consider getting an API key." if not self.api_key else "Check your API key.")
                return None
            
            resp.raise_for_status()
            data = resp.json()
            
            papers = []
            # Handle different response formats
            items = data.get("data", []) if not use_v1 else data.get("results", [])
            
            for item in items:
                # Handle different field names between API versions
                authors_list = item.get("authors", [])
                if isinstance(authors_list, list) and authors_list and isinstance(authors_list[0], dict):
                    authors = [a.get("name", "") for a in authors_list]
                else:
                    authors = [str(a) for a in authors_list]
                
                abstract = item.get("abstract") or ""
                year = item.get("year")
                citation_count = item.get("citationCount", 0)
                
                # URL might be in different locations
                url = item.get("url", "")
                if not url and "paperId" in item:
                    url = f"https://www.semanticscholar.org/paper/{item['paperId']}"
                
                papers.append(Paper(
                    title=item.get("title", "Untitled"),
                    authors=authors,
                    year=year,
                    abstract=abstract,
                    url=url,
                    source="semantic_scholar",
                    citation_count=citation_count
                ))
            
            logger.info("Retrieved %d papers from Semantic Scholar", len(papers))
            return papers
            
        except requests.exceptions.RequestException as e:
            logger.error("Semantic Scholar request failed: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected error in Semantic Scholar search: %s", e)
            return None