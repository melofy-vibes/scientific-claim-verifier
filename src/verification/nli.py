"""Natural Language Inference with safeguards."""
import logging
from typing import List, Tuple, Optional
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from ..embedding.embedder import Embedder

logger = logging.getLogger(__name__)

class NLIModel:
    def __init__(self, model_name: str = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli",
                 confidence_threshold: float = 0.65,
                 similarity_threshold: float = 0.5,
                 embedder: Optional[Embedder] = None):
        logger.info("Loading NLI model %s", model_name)
        self.device = torch.device("cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name).to(self.device)
        self.model.eval()
        self.id2label = self.model.config.id2label
        self.confidence_threshold = confidence_threshold
        self.similarity_threshold = similarity_threshold
        self.embedder = embedder

    def predict(self, premise: str, hypothesis: str,
                premise_emb: Optional[np.ndarray] = None,
                hypothesis_emb: Optional[np.ndarray] = None) -> Tuple[str, float]:
        """Return (label, confidence) after applying safeguards."""
        label, conf = self._raw_predict(premise, hypothesis)
        if label == "CONTRADICTS":
            # Confidence threshold
            if conf < self.confidence_threshold:
                logger.debug("Downgrading CONTRADICTS due to low confidence %.3f", conf)
                return "NEUTRAL", conf
            # Similarity check
            if self.embedder and premise_emb is not None and hypothesis_emb is not None:
                sim = self._cosine(premise_emb, hypothesis_emb)
                if sim < self.similarity_threshold:
                    logger.debug("Downgrading CONTRADICTS due to low similarity %.3f", sim)
                    return "NEUTRAL", conf
        return label, conf

    def batch_predict(self, premises: List[str], hypothesis: str,
                      premise_embs: Optional[np.ndarray] = None) -> List[Tuple[str, float]]:
        """Batch predict with the same hypothesis."""
        if not premises:
            return []
        # Get raw predictions
        raw_labels, raw_confs = self._batch_raw_predict(premises, hypothesis)

        # Compute hypothesis embedding once
        hyp_emb = None
        if self.embedder:
            hyp_emb = self.embedder.embed([hypothesis])[0]

        results = []
        for i, (label, conf) in enumerate(zip(raw_labels, raw_confs)):
            prem_emb = premise_embs[i] if premise_embs is not None else None
            new_label, new_conf = self._apply_safeguards(label, conf, prem_emb, hyp_emb)
            results.append((new_label, new_conf))
        return results

    def _raw_predict(self, premise: str, hypothesis: str) -> Tuple[str, float]:
        inputs = self.tokenizer(premise, hypothesis, return_tensors="pt",
                                truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1).squeeze()
        label_id = torch.argmax(probs).item()
        label = self.id2label[label_id].upper()
        conf = probs[label_id].item()
        # Normalize labels
        if label in ("ENTAILMENT", "ENTAILS"):
            return "SUPPORTS", conf
        elif label in ("CONTRADICTION", "CONTRADICTS"):
            return "CONTRADICTS", conf
        return "NEUTRAL", conf

    def _batch_raw_predict(self, premises: List[str], hypothesis: str):
        batch_size = len(premises)
        features = self.tokenizer(premises, [hypothesis] * batch_size,
                                  padding=True, truncation=True, max_length=512,
                                  return_tensors="pt")
        with torch.no_grad():
            outputs = self.model(**features)
        probs = torch.softmax(outputs.logits, dim=-1)
        labels_ids = torch.argmax(probs, dim=-1)
        raw_labels = []
        raw_confs = []
        for i in range(batch_size):
            lid = labels_ids[i].item()
            lbl = self.id2label[lid].upper()
            conf = probs[i, lid].item()
            if lbl in ("ENTAILMENT", "ENTAILS"):
                raw_labels.append("SUPPORTS")
            elif lbl in ("CONTRADICTION", "CONTRADICTS"):
                raw_labels.append("CONTRADICTS")
            else:
                raw_labels.append("NEUTRAL")
            raw_confs.append(conf)
        return raw_labels, raw_confs

    def _apply_safeguards(self, label: str, confidence: float,
                          premise_emb: Optional[np.ndarray],
                          hypothesis_emb: Optional[np.ndarray]) -> Tuple[str, float]:
        if label == "CONTRADICTS":
            if confidence < self.confidence_threshold:
                return "NEUTRAL", confidence
            if premise_emb is not None and hypothesis_emb is not None:
                sim = self._cosine(premise_emb, hypothesis_emb)
                if sim < self.similarity_threshold:
                    return "NEUTRAL", confidence
        return label, confidence

    @staticmethod
    def _cosine(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)