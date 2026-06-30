"""Localization system loading JSON translations."""
import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

class LocalizationManager:
    def __init__(self, locales_dir: str = "locales"):
        self.locales_dir = Path(locales_dir)
        self.current_lang = "en"
        self.strings: Dict[str, str] = {}
        self.load_language(self.current_lang)

    def load_language(self, lang: str):
        file_path = self.locales_dir / f"{lang}.json"
        if not file_path.exists():
            logger.warning("Locale file %s not found, falling back to en", file_path)
            file_path = self.locales_dir / "en.json"
        with open(file_path, "r", encoding="utf-8") as f:
            self.strings = json.load(f)
        self.current_lang = lang
        logger.info("Loaded locale: %s", lang)

    def get(self, key: str, default: str = "") -> str:
        return self.strings.get(key, default)