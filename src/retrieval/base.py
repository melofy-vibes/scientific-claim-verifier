"""Base class and data classes for literature retrieval."""
from dataclasses import dataclass, field
from typing import List, Optional
from abc import ABC, abstractmethod

@dataclass
class Paper:
    title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    abstract: str = ""  # Default to empty string instead of None
    url: str = ""
    source: str = ""  # 'arxiv', 'semantic_scholar', 'pubmed'
    citation_count: int = 0
    relevance_score: float = 0.0 

@dataclass
class RetrievalResult:
    papers: List[Paper]
    query: str
    source: str

class BaseRetriever(ABC):
    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> List[Paper]:
        """Retrieve papers for a query."""
        pass