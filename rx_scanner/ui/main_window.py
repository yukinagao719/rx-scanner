"""
メインウィンドウ

処方箋OCRタブと薬剤検索タブを提供するアプリケーションのメインウィンドウ
メニューバー、ステータスバー、タブ切り替え機能を実装
"""

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .prescription_tab import PrescriptionTab
from .search_tab import SearchTab


class MainWindow(QMainWindow):
    """アプリケーションのメインウィンドウ"""

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_menubar()
        self.setup_statusbar()

    def closeEvent(self, event):
        """ウィンドウを閉じる時の処理"""
        # 保存されていない薬剤リストがあるかチェック
        if self.prescription_tab.confirmed_list.count() > 0:
            reply = QMessageBox.question(
                self,
                "終了確認",
                "確定済みの薬剤リストがあります。\n"
                "保存せずに終了しますか？\n\n"
                "※保存していないデータは失われます。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            # 薬剤リストが空の場合は確認なしで終了
            event.accept()

    def init_ui(self):
        """UI初期化（ウィンドウ設定、タブ作成）"""
        self.setWindowTitle("RX Scanner")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        self.tab_widget = QTabWidget()

        self.prescription_tab = PrescriptionTab()
        self.search_tab = SearchTab()

        self.tab_widget.addTab(self.prescription_tab, "Prescription")
        self.tab_widget.addTab(self.search_tab, "Search")
        layout.addWidget(self.tab_widget)

        # タブ切り替え時のシグナル接続
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def setup_menubar(self):
        """メニューバー設定"""
        menubar = self.menuBar()

        # ファイルメニュー
        file_menu = menubar.addMenu("ファイル名（&F）")

        # 処方箋読み込み
        open_action = QAction("処方箋を開く（&O）", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.prescription_tab.on_open_image)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        # 終了
        exit_action = QAction("終了（&X）", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ヘルプメニュー
        help_menu = menubar.addMenu("ヘルプ（&H）")

        # バージョン情報
        about_action = QAction("バージョン情報（&A）", self)
        about_action.triggered.connect(self.on_show_about)
        help_menu.addAction(about_action)

    def setup_statusbar(self):
        """ステータスバー設定"""
        self.statusbar = self.statusBar()
        self.statusbar.showMessage("準備完了")

    def on_tab_changed(self, index):
        """タブ切り替え時の処理"""
        if index == 0:
            self.statusbar.showMessage("処方箋OCRタブ")
        elif index == 1:
            self.statusbar.showMessage("薬剤検索タブ")

    def on_show_about(self):
        """バージョン情報表示"""
        QMessageBox.about(
            self,
            "RX Scannerについて",
            """
            <h3>RX Scanner v0.1.0</h3>
            <p>処方箋OCRアプリ</p>
            <p>開発者：Yuki Nagao</p>
            <p>技術スタック：PySide6, OpenCV, Tesseract OCR</p>
        """,
        )
