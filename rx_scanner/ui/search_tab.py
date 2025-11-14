"""
薬剤検索タブ

薬剤マスタDBから薬剤名・成分名で全文検索を行う機能を提供
リアルタイム検索、検索結果表示、詳細情報表示に対応
"""

import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from rx_scanner.database.db_manager import DatabaseManager
from rx_scanner.utils.text_utils import normalize_to_katakana


class SearchTab(QWidget):
    """薬剤検索タブクラス"""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        self.selected_medicine = None

        # DB接続
        try:
            self.db_manager = DatabaseManager()

        except Exception as e:
            self.db_manager = None
            self.logger.error(f"Database initialization failed: {e}")

        # デバウンス検索用タイマー
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.on_perform_search)

        self.init_ui()

    def init_ui(self):
        """UI初期化"""
        main_layout = QVBoxLayout(self)

        # 検索エリア
        self.setup_search_area(main_layout)

        # 結果表示エリア（水平分割）
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 左側: 検索結果リスト
        self.setup_results_area(splitter)

        # 右側: 詳細表示・操作エリア
        self.setup_detail_area(splitter)

        # スプリッターの初期比率
        splitter.setSizes([500, 400])

        # DB接続状態を表示
        if not self.db_manager:
            self.search_status.setText("DB接続エラー：ダミーデータで動作します")

    def setup_search_area(self, parent):
        """検索入力エリアのUI構築"""
        search_group = QGroupBox("薬剤検索")
        group_layout = QVBoxLayout(search_group)

        # 検索入力エリア
        input_layout = QHBoxLayout()

        # ラベル
        medicine_label = QLabel("薬剤名：")

        # 検索窓
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "薬剤名を入力してください（例：アスピリン）"
        )

        # ボタン
        self.search_button = QPushButton("検索")
        self.search_button.setMinimumWidth(80)
        self.clear_button = QPushButton("クリア")
        self.clear_button.setMinimumWidth(80)

        # 検索状態表示
        self.search_status = QLabel("薬剤名を入力して検索してください")
        self.search_status.setStyleSheet("color: #666; font-style: italic;")

        # レイアウト追加
        input_layout.addWidget(medicine_label)
        input_layout.addWidget(self.search_input)
        input_layout.addWidget(self.search_button)
        input_layout.addWidget(self.clear_button)

        group_layout.addLayout(input_layout)
        group_layout.addWidget(self.search_status)

        parent.addWidget(search_group)

        # シグナル接続
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.returnPressed.connect(self.on_perform_search)
        self.search_button.clicked.connect(self.on_perform_search)
        self.clear_button.clicked.connect(self.on_clear_search)

    def setup_results_area(self, parent):
        """検索結果リスト表示エリアのUI構築"""
        results_group = QGroupBox("検索結果")
        group_layout = QVBoxLayout(results_group)

        # 結果カウント表示
        self.result_count_label = QLabel("0件")

        # 検索結果リスト
        self.results_list = QListWidget()
        self.results_list.setMinimumWidth(300)
        self.results_list.setAlternatingRowColors(True)

        group_layout.addWidget(self.result_count_label)
        group_layout.addWidget(self.results_list)

        parent.addWidget(results_group)

        # シグナル接続
        self.results_list.itemClicked.connect(self.on_medicine_selected)

    def setup_detail_area(self, parent):
        """薬剤詳細情報と操作ボタンのUI構築"""
        detail_widget = QWidget()
        layout = QVBoxLayout(detail_widget)

        # 薬剤詳細グループ
        detail_group = QGroupBox("薬剤詳細情報")
        detail_layout = QVBoxLayout(detail_group)

        # 詳細情報表示
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText("薬剤を選択すると詳細情報が表示されます")
        self.detail_text.setMinimumSize(350, 300)

        detail_layout.addWidget(self.detail_text)

        # 操作ボタングループ
        action_group = QGroupBox("操作")
        action_layout = QVBoxLayout(action_group)

        # 追加ボタン
        self.add_button = QPushButton("処方箋OCRタブに追加")
        self.add_button.setEnabled(False)

        action_layout.addWidget(self.add_button)
        action_layout.addStretch()

        layout.addWidget(detail_group)
        layout.addWidget(action_group)
        parent.addWidget(detail_widget)

        # シグナル接続
        self.add_button.clicked.connect(self.on_add_to_prescription_tab)

    def on_search_text_changed(self, text):
        """検索テキスト変更イベント（デバウンス処理）"""
        if len(text) >= 2:
            # タイマーをリセットして500ms後に検索実行
            self.search_timer.start(500)
        else:
            self.search_timer.stop()
            self._clear_results()

    def on_perform_search(self):
        """検索実行"""
        search_text = self.search_input.text().strip()

        if len(search_text) < 2:
            self._clear_results()
            if search_text:
                self.search_status.setText("2文字以上入力してください")
            return

        search_katakana = normalize_to_katakana(search_text)

        self.search_status.setText("検索中...")

        try:
            if self.db_manager:
                results = self.db_manager.search_medicines(search_katakana, limit=200)
            else:
                # DBが使用できない場合はダミーデータで検索
                results = self._simulate_search(search_katakana)

            self._display_search_results(results, search_text)

        except Exception as e:
            self.search_status.setText(f"検索エラー：{str(e)}")
            QMessageBox.warning(
                self, "検索エラー", f"検索中にエラーが発生しました：\n{str(e)}"
            )

    def on_clear_search(self):
        """検索クリア"""
        self.search_input.clear()
        self._clear_results()

    def on_medicine_selected(self, item):
        """薬剤選択"""
        medicine_data = item.data(Qt.ItemDataRole.UserRole)
        if medicine_data:
            self._show_medicine_detail(medicine_data)
            self.add_button.setEnabled(True)
            self.selected_medicine = medicine_data

    def on_add_to_prescription_tab(self):
        """処方箋処理タブに薬剤追加"""
        if not self.selected_medicine:
            return
        try:
            # メインウィンドウから処方箋タブを取得
            prescription_tab = self.window().prescription_tab

            # 薬剤リストに追加
            medicine_name = self.selected_medicine["medicine_name"]
            medicine_type = self.selected_medicine["medicine_type"]
            price = self.selected_medicine["price"]

            display_text = f"✓ {medicine_name} [{medicine_type}]"
            if price > 0:
                display_text += f" (¥{price:.2f})"

            prescription_tab.confirmed_list.addItem(display_text)

            # 成功メッセージ
            QMessageBox.information(
                self,
                "追加完了",
                f"「{self.selected_medicine['medicine_name']}」を処方箋処理タブに追加しました。",
            )
            # メインタブに切り替え
            self.window().tab_widget.setCurrentIndex(0)

        except Exception as e:
            QMessageBox.critical(
                self, "エラー", f"薬剤の追加中にエラーが発生しました:\n{str(e)}"
            )

    def _clear_results(self):
        """検索結果クリア"""
        self.results_list.clear()
        self.result_count_label.setText("0件")
        self.search_status.setText("薬剤名を入力して検索してください")
        self.detail_text.clear()
        self.add_button.setEnabled(False)

    def _display_search_results(self, results, search_text):
        """検索結果を表示"""
        self.results_list.clear()

        for medicine in results:
            # リストアイテムのテキスト作成
            price_text = (
                f"¥{medicine['price']:.2f}" if medicine["price"] > 0 else "価格未設定"
            )
            manufacturer_text = medicine["manufacturer"]
            item_text = (
                f"{medicine['medicine_name']} | {manufacturer_text} | {price_text}"
            )

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, medicine)
            self.results_list.addItem(item)

        # 検索状態更新
        count = len(results)
        self.result_count_label.setText(f"{count}件")

        if count == 0:
            self.search_status.setText(
                f"「{search_text}」に該当する薬剤が見つかりませんでした"
            )
        elif count > 100:
            self.search_status.setText(
                f"「{search_text}」の検索完了（100件以上のため上位100件のみ表示）"
            )
        else:
            self.search_status.setText(f"「{search_text}」の検索完了")

    def _show_medicine_detail(self, medicine_data):
        """薬剤詳細情報表示"""
        detail_html = f"""
        <h3 style="color: #007ACC;">
            {medicine_data["medicine_name"]}
        </h3>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <tr style="background-color: #f5f5f5;">
                <td style="
                padding: 8px;
                border: 1px solid #ddd;
                font-weight: bold;
                ">
                成分名</td>
                <td style="
                padding: 8px;
                border: 1px solid #ddd;
                ">
                {medicine_data["ingredient_name"]}</td>
            </tr>
            <tr>
                <td style="
                padding: 8px;
                border: 1px solid #ddd;
                font-weight: bold;
                ">
                規格</td>
                <td style="padding: 8px;
                border: 1px solid #ddd;
                ">
                {medicine_data["specification"]}</td>
            </tr>
            <tr style="background-color: #f5f5f5;">
                <td style="
                padding: 8px;
                border: 1px solid #ddd;
                font-weight: bold;
                ">
                区分</td>
                <td style="
                padding: 8px;
                border: 1px solid #ddd;
                ">
                {medicine_data["classification"]}</td>
            </tr>
            <tr>
                <td style="
                padding: 8px;
                border: 1px solid #ddd;
                font-weight: bold;
                ">
                薬価</td>
                <td style="
                padding: 8px;
                border: 1px solid #ddd;
                ">
                ¥{medicine_data["price"]}</td>
            </tr>
            <tr style="background-color: #f5f5f5;">
                <td style="
                padding: 8px;
                border: 1px solid #ddd;
                font-weight: bold;
                ">
                薬剤分類</td>
                <td style="
                padding: 8px;
                border: 1px solid #ddd;
                ">
                {medicine_data["medicine_type"]}</td>
            </tr>
            <tr>
                <td style="
                padding: 8px;
                border: 1px solid #ddd;
                font-weight: bold;
                ">
                メーカー</td>
                <td style="
                padding: 8px;
                border: 1px solid #ddd;
                ">
                {medicine_data["manufacturer"]}</td>
            </tr>
        </table>
        <h4 style="color: #333; margin-top: 20px;">基本情報</h4>
        <p style="line-height: 1.6; color: #555;">
        この薬剤の詳細な効能・効果、用法・用量、副作用等の情報は、
        実際の添付文書を確認してください。
        </p>
        <p style="font-size: 12px; color: #888; margin-top: 20px;">
        ※ 本システムの薬剤情報は参考用です。必ず最新の添付文書をご確認ください。
        </p>
        """

        self.detail_text.setHtml(detail_html)

    def _simulate_search(self, search_katakana):
        """DB接続失敗時のダミーデータ検索"""
        dummy_medicines = [
            {
                "classification": "内用薬",
                "ingredient_name": "アスピリン",
                "specification": "100mg1錠",
                "medicine_name": "アスピリン錠100mg",
                "manufacturer": "バイエル薬剤",
                "price": 5.90,
                "medicine_type": "後発品",
            },
            {
                "classification": "内用薬",
                "ingredient_name": "アスピリン",
                "specification": "81mg1錠",
                "medicine_name": "アスピリン錠81mg",
                "manufacturer": "バイエル薬剤",
                "price": 5.40,
                "medicine_type": "後発品",
            },
            {
                "classification": "内用薬",
                "ingredient_name": "アスピリン",
                "specification": "100mg1錠",
                "medicine_name": "アスピリン腸溶錠100mg",
                "manufacturer": "武田薬剤",
                "price": 6.10,
                "medicine_type": "先発品",
            },
            {
                "classification": "内用薬",
                "ingredient_name": "ロキソプロフェンナトリウム水和物",
                "specification": "60mg1錠",
                "medicine_name": "ロキソプロフェン錠60mg",
                "manufacturer": "第一三共",
                "price": 9.60,
                "medicine_type": "後発品",
            },
            {
                "classification": "内用薬",
                "ingredient_name": "ロキソプロフェンナトリウム水和物",
                "specification": "60mg1錠",
                "medicine_name": "ロキソニン錠60mg",
                "manufacturer": "第一三共",
                "price": 22.10,
                "medicine_type": "先発品",
            },
            {
                "classification": "内用薬",
                "ingredient_name": "アセトアミノフェン",
                "specification": "200mg1錠",
                "medicine_name": "カロナール錠200mg",
                "manufacturer": "あゆみ製薬",
                "price": 5.70,
                "medicine_type": "先発品",
            },
            {
                "classification": "内用薬",
                "ingredient_name": "アセトアミノフェン",
                "specification": "300mg1錠",
                "medicine_name": "カロナール錠300mg",
                "manufacturer": "あゆみ製薬",
                "price": 6.20,
                "medicine_type": "先発品",
            },
            {
                "classification": "内用薬",
                "ingredient_name": "アセトアミノフェン",
                "specification": "300mg1錠",
                "medicine_name": "タイレノールA",
                "manufacturer": "東亜薬剤",
                "price": 15.80,
                "medicine_type": "その他",
            },
        ]

        # 検索文字列でフィルタリング
        filtered_medicines = [
            medicine
            for medicine in dummy_medicines
            if medicine["medicine_name"].startswith(search_katakana)
            or medicine["ingredient_name"].startswith(search_katakana)
        ]

        return filtered_medicines
