"""FAISS index management."""
import logging
from pathlib import Path
import numpy as np
import faiss

logger = logging.getLogger(__name__)

class Indexer:
    def __init__(self, dim: int, index_dir: Path = Path("data/embeddings")):
        self.dim = dim
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index = None
        self.texts = []   # sentences stored in order

    def build(self, embeddings: np.ndarray, texts: list):
        """Create a new FAISS index from embeddings."""
        self.texts = texts
        if embeddings.shape[0] == 0:
            self.index = None
            return
        self.index = faiss.IndexFlatIP(self.dim)  # inner product (cosine after normalisation)
        # Normalize embeddings
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        logger.info("FAISS index built with %d vectors", self.index.ntotal)

    def search(self, query_embedding: np.ndarray, k: int = 20) -> list:
        """Return list of (text, score) tuples."""
        if self.index is None:
            return []
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)
        scores, indices = self.index.search(query_embedding, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.texts):
                results.append((self.texts[idx], float(score)))
        return results

    def save(self, name: str):
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_dir / f"{name}.index"))
        np.save(self.index_dir / f"{name}_texts.npy", np.array(self.texts))
        logger.info("Saved FAISS index and texts for %s", name)

    def load(self, name: str):
        index_path = self.index_dir / f"{name}.index"
        texts_path = self.index_dir / f"{name}_texts.npy"
        if index_path.exists() and texts_path.exists():
            self.index = faiss.read_index(str(index_path))
            self.texts = np.load(texts_path, allow_pickle=True).tolist()
            logger.info("Loaded FAISS index with %d vectors", self.index.ntotal)
            return True
        return False