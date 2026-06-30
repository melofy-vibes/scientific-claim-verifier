"""PubMed E-utilities retriever with error handling."""
import logging
import time
from typing import List, Optional
import requests
import xml.etree.ElementTree as ET
from .base import Paper, BaseRetriever

logger = logging.getLogger(__name__)

class PubMedRetriever(BaseRetriever):
    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    
    def __init__(self, tool: str = "ClaimVerifier", email: str = "user@example.com", delay: float = 0.5):
        self.tool = tool
        self.email = email
        self.delay = delay
        self.headers = {
            "User-Agent": f"{self.tool}/1.0 ({self.email})"
        }

    def search(self, query: str, top_k: int = 10) -> List[Paper]:
        """Search PubMed, return empty list on failure."""
        try:
            # Step 1: search IDs
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": top_k,
                "retmode": "xml",
                "sort": "relevance",
                "tool": self.tool,
                "email": self.email
            }
            logger.info("PubMed query: %s", query)
            time.sleep(self.delay)
            
            try:
                resp = requests.get(self.ESEARCH_URL, params=params, 
                                   headers=self.headers, timeout=30)
                resp.raise_for_status()
            except requests.exceptions.ConnectionError as e:
                logger.warning("PubMed connection failed (check internet/DNS): %s", e)
                return []
            except requests.exceptions.RequestException as e:
                logger.warning("PubMed request failed: %s", e)
                return []
            
            root = ET.fromstring(resp.text)
            ids = [id_elem.text for id_elem in root.findall(".//Id")]
            
            if not ids:
                logger.info("No PubMed results found")
                return []
            
            # Step 2: fetch details
            efetch_params = {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "xml",
                "tool": self.tool,
                "email": self.email
            }
            time.sleep(self.delay)
            
            try:
                resp = requests.get(self.EFETCH_URL, params=efetch_params,
                                   headers=self.headers, timeout=30)
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.warning("PubMed fetch failed: %s", e)
                return []
            
            fetch_root = ET.fromstring(resp.text)
            papers = []
            
            for article in fetch_root.findall(".//PubmedArticle"):
                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else "Untitled"
                
                abstract_elem = article.find(".//AbstractText")
                abstract = abstract_elem.text if abstract_elem is not None else ""
                
                year = None
                date = article.find(".//PubDate/Year")
                if date is not None and date.text:
                    try:
                        year = int(date.text)
                    except ValueError:
                        pass
                
                authors = []
                for author in article.findall(".//Author"):
                    last = author.find("LastName")
                    fore = author.find("ForeName")
                    if last is not None and fore is not None:
                        name = f"{last.text} {fore.text}"
                    elif last is not None:
                        name = last.text
                    else:
                        continue
                    authors.append(name)
                
                pmid = article.find('.//PMID')
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid.text}" if pmid is not None else ""
                
                papers.append(Paper(
                    title=title,
                    authors=authors,
                    year=year,
                    abstract=abstract,
                    url=url,
                    source="pubmed"
                ))
            
            logger.info("Retrieved %d PubMed papers", len(papers))
            return papers
            
        except Exception as e:
            logger.error("Unexpected error in PubMed search: %s", e)
            return []