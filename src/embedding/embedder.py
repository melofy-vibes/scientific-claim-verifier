"""Embedding generation using Sentence Transformers."""
import logging
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info("Loading embedding model %s", model_name)
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list) -> np.ndarray:
        """Return numpy array of shape (len(texts), embedding_dim)."""
        return self.model.encode(texts, show_progress_bar=False)