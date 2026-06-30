"""Background thread for running the verification pipeline."""
import logging
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class VerificationThread(QThread):
    """Runs the verification pipeline off the UI thread, with language support."""
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, pipeline, claim, target_lang="auto"):
        super().__init__()
        self.pipeline = pipeline
        self.claim = claim
        self.target_lang = target_lang

    def run(self):
        try:
            result = self.pipeline.run(self.claim, target_lang=self.target_lang)
            self.result_ready.emit(result)
        except Exception as e:
            logger.exception("Pipeline failed")
            self.error_occurred.emit(str(e))