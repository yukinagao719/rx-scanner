import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rx_scanner.ui.main_window import MainWindow  # noqa: E402


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RX Scanner")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("CuriFun")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
