import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtWidgets import QApplication

from rx_scanner.ui.main_window import MainWindow


def setup_logging():
    """ログ設定（ファイル + 標準出力）"""
    # ログディレクトリ作成
    if sys.platform == "darwin":  # macOS
        log_dir = Path.home() / "Library" / "Logs" / "RXScanner"
    elif sys.platform == "win32":  # Windows
        log_dir = Path.home() / "AppData" / "Local" / "RXScanner" / "Logs"
    else:  # Linux
        log_dir = Path.home() / ".local" / "share" / "RXScanner" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    # ログフォーマット
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # ルートロガー取得
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 既存のハンドラーをクリア
    root_logger.handlers.clear()

    # ファイルハンドラー（ローテーション: 5MB x 3ファイル）
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    # ハンドラー追加
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    root_logger.info(f"log_file: {log_file}")


def main():
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("RX Scanner")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("CuriFun")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
