import logging

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from rx_scanner.database.db_manager import DatabaseManager


class SearchTab(QWidget):
    def __init__(self):
        super().__init__()
        self.logegr = logging.getLogger(__name__)

        self.selected_medicine = None

        try:
            self.db_manager = DatabaseManager()

        except Exception as e:
            self.db_manager = None
            self.logger.error(f"Database initialization failed: {e}")

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.on_perform_search)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        self.setup_search_area(main_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        self.setup_results_area(splitter)
        self.setup_detail_area(splitter)

        splitter.setSizes([500, 400])

        if not self.db_manager:
            self.search_status.setText("DB接続エラー: ダミーデータで動作します")

    def setup_search_area(self, parent):
        group = QGroupBox("薬剤検索")
        group_layout = QVBoxLayout(group)

        input_layout = QHBoxLayout()

        madicine_label = QLabel("薬剤名：")

        search_input = QLineEdit()
        search_input.setPlaceholderText("薬剤名を入力してください")
        search_input.setFont(QFont(""), 12)

        self.search_button = QPushButton("検索")
        self.search_button.setMinimumWidth(80)
        self.clear_button = QPushButton("クリア")
        self.clear_button.setMinimumWidth(80)
