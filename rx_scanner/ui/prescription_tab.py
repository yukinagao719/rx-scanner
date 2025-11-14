"""
処方箋OCRタブ

処方箋画像からOCRで薬剤情報を抽出し、DBと照合する機能を提供
画像プレビュー、OCR処理、薬剤リスト管理、CSV出力に対応
"""

import csv
import logging
import os
import re
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from rx_scanner.ui.medicine_selection_dialog import MedicineSelectionDialog
from rx_scanner.utils.ocr_processor import OCRProcessor


class OCRWorker(QThread):
    """OCR処理用ワーカースレッド"""

    finished = Signal(dict)  # OCR結果（抽出されたテキストと薬剤情報）
    error = Signal(str)  # エラーメッセージ

    def __init__(self, image_path):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        self.image_path = image_path

    def run(self):
        """OCR処理実行"""
        try:
            ocr_processor = OCRProcessor()
            result = ocr_processor.process_image(self.image_path)
            self.finished.emit(result)

        except FileNotFoundError as e:
            self.logger.error(f"Image file not found: {self.image_path}")
            self.error.emit(str(e))

        except ValueError as e:
            self.logger.error(f"Image format error: {e}")
            self.error.emit(str(e))

        except Exception as e:
            self.logger.error(f"Unexpected error during OCR processing: {e}")
            self.error.emit(f"予期しないエラーが発生しました:\n{str(e)}")


class PrescriptionTab(QWidget):
    """処方箋OCRタブクラス"""

    def __init__(self):
        super().__init__()

        # 画像関連
        self.current_image_path = None
        self.original_pixmap = None

        # OCR結果
        self.raw_ocr_text = None
        self.extracted_medicines = []

        # ワーカースレッド
        self.ocr_worker = None

        # ドラッグ&ドロップ有効化
        self.setAcceptDrops(True)

        self.init_ui()

    def dragEnterEvent(self, event):
        """ドラッグイベント（ファイルがドラッグされた時）"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """ドロップイベント（ファイルがドロップされた時）"""
        urls = event.mimeData().urls()
        if urls:
            # 最初のファイルのみ処理
            file_path = urls[0].toLocalFile()
            self._load_image(file_path)

    def resizeEvent(self, event):
        """ウィンドウリサイズ時に画像も再スケール"""
        super().resizeEvent(event)
        self._update_image_display()

    def init_ui(self):
        """UI初期化"""
        main_layout = QHBoxLayout(self)

        # 表示エリア（水平分割）
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 左側: 画像表示エリア
        self.setup_image_area(splitter)

        # 中央: OCR結果・編集エリア
        self.setup_ocr_area(splitter)

        # 右側: 確定薬剤リスト・出力エリア
        self.setup_output_area(splitter)

        # スプリッターの初期比率
        splitter.setSizes([400, 300, 400])

    def setup_image_area(self, parent):
        """画像表示エリアを設定"""
        image_group = QGroupBox("処方箋画像")
        group_layout = QVBoxLayout(image_group)

        # 画像表示ラベル
        self.image_label = QLabel("画像をドラッグ＆ドロップ\nまたは\n下のボタンで選択")
        self.image_label.setMinimumWidth(350)
        self.image_label.setStyleSheet("""
            border: 2px dashed #ccc;
            border-radius: 10px;
            background-color: #f9f9f9;
            color: #666;
            font-size: 14px;
        """)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

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

        parent.addWidget(image_group)

        # シグナル接続
        self.open_button.clicked.connect(self.on_open_image)
        self.ocr_button.clicked.connect(self.on_run_ocr)

    def setup_ocr_area(self, parent):
        """OCR結果表示エリアのUI構築"""
        ocr_group = QGroupBox("抽出された薬剤名")
        group_layout = QVBoxLayout(ocr_group)

        # OCR結果リスト
        self.ocr_results_list = QListWidget()
        self.ocr_results_list.setToolTip("右クリックで削除できます")
        self.ocr_results_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        # 全テキスト表示ボタン
        self.show_full_text_button = QPushButton("全テキストを表示")
        self.show_full_text_button.setEnabled(False)

        # 薬剤照合ボタン
        self.match_button = QPushButton("薬剤照合実行")
        self.match_button.setEnabled(False)

        # レイアウト追加
        group_layout.addWidget(self.ocr_results_list)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.show_full_text_button)
        button_layout.addWidget(self.match_button)
        group_layout.addLayout(button_layout)

        parent.addWidget(ocr_group)

        # シグナル接続
        self.ocr_results_list.customContextMenuRequested.connect(
            self.on_show_medicine_context_menu
        )
        self.show_full_text_button.clicked.connect(self.on_show_full_text)
        self.match_button.clicked.connect(self.on_match_medicines)

    def setup_output_area(self, parent):
        """確定薬剤リストと出力機能のUI構築"""
        output_group = QGroupBox("確定薬剤リスト")
        group_layout = QVBoxLayout(output_group)

        # 確定薬剤リスト
        self.confirmed_list = QListWidget()

        # ボタン
        self.remove_button = QPushButton("選択項目を削除")
        self.clear_button = QPushButton("リストをクリア")
        self.export_button = QPushButton("CSVエクスポート")

        # ボタンレイアウト
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.clear_button)

        # レイアウト追加
        group_layout.addWidget(self.confirmed_list)
        group_layout.addLayout(button_layout)
        group_layout.addWidget(self.export_button)

        parent.addWidget(output_group)

        # シグナル接続
        self.remove_button.clicked.connect(self.on_remove_selected_medicine)
        self.clear_button.clicked.connect(self.on_clear_medicine_list)
        self.export_button.clicked.connect(self.on_export_csv)

    def on_open_image(self):
        """画像ファイルを開く"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "処方箋画像を選択",
            "",
            "画像ファイル (*.png *.jpg *.jpeg *.bmp *.tiff *.tif)",
        )

        if file_path:
            self._load_image(file_path)

    def on_run_ocr(self):
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
        # 抽出された薬剤情報を保存
        self.extracted_medicines = result.get("medicines", [])

        # 全テキストを保存
        self.raw_ocr_text = result.get("raw_text", "")

        # OCR結果をリストに表示
        self.ocr_results_list.clear()
        for medicine_data in self.extracted_medicines:
            # display_nameがあればそれを使用（部分一致の場合は成分名）
            medicine_name = (
                medicine_data.get("display_name") or medicine_data["medicine_name"]
            )
            item = QListWidgetItem(medicine_name)
            self.ocr_results_list.addItem(item)

        # ボタンを有効化
        self.show_full_text_button.setEnabled(True)
        self.match_button.setEnabled(True)

        # UI状態復元
        self.ocr_button.setEnabled(True)
        self.progress_bar.setVisible(False)

        # ステータス更新
        medicines_count = len(self.extracted_medicines)
        self.window().statusbar.showMessage(
            f"OCR処理完了 - {medicines_count}件の薬剤を抽出"
        )

    def on_ocr_error(self, error):
        """OCR処理エラー時"""
        QMessageBox.critical(
            self, "OCRエラー", f"OCR処理中にエラーが発生しました：\n{error}"
        )

        # UI状態復元
        self.ocr_button.setEnabled(True)
        self.progress_bar.setVisible(False)

    def on_show_full_text(self):
        """全テキストを表示するダイアログ"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle("OCR全テキスト")
        dialog.setText("OCRで抽出された全テキスト:")
        dialog.setDetailedText(self.raw_ocr_text or "")
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.exec()

    def on_match_medicines(self):
        """薬剤照合処理"""
        if not self.extracted_medicines:
            QMessageBox.warning(self, "警告", "薬剤名がありません。")
            return

        try:
            # 各抽出薬剤について処理
            for medicine_data in self.extracted_medicines:
                has_alternatives = medicine_data.get("has_alternatives", False)

                if has_alternatives:
                    # 代替薬剤がある場合は選択ダイアログを表示
                    dialog = MedicineSelectionDialog(medicine_data, self)
                    if dialog.exec() == dialog.DialogCode.Accepted:
                        selected_medicine = dialog.selected_medicine
                        self._add_medicine_to_confirmed_list(selected_medicine)
                    # キャンセルされた場合は何もしない
                else:
                    # 代替薬剤がない場合は直接追加
                    self._add_medicine_to_confirmed_list(medicine_data)

            self.window().statusbar.showMessage("薬剤照合完了")

        except Exception as e:
            QMessageBox.critical(
                self, "エラー", f"薬剤照合中にエラーが発生しました:\n{str(e)}"
            )

    def on_show_medicine_context_menu(self, position):
        """OCR結果リストの右クリックメニューを表示"""
        # 選択されているアイテムを取得
        current_item = self.ocr_results_list.currentItem()

        if not current_item:
            return

        # メニュー作成
        menu = QMenu()
        delete_action = menu.addAction("削除")

        # メニューを表示してアクションを取得
        action = menu.exec(self.ocr_results_list.mapToGlobal(position))

        # 削除処理
        if action == delete_action:
            row = self.ocr_results_list.row(current_item)
            self.ocr_results_list.takeItem(row)
            # extracted_medicinesリストからも削除
            if 0 <= row < len(self.extracted_medicines):
                del self.extracted_medicines[row]

    def on_remove_selected_medicine(self):
        """選択された薬剤を削除"""
        current_item = self.confirmed_list.currentItem()
        if current_item:
            self.confirmed_list.takeItem(self.confirmed_list.row(current_item))

    def on_clear_medicine_list(self):
        """薬剤リストをクリア"""
        self.confirmed_list.clear()

    def on_export_csv(self):
        """CSVエクスポート"""
        if self.confirmed_list.count() == 0:
            QMessageBox.warning(self, "警告", "エクスポートする薬剤がありません。")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "CSVファイルを保存", "prescription_data.csv", "CSVファイル (*.csv)"
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    # ヘッダー行
                    writer.writerow(
                        ["薬剤名", "分類", "薬価", "用法", "用量", "日数", "備考"]
                    )

                    for i in range(self.confirmed_list.count()):
                        item_text = self.confirmed_list.item(i).text()
                        item_text = item_text.replace("✓ ", "")

                        # 薬剤名、分類、薬価を抽出
                        # 形式: "薬剤名 [分類] (¥薬価)"
                        medicine_type = ""
                        price = ""

                        # 薬価を抽出・削除
                        price_match = re.search(r"\(¥([\d.]+)\)", item_text)
                        if price_match:
                            price = price_match.group(1)
                            item_text = re.sub(r"\s*\(¥[\d.]+\)", "", item_text).strip()

                        # 分類を抽出・削除
                        type_match = re.search(r"\[([^\]]+)\]", item_text)
                        if type_match:
                            medicine_type = type_match.group(1)
                            medicine_name = item_text[: type_match.start()].strip()
                        else:
                            medicine_name = item_text

                        # CSV行を書き込み（用法・用量・日数は空欄 - 今後の拡張用）
                        writer.writerow(
                            [medicine_name, medicine_type, price, "", "", "", ""]
                        )

                QMessageBox.information(
                    self, "完了", f"CSVファイルを保存しました:\n{file_path}"
                )
                self.window().statusbar.showMessage("CSV出力完了")

            except Exception as e:
                QMessageBox.critical(
                    self, "エラー", f"CSV出力中にエラーが発生しました:\n{str(e)}"
                )

    def _load_image(self, file_path):
        """画像を読み込んで表示"""
        try:
            # 画像ファイル存在チェック
            if not os.path.exists(file_path):
                QMessageBox.warning(
                    self,
                    "ファイルエラー",
                    f"画像ファイルが見つかりません:\n{file_path}",
                )
                return

            # ファイルサイズチェック（10MB以上は警告）
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            if file_size > 10:
                reply = QMessageBox.question(
                    self,
                    "大きなファイル",
                    f"ファイルサイズが大きいです ({file_size:.1f}MB)。\n"
                    "処理に時間がかかる可能性があります。続行しますか？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            # サポートされる形式チェック
            supported_formats = [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"]
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in supported_formats:
                QMessageBox.warning(
                    self,
                    "ファイル形式エラー",
                    f"サポートされていない画像形式です: {file_ext}\n\n"
                    f"サポート形式: {', '.join(supported_formats)}",
                )
                return

            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # 元画像を保持
                self.original_pixmap = pixmap
                # 画像をラベルサイズに合わせてスケール
                self._update_image_display()
                self.current_image_path = file_path
                self.ocr_button.setEnabled(True)

                # ステータス更新
                self.window().statusbar.showMessage(
                    f"画像読み込み完了: {Path(file_path).name}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "画像読み込みエラー",
                    "画像ファイルを読み込めませんでした。\n"
                    "ファイルが破損している可能性があります。",
                )
        except PermissionError:
            QMessageBox.critical(
                self,
                "アクセス権限エラー",
                f"ファイルへのアクセス権限がありません:\n{file_path}",
            )
        except Exception as e:
            QMessageBox.critical(
                self, "エラー", f"画像読み込み中にエラーが発生しました:\n{str(e)}"
            )

    def _update_image_display(self):
        """画像表示を更新"""
        if self.original_pixmap:
            scaled_pixmap = self.original_pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled_pixmap)

    def _add_medicine_to_confirmed_list(self, medicine_data):
        """薬剤を確定リストに追加"""
        medicine_name = medicine_data["medicine_name"]
        medicine_type = medicine_data["medicine_type"]
        price = medicine_data["price"]

        # 表示用テキスト作成
        display_text = f"{medicine_name}"
        if medicine_type:
            display_text += f" [{medicine_type}]"
        if price:
            display_text += f" (¥{price:.2f})"

        full_text = f"✓ {display_text}"

        # 重複チェック
        if self._is_duplicate(full_text):
            reply = QMessageBox.question(
                self,
                "重複確認",
                f"この薬剤は既にリストに存在します:\n{display_text}\n\n追加しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self.confirmed_list.addItem(full_text)

    def _is_duplicate(self, medicine_text):
        """確定リスト内の重複チェック"""
        for i in range(self.confirmed_list.count()):
            if self.confirmed_list.item(i).text() == medicine_text:
                return True
        return False
