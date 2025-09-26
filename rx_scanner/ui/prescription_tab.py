from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class OCRWorker(QThread):
    """OCR処理用ワーカースレッド"""

    finished = Signal(str)  # OCR結果
    error = Signal(str)  # エラーメッセージ

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path

    def run(self):
        """OCR処理実行"""
        try:
            # 現在はダミーテキスト
            dummy_result = """
            アスピリン錠100mg
            1回1錠 1日3回 毎食後
            7日分
            ロキソプロフェン錠60mg
            1回1錠 1日3回 毎食後
            3日分
            """
            self.finished.emit(dummy_result.strip())
        except Exception as e:
            self.error.emit(str(e))


class PrescriptionTab(QWidget):
    """処方箋処理タブクラス"""

    def __init__(self):
        super().__init__()
        self.current_image_path = None
        self.ocr_worker = None
        self.init_ui()

    def init_ui(self):
        """UI初期化"""
        # メインレイアウト（水平分割）
        main_layout = QHBoxLayout(self)

        # スプリッター作成
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 左側: 画像表示エリア
        self.setup_image_area(splitter)

        # 中央: OCR結果・編集エリア
        self.setup_ocr_area(splitter)

        # 右側: 確定薬品リスト・出力エリア
        self.setup_output_area(splitter)

        # スプリッターの初期比率設定
        splitter.setSizes([400, 400, 300])

    def setup_image_area(self, parent):
        """画像表示エリアを設定"""
        image_widget = QWidget()
        layout = QVBoxLayout(image_widget)

        # グループボックス
        group = QGroupBox("処方箋画像")
        group_layout = QVBoxLayout(group)

        # 画像表示ラベル
        self.image_label = QLabel("画像をドラッグ＆ドロップ\nまたは下のボタンで選択")
        self.image_label.setMinimumWidth(350)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 10px;
                background-color: #f9f9f9;
                color: #666;
                font-size: 14px;
            }
        """)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(True)

        # ボタン
        self.open_button = QPushButton("画像を開く")
        self.ocr_button = QPushButton("OCR実行")
        self.ocr_button.setEnabled(False)

        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        # レイアウト追加
        group_layout.addWidget(self.image_label)
        group_layout.addWidget(self.open_button)
        group_layout.addWidget(self.ocr_button)
        group_layout.addWidget(self.progress_bar)

        layout.addWidget(group)
        parent.addWidget(image_widget)

        # シグナル接続
        self.open_button.clicked.connect(self.open_image)
        self.ocr_button.clicked.connect(self.run_ocr)

    def setup_ocr_area(self, parent):
        """OCR結果"""
        ocr_widget = QWidget()
        layout = QVBoxLayout(ocr_widget)

        # グループボックス
        group = QGroupBox("OCR結果・編集")
        group_layout = QVBoxLayout(group)

        # OCR結果表示・編集
        self.ocr_text = QTextEdit()
        self.ocr_text.setPlaceholderText(
            "OCR結果がここに表示されます。\n手動で修正も可能です。"
        )

        # 薬剤照合ボタン
        self.match_button = QPushButton("薬剤照合実行")
        self.match_button.setEnabled(False)

        # レイアウト追加
        group_layout.addWidget(self.ocr_text)
        group_layout.addWidget(self.match_button)

        layout.addWidget(group)
        parent.addWidget(ocr_widget)

        # シグナル接続
        self.match_button.clicked.connect(self.match_medicines)

    def setup_output_area(self, parent):
        """出力エリア設定"""
        output_widget = QWidget()
        layout = QVBoxLayout(output_widget)

        # グループボックス
        group = QGroupBox("確定薬剤リスト")
        group_layout = QVBoxLayout(group)

        # 確定薬剤リスト
        self.medicine_list = QListWidget()

        # ボタン
        self.remove_button = QPushButton("選択項目を削除")
        self.clear_button = QPushButton("リストをクリア")
        self.export_button = QPushButton("CSVエクスポート")

        # レイアウト追加
        group_layout.addWidget(self.medicine_list)
        group_layout.addWidget(self.remove_button)
        group_layout.addWidget(self.clear_button)
        group_layout.addWidget(self.export_button)

        layout.addWidget(group)
        parent.addWidget(output_widget)
        # シグナル接続
        self.remove_button.clicked.connect(self.remove_selected_medicine)
        self.clear_button.clicked.connect(self.clear_medicine_list)
        self.export_button.clicked.connect(self.export_csv)

    def open_image(self):
        """画像ファイルを開く"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "処方箋画像を選択",
            "",
            "画像ファイル (*.png *.jpg *.jpeg *.bmp *.tiff)",
        )

        if file_path:
            self.load_image()

    def load_image(self, file_path):
        """画像を読み込んで表示"""
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # 画像をラベルサイズに合わせてスケール
                scaled_pixmap = pixmap.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.image_label.setPixmap(scaled_pixmap)
                self.current_image_path = file_path
                self.ocr_button.setEnabled(True)

                # ステータス更新
                self.window().status_bar.showMessage(
                    f"画像読み込み完了: {Path(file_path).name}"
                )
            else:
                QMessageBox.warning(
                    self, "エラー", "画像ファイルを読み込めませんでした。"
                )
        except Exception as e:
            QMessageBox.critical(
                self, "エラー", f"画像読み込み中にエラーが発生しました:\n{str(e)}"
            )

    def run_ocr(self):
        """OCR処理を実行"""
        if not self.current_image_path:
            return

        # UI状態変更
        self.ocr_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        # OCRワーカー起動
        self.ocr_worker = OCRWorker(self.current_image_path)
        self.ocr_worker.finished.connect(self.on_ocr_finished)
        self.ocr_worker.error.connect(self.on_ocr_error)
        self.ocr_worker.start()

    def on_ocr_finished(self, result):
        """OCR処理完了時"""
        self.ocr_text.setText(result)
        self.match_button.setEnabled(True)

        # UI状態復元
        self.ocr_button.setEnabled(True)
        self.progress_bar.setVisible(False)

        # ステータス更新
        self.window().status_bar.showMessage("OCR処理完了")

    def on_ocr_error(self, error):
        """OCR処理エラー時"""
        QMessageBox.critical(
            self, "OCRエラー", f"OCR処理中にエラーが発生しました：\n{error}"
        )

        # UI状態復元
        self.ocr_button.setEnabled(True)
        self.progress_bar.setVisible(False)

    def match_medicines(self):
        """薬剤照合処理"""
        # 現在はダミー処理
        ocr_text = self.ocr_text.toPlainText()
        if ocr_text.strip():
            # ダミーで薬剤リストに追加
            lines = [line.strip() for line in ocr_text.strip("\n") if line.strip()]
            for line in lines:
                if any(keyword in line for keyword in ["錠", "mg", "回", "日"]):
                    self.medicine_list.addItem(f"✓ {line}")

            self.window().status_bar.showMessage("薬剤照合完了")
        else:
            QMessageBox.warning(self, "警告", "OCR結果が空です。")

    def remove_selected_medicine(self):
        """選択された薬剤を削除"""
        current_item = self.medicine_list.currentItem()
        if current_item:
            self.medicine_list.takeItem(self.medicine_list.row(current_item))

    def clear_medicine_list(self):
        """薬剤リストをクリア"""
        self.medicine_list.clear()

    def export_csv(self):
        """CSVエクスポート"""
        if self.medicine_list.count() == 0:
            QMessageBox.warning(self, "警告", "エクスポートする薬剤がありません。")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "CSVファイルを保存", "prescription_data.csv", "CSVファイル (*.csv)"
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("薬品名,数量,備考\n")
                    for i in range(self.medicine_list.count()):
                        item_text = self.medicine_list.item(i).text()
                        f.write(f'"{item_text.replace("✓ ", "")}","",""\n')

                QMessageBox.information(
                    self, "完了", f"CSVファイルを保存しました:\n{file_path}"
                )
                self.window().status_bar.showMessage("CSV出力完了")
            except Exception as e:
                QMessageBox.critical(
                    self, "エラー", f"CSV出力中にエラーが発生しました:\n{str(e)}"
                )
