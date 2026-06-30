"""Claim parsing and query generation using spaCy."""
import logging
from dataclasses import dataclass, field
from typing import List, Optional
import spacy

logger = logging.getLogger(__name__)

_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

@dataclass
class Claim:
    text: str
    subject: Optional[str] = None
    relation: Optional[str] = None
    object: Optional[str] = None
    domain: Optional[str] = None
    queries: List[str] = field(default_factory=list)

    def to_dict(self):
        return self.__dict__

class ClaimParser:
    def __init__(self):
        self.nlp = get_nlp()

    def parse(self, text: str) -> Claim:
        doc = self.nlp(text)
        claim = Claim(text=text)

        for token in doc:
            if token.dep_ == "ROOT" and token.pos_ == "VERB":
                claim.relation = token.lemma_
                for child in token.children:
                    if child.dep_ == "nsubj":
                        claim.subject = self._get_span(child)
                    elif child.dep_ == "dobj":
                        claim.object = self._get_span(child)
                break

        if not claim.subject and doc.ents:
            claim.subject = doc.ents[0].text
        if not claim.object and len(doc.ents) > 1:
            claim.object = doc.ents[-1].text

        if claim.relation:
            root = [t for t in doc if t.dep_ == "ROOT"]
            if root:
                root = root[0]
                domain_parts = []
                for child in root.children:
                    if child.dep_ == "prep":
                        domain_parts.append(child.text)
                        for pchild in child.children:
                            if pchild.dep_ == "pobj":
                                domain_parts.append(self._get_span(pchild))
                if domain_parts:
                    claim.domain = " ".join(domain_parts)

        claim.queries = self._generate_queries(claim, doc)
        logger.info("Parsed claim: %s", claim.to_dict())
        return claim

    def _get_span(self, token: spacy.tokens.Token) -> str:
        if token.pos_ in ("NOUN", "PROPN", "PRON"):
            subtree = sorted(token.subtree, key=lambda t: t.i)
            words = [t.text for t in subtree if t.dep_ != "punct"]
            return " ".join(words)
        return token.text

    def _generate_queries(self, claim: Claim, doc: spacy.tokens.Doc) -> List[str]:
        """Create retrieval queries using noun chunks and named entities."""
        queries = []
        # Original claim
        queries.append(claim.text)

        # Noun chunks (longer phrases)
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) >= 2:
                queries.append(chunk.text)

        # Named entities
        for ent in doc.ents:
            if len(ent.text.split()) >= 2:
                queries.append(ent.text)

        # Combine subject/object if present
        if claim.subject and claim.object:
            queries.append(f"{claim.subject} {claim.object} comparison")
            queries.append(f"{claim.subject} versus {claim.object}")
            if claim.relation:
                queries.append(f"{claim.subject} {claim.relation} {claim.object}")

        # Domain
        if claim.domain:
            queries.append(claim.domain)

        # Remove duplicates and short queries
        seen = set()
        clean_queries = []
        for q in queries:
            if len(q.split()) >= 2 and q not in seen:
                seen.add(q)
                clean_queries.append(q)
        return clean_queries[:10]  # keep at most 10