"""Detect language of input text using langdetect."""
import logging
from langdetect import detect, DetectorFactory

# Ensure consistent results
DetectorFactory.seed = 0
logger = logging.getLogger(__name__)

def detect_language(text: str) -> str:
    """Return 'fa' for Persian, 'en' for English, or other codes."""
    try:
        lang = detect(text)
        logger.info("Detected language: %s", lang)
        return lang
    except Exception as e:
        logger.warning("Language detection failed: %s", e)
        return "en"  # fallback