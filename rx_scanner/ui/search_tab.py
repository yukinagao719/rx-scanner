from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
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


class SearchTab(QWidget):
    """薬品検索タブクラス"""

    def __init__(self):
        super().__init__()
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)

        # データベース管理クラス初期化
        try:
            self.db_manager = DatabaseManager()
            self.db_connected = True

        except Exception as e:
            self.db_manager = None
            self.db_connected = False
            print(f"Database initialization failed: {e}")

        self.init_ui()

    def init_ui(self):
        """UI初期化"""
        # メインレイアウト
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
        if not self.db_connected:
            self.search_status.setText(
                "データベース接続エラー：ダミーデータで動作します"
            )

    def setup_search_area(self, parent_layout):
        """検索エリア設定"""
        search_group = QGroupBox("薬剤検索")
        search_layout = QVBoxLayout(search_group)

        # 検索入力エリア
        input_layout = QHBoxLayout()

        # ラベル
        medicine_label = QLabel("薬剤名：")

        # 検索窓
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "薬剤名を入力してください（例：アスピリン）"
        )
        self.search_input.setFont(QFont("", 12))

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

        search_layout.addLayout(input_layout)
        search_layout.addWidget(self.search_status)

        parent_layout.addWidget(search_group)

        # シグナル接続
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.returnPressed.connect(self.perform_search)
        self.search_button.clicked.connect(self.perform_search)
        self.clear_button.clicked.connect(self.clear_search)

    def setup_results_area(self, parent):
        """検索結果エリア設定"""
        results_widget = QWidget()
        layout = QVBoxLayout(results_widget)

        # グループボックス
        group = QGroupBox("検索結果")
        group_layout = QVBoxLayout(group)

        # 結果カウント表示
        self.result_count_label = QLabel("0件")

        # 検索結果リスト
        self.results_list = QListWidget()
        self.results_list.setMinimumWidth(300)
        self.results_list.setAlternatingRowColors(True)

        group_layout.addWidget(self.result_count_label)
        group_layout.addWidget(self.results_list)

        layout.addWidget(group)
        parent.addWidget(results_widget)

        # シグナル接続
        self.results_list.itemClicked.connect(self.on_medicine_selected)

    def setup_detail_area(self, parent):
        """詳細表示・操作エリア設定"""
        detail_widget = QWidget()
        layout = QVBoxLayout(detail_widget)

        # 薬品詳細グループ
        detail_group = QGroupBox("薬品詳細情報")
        detail_layout = QVBoxLayout(detail_group)

        # 詳細情報表示
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText("薬品を選択すると詳細情報が表示されます")
        self.detail_text.setMinimumSize(350, 300)

        detail_layout.addWidget(self.detail_text)

        # 操作ボタングループ
        action_group = QGroupBox("操作")
        action_layout = QVBoxLayout(action_group)

        # 追加ボタン
        self.add_button = QPushButton("処方箋処理タブに追加")
        self.add_button.setEnabled(False)

        # お気に入り追加ボタン（将来機能）
        self.favorite_button = QPushButton("お気に入りに追加")
        self.favorite_button.setEnabled(False)

        action_layout.addWidget(self.add_button)
        action_layout.addWidget(self.favorite_button)
        action_layout.addStretch()

        layout.addWidget(detail_group)
        layout.addWidget(action_group)
        parent.addWidget(detail_widget)

        # シグナル接続
        self.add_button.clicked.connect(self.add_to_prescription_tab)

    def on_search_text_changed(self, text):
        """インクリメンタルサーチ"""
        if len(text) >= 2:
            self.search_timer.start(500)  # 500ms後に検索実行

        else:
            self.search_timer.stop()
            self.clear_results()

    def perform_search(self):
        """検索実行"""
        search_text = self.search_input.text().strip()

        if not search_text:
            self.clear_results()
            return

        if len(search_text) < 2:
            self.search_status.setText("2文字以上入力してください")
            return

        # 実際のデータベース検索
        self.search_status.setText("検索中...")

        try:
            if self.db_connected and self.db_manager:
                results = self.db_manager.search_medicines(search_text, limit=100)
                self.display_search_results(results, search_text)
            else:
                # データベースが使用できない場合はダミーデータで検索
                self.simulate_search(search_text)
        except Exception as e:
            self.search_status.setText(f"検索エラー：{str(e)}")
            QMessageBox.warning(
                self, "検索エラー", f"検索中にエラーが発生しました：\n{str(e)}"
            )

    def display_search_results(self, results, search_text):
        """検索結果を表示"""
        # 結果をリストに追加
        self.results_list.clear()

        for med in results:
            # リストアイテムのテキスト作成
            price_text = f"¥{med['price']:.2f}" if med.get("price") else "価格未設定"
            maker_text = med.get("manufacturer", "不明") or "不明"
            item_text = f"{med['product_name']} | {maker_text} | {price_text}"

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, med)
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

    def simulate_search(self, search_text):
        """検索シミュレーション（DBが使用できない場合のフォールバック）"""
        # ダミー薬品データ
        dummy_medicines = [
            {
                "product_name": "アスピリン錠100mg",
                "ingredient_name": "アスピリン",
                "specification": "100mg1錠",
                "classification": "内用薬",
                "price": 5.90,
                "manufacturer": "バイエル薬品",
            },
            {
                "product_name": "アスピリン錠81mg",
                "ingredient_name": "アスピリン",
                "specification": "81mg1錠",
                "classification": "内用薬",
                "price": 5.40,
                "manufacturer": "バイエル薬品",
            },
            {
                "product_name": "アスピリン腸溶錠100mg",
                "ingredient_name": "アスピリン",
                "specification": "100mg1錠",
                "classification": "内用薬",
                "price": 6.10,
                "manufacturer": "武田薬品",
            },
            {
                "product_name": "ロキソプロフェン錠60mg",
                "ingredient_name": "ロキソプロフェンナトリウム水和物",
                "specification": "60mg1錠",
                "classification": "内用薬",
                "price": 9.60,
                "manufacturer": "第一三共",
            },
            {
                "product_name": "ロキソニン錠60mg",
                "ingredient_name": "ロキソプロフェンナトリウム水和物",
                "specification": "60mg1錠",
                "classification": "内用薬",
                "price": 22.10,
                "manufacturer": "第一三共",
            },
            {
                "product_name": "カロナール錠200mg",
                "ingredient_name": "アセトアミノフェン",
                "specification": "200mg1錠",
                "classification": "内用薬",
                "price": 5.70,
                "manufacturer": "あゆみ製薬",
            },
            {
                "product_name": "カロナール錠300mg",
                "ingredient_name": "アセトアミノフェン",
                "specification": "300mg1錠",
                "classification": "内用薬",
                "price": 6.20,
                "manufacturer": "あゆみ製薬",
            },
            {
                "product_name": "タイレノールA",
                "ingredient_name": "アセトアミノフェン",
                "specification": "300mg1錠",
                "classification": "内用薬",
                "price": 15.80,
                "manufacturer": "東亜薬品",
            },
        ]

        # 検索文字列でフィルタリング（ひらがな→カタカナ変換対応）
        search_lower = search_text.lower()
        search_katakana = self.hiragana_to_katakana(search_text)
        filtered_medicines = [
            med
            for med in dummy_medicines
            if search_lower in med["product_name"].lower()
            or search_lower in med["ingredient_name"].lower()
            or search_katakana in med["product_name"]
            or search_katakana in med["ingredient_name"]
        ]

        self.display_search_results(filtered_medicines, search_text)

    def clear_search(self):
        """検索クリア"""
        self.search_input.clear()
        self.clear_results()

    def clear_results(self):
        """検索結果クリア"""
        self.results_list.clear()
        self.result_count_label.setText("0件")
        self.search_status.setText("薬剤名を入力して検索してください")
        self.detail_text.clear()
        self.add_button.setEnabled(False)

    def on_medicine_selected(self, item):
        """薬剤選択時"""
        medicine_data = item.data(Qt.ItemDataRole.UserRole)
        if medicine_data:
            self.show_medicine_detail(medicine_data)
            self.add_button.setEnabled(True)
            self.selected_medicine = medicine_data

    def show_medicine_detail(self, medicine_data):
        """薬剤詳細情報表示"""
        detail_html = f"""
        <h3 style="color: #007ACC;">
            {medicine_data["product_name"]}
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
                {medicine_data.get("specification", "不明")}</td>
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
        この薬品の詳細な効能・効果、用法・用量、副作用等の情報は、
        実際の添付文書を確認してください。
        </p>
        <p style="font-size: 12px; color: #888; margin-top: 20px;">
        ※ 本システムの薬剤情報は参考用です。必ず最新の添付文書をご確認ください。
        </p>
        """

        self.detail_text.setHtml(detail_html)

    def hiragana_to_katakana(self, text):
        """ひらがなをカタカナに変換"""
        katakana_text = ""
        for char in text:
            # ひらがなの範囲 (U+3041-U+3096)
            if 0x3041 <= ord(char) <= 0x3096:
                # カタカナに変換 (U+30A1-U+30F6)
                katakana_text += chr(ord(char) + 0x60)
            else:
                katakana_text += char
        return katakana_text

    def add_to_prescription_tab(self):
        """処方箋処理タブに薬剤追加"""
        if not hasattr(self, "selected_medicine"):
            return
        try:
            # メインウィンドウから処方箋タブを取得
            prescription_tab = self.window().prescription_tab

            # 薬剤リストに追加
            medicine_text = (
                f"✓ {self.selected_medicine['product_name']} | "
                f"¥{self.selected_medicine['price']}"
            )
            prescription_tab.medicine_list.addItem(medicine_text)

            # 成功メッセージ
            QMessageBox.information(
                self,
                "追加完了",
                f"「{self.selected_medicine['product_name']}」を処方箋処理タブに追加しました。",
            )
            # メインタブに切り替え
            self.window().tab_widget.setCurrentIndex(0)

        except Exception as e:
            QMessageBox.critical(
                self, "エラー", f"薬品の追加中にエラーが発生しました:\n{str(e)}"
            )
