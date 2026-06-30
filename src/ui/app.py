"""Application entry point for Scientific Claim Verifier & Evidence Explorer."""
import sys
import logging
from src.ui.main_window import MainWindow
from PyQt5.QtWidgets import QApplication



def main():
    """Launch the Scientific Claim Verifier desktop application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()