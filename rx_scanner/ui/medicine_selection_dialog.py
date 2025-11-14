"""
薬剤選択ダイアログ
先発・後発品の選択と価格比較機能
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class MedicineSelectionDialog(QDialog):
    """薬剤選択ダイアログ（先発・後発品選択）"""

    def __init__(self, medicine_data, parent=None):
        """
        Args:
            medicine_data: 関連薬剤情報付きの薬剤データ
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.medicine_data = medicine_data
        self.selected_medicine = None

        self.setWindowTitle("薬剤選択 - 先発・後発品比較")
        self.setModal(True)
        self.resize(800, 600)

        self.init_ui()

    def init_ui(self):
        """UI初期化"""
        layout = QVBoxLayout(self)

        # 元薬剤情報エリア
        self.setup_original_medicine_area(layout)

        # テーブルエリア
        self.setup_table_area(layout)

        # 選択情報エリア
        self.setup_selection_info_area(layout)

        # ボタンエリア
        self.setup_button_area(layout)

        # データをテーブルに読み込み
        self.populate_data()

    def setup_original_medicine_area(self, parent):
        """元薬剤情報エリア設定"""
        original_group = QGroupBox("抽出された薬剤")
        group_layout = QVBoxLayout(original_group)

        # display_nameがあればそれを使用
        medicine_name = (
            self.medicine_data.get("display_name")
            or self.medicine_data["medicine_name"]
        )

        original_info = QLabel(f"薬剤名: {medicine_name}")
        original_info.setStyleSheet(
            "font-size: 14px; padding: 10px; background-color: #f0f0f0;"
        )
        group_layout.addWidget(original_info)
        parent.addWidget(original_group)

    def setup_table_area(self, parent):
        """テーブルエリア設定"""
        table_group = QGroupBox("選択可能な薬剤（価格順）")
        group_layout = QVBoxLayout(table_group)

        self.medicine_table = QTableWidget()
        self.medicine_table.setColumnCount(4)
        self.medicine_table.setHorizontalHeaderLabels(
            ["薬剤名", "分類", "価格", "メーカー"]
        )

        # テーブル設定
        header = self.medicine_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.medicine_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.medicine_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.medicine_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        group_layout.addWidget(self.medicine_table)
        parent.addWidget(table_group)

        # シグナル接続
        self.medicine_table.itemSelectionChanged.connect(self.on_selection_changed)

    def setup_selection_info_area(self, parent):
        """選択情報エリア設定"""
        self.selection_info = QLabel("薬剤を選択してください")
        self.selection_info.setStyleSheet(
            "font-size: 12px; padding: 10px; background-color: #e8f4fd;"
        )
        parent.addWidget(self.selection_info)

    def setup_button_area(self, parent):
        """ボタンエリア設定"""
        button_layout = QHBoxLayout()

        self.select_button = QPushButton("選択")
        self.select_button.setEnabled(False)

        self.cancel_button = QPushButton("キャンセル")

        button_layout.addStretch()
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.cancel_button)
        parent.addLayout(button_layout)

        # シグナル接続
        self.select_button.clicked.connect(self.on_accept_selection)
        self.cancel_button.clicked.connect(self.reject)

    def on_selection_changed(self):
        """選択変更イベント"""
        row = self.medicine_table.currentRow()
        if row < 0:
            self.select_button.setEnabled(False)
            self.selection_info.setText("薬剤を選択してください")
            return

        # 選択された行の薬剤データを取得
        name_item = self.medicine_table.item(row, 0)
        selected_medicine = name_item.data(Qt.ItemDataRole.UserRole)

        if selected_medicine:
            # 選択情報を表示
            medicine_name = selected_medicine["medicine_name"]
            medicine_type = selected_medicine["medicine_type"]
            price = selected_medicine["price"]
            manufacturer = selected_medicine["manufacturer"]

            info_text = (
                f"選択中: {medicine_name}\n"
                f"分類: {medicine_type} | 価格: ¥{price:.2f} | メーカー: {manufacturer}"
            )
            self.selection_info.setText(info_text)
            self.select_button.setEnabled(True)
            self.selected_medicine = selected_medicine

    def on_accept_selection(self):
        """選択確定"""
        if not self.selected_medicine:
            QMessageBox.warning(self, "エラー", "薬剤を選択してください")
            return

        medicine_name = self.selected_medicine["medicine_name"]
        medicine_type = self.selected_medicine["medicine_type"]

        reply = QMessageBox.question(
            self,
            "確認",
            f"以下の薬剤を選択しますか？\n\n"
            f"薬剤名: {medicine_name}\n"
            f"分類: {medicine_type}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.accept()

    def populate_data(self):
        """テーブルにデータを設定"""
        alternatives = self.medicine_data.get("alternative_medicines", [])

        if not alternatives:
            self.selection_info.setText("この薬剤には代替薬剤がありません")
            return

        # 元薬剤 + 関連薬剤をすべて表示
        all_medicines = [self.medicine_data] + alternatives

        self.medicine_table.setRowCount(len(all_medicines))

        for row, medicine in enumerate(all_medicines):
            # 薬剤名
            name_item = QTableWidgetItem(medicine["medicine_name"])
            if row == 0:  # 元薬剤
                name_item.setBackground(Qt.GlobalColor.cyan)
            self.medicine_table.setItem(row, 0, name_item)

            # 分類
            medicine_type = medicine["medicine_type"]
            type_item = QTableWidgetItem(medicine_type)
            if medicine_type == "先発品":
                type_item.setBackground(Qt.GlobalColor.yellow)
            elif medicine_type == "後発品":
                type_item.setBackground(Qt.GlobalColor.green)
            self.medicine_table.setItem(row, 1, type_item)

            # 価格
            price = medicine["price"]
            price_item = QTableWidgetItem(f"¥{price:.2f}")
            self.medicine_table.setItem(row, 2, price_item)

            # メーカー
            manufacturer_item = QTableWidgetItem(medicine["manufacturer"])
            self.medicine_table.setItem(row, 3, manufacturer_item)

            # 薬剤データを行に関連付け
            name_item.setData(Qt.ItemDataRole.UserRole, medicine)
