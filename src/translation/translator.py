"""Translation service using Google Translate (free)."""
import logging
from deep_translator import GoogleTranslator
from functools import lru_cache

logger = logging.getLogger(__name__)

class Translator:
    def __init__(self):
        # GoogleTranslator is stateless; we can create per call or reuse.
        self.fa_to_en = GoogleTranslator(source='fa', target='en')
        self.en_to_fa = GoogleTranslator(source='en', target='fa')

    @lru_cache(maxsize=200)
    def translate_fa_to_en(self, text: str) -> str:
        """Translate Persian text to English. Cached for repeated claims."""
        if not text.strip():
            return text
        try:
            result = self.fa_to_en.translate(text)
            logger.info("Translated FA->EN: %s", result)
            return result
        except Exception as e:
            logger.error("FA->EN translation error: %s", e)
            raise

    @lru_cache(maxsize=200)
    def translate_en_to_fa(self, text: str) -> str:
        """Translate English text to Persian."""
        if not text.strip():
            return text
        try:
            result = self.en_to_fa.translate(text)
            logger.info("Translated EN->FA: %s", result)
            return result
        except Exception as e:
            logger.error("EN->FA translation error: %s", e)
            raise

    def translate_batch_en_to_fa(self, texts: list) -> list:
        """Translate a list of English strings to Persian (not batched API, one by one)."""
        return [self.translate_en_to_fa(t) for t in texts]