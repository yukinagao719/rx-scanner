"""
CSV薬剤データをDBにインポートするスクリプト
medicine_list_XXXXXXXX.csvを読み込み、薬剤マスタDBに登録する
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from rx_scanner.database.db_manager import DatabaseManager


class CSVImporter:
    """CSV薬剤データインポートクラス"""

    def __init__(self, db_manager: DatabaseManager | None = None):
        """
        Args:
            db_manager: DatabaseManagerインスタンス（テスト用、通常はNone）
        """
        self.db_manager = db_manager or DatabaseManager()

        self.logger = logging.getLogger(__name__)

    def read_csv_data(self, csv_path: str | Path) -> list[dict]:
        """
        CSVファイルから薬剤データを読み込み

        Args:
            csv_path: CSVファイルのパス

        Returns:
            薬剤データのリスト

        Raises:
            FileNotFoundError: ファイルが見つからない場合
            ValueError: データ形式が不正な場合
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")

        try:
            # CSVファイルを読み込み
            df = pd.read_csv(csv_path)
            self.logger.info(f"CSV file loaded: {len(df)} rows")

            # 必要な列が存在するかチェック
            required_columns = [
                "classification",
                "ingredient_name",
                "specification",
                "medicine_name",
                "manufacturer",
                "price",
                "medicine_type",
            ]

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"必要な列が不足しています: {missing_columns}")

            # データを辞書のリストに変換
            medicines = []
            for _, row in df.iterrows():
                # 空行をスキップ
                if (
                    pd.isna(row["medicine_name"])
                    or not str(row["medicine_name"]).strip()
                ):
                    self.logger.warning(f"Skipping row with empty medicine name: {row}")
                    continue

                medicine = {
                    "classification": str(row["classification"]).strip()
                    if pd.notna(row["classification"])
                    else "未分類",
                    "ingredient_name": str(row["ingredient_name"]).strip()
                    if pd.notna(row["ingredient_name"])
                    else "",
                    "specification": str(row["specification"]).strip()
                    if pd.notna(row["specification"])
                    else "",
                    "medicine_name": str(row["medicine_name"]).strip(),
                    "manufacturer": str(row["manufacturer"]).strip()
                    if pd.notna(row["manufacturer"])
                    else "不明",
                    "price": self._parse_price(row["price"]),
                    "medicine_type": str(row["medicine_type"]).strip()
                    if pd.notna(row["medicine_type"])
                    else "その他",
                }

                medicines.append(medicine)

            self.logger.info(f"Valid medicine data: {len(medicines)} records")
            return medicines

        except Exception as e:
            self.logger.error(f"CSV file read error: {e}")
            raise

    def import_to_database(self, csv_path: str | Path) -> int:
        """
        CSVデータをDBにインポート

        Args:
            csv_path: CSVファイルのパス

        Returns:
            インポート件数
        """
        try:
            # CSVデータを読み込み
            medicines = self.read_csv_data(csv_path)

            if not medicines:
                self.logger.warning("No data to import")
                return 0

            # DBに全薬剤を置き換えてインポート
            self.logger.info("Starting full medicine replacement import")
            count = self.db_manager.replace_all_medicines(medicines)

            self.logger.info(f"Import completed: {count} records")
            return count

        except Exception as e:
            self.logger.error(f"Import process error: {e}")
            raise

    def preview_csv_data(self, csv_path: str | Path, limit: int = 10) -> list[dict]:
        """
        CSVデータのプレビュー表示

        Args:
            csv_path: CSVファイルのパス
            limit: 表示件数

        Returns:
            プレビューデータのリスト
        """
        try:
            medicines = self.read_csv_data(csv_path)
            preview_data = medicines[:limit]

            self.logger.info(
                f"Preview displayed: {len(preview_data)} records "
                f"(of {len(medicines)} total)"
            )
            return preview_data

        except Exception as e:
            self.logger.error(f"Preview error: {e}")
            return []

    def _parse_price(self, price_data: Any) -> float:
        """
        価格文字列をfloatに変換（カンマ区切りや空白を除去）
        - エクセルの書式設定に由来する不整合データ

        Args:
            price_data: 価格データ（str, float, int, Noneなど）

        Returns:
            float値の価格
        """
        if pd.isna(price_data) or str(price_data).strip() == "":
            return 0.0

        try:
            # 文字列に変換してカンマと空白を除去
            clean_price = str(price_data).strip().replace(",", "").replace(" ", "")
            return float(clean_price)

        except (ValueError, TypeError):
            self.logger.warning(f"Price conversion error: {price_data} -> 0.0")
            return 0.0


def main():
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description="CSV薬剤データをDBにインポート")
    parser.add_argument(
        "csv_file",
        help="インポートするCSVファイルパス",
        default="data/medicine_list_20251001.csv",
        nargs="?",
    )
    parser.add_argument(
        "-p", "--preview", action="store_true", help="データのプレビューのみ実行"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細ログ表示")

    args = parser.parse_args()

    # ログ設定
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        importer = CSVImporter()

        if args.preview:
            # プレビューモード
            importer.logger.info("Running in preview mode")
            preview_data = importer.preview_csv_data(args.csv_file, limit=10)

            print("\n=== データプレビュー ===")
            for i, medicine in enumerate(preview_data, 1):
                print(f"{i:2d}. {medicine['medicine_name']}")
                print(f"     成分: {medicine['ingredient_name']}")
                print(f"     規格: {medicine['specification']}")
                print(f"     区分: {medicine['classification']}")
                print(f"     価格: ¥{medicine['price']}")
                print(f"     メーカー: {medicine['manufacturer']}")
                print(f"     薬剤分類: {medicine['medicine_type']}")
                print()

        else:
            # インポートモード
            importer.logger.info(f"Starting import: {args.csv_file}")
            count = importer.import_to_database(args.csv_file)

            # インポート後の統計情報取得
            stats = importer.db_manager.get_statistics()

            print("\n=== インポート結果 ===")
            print(f"インポート件数: {count}件")
            print(f"総薬剤数: {stats.get('total_medicines', 'N/A')}件")
            print(f"成分数: {stats.get('total_ingredients', 'N/A')}種類")

            # 区分別内訳
            classification_breakdown = stats.get("classification_breakdown", {})
            if classification_breakdown:
                print("\n区分別内訳:")
                for classification, count in classification_breakdown.items():
                    print(f"  {classification}: {count:,}件")

            # 薬剤タイプ別内訳
            medicine_type_breakdown = stats.get("medicine_type_breakdown", {})
            if medicine_type_breakdown:
                print("\n薬剤タイプ別内訳:")
                for med_type, count in medicine_type_breakdown.items():
                    print(f"  {med_type}: {count:,}件")

            # DBサイズをMB表示
            db_size_bytes = stats.get("db_size", 0)
            db_size_mb = db_size_bytes / (1024 * 1024)
            print(f"\nDBサイズ: {db_size_mb:.2f} MB")

        print("\n処理が完了しました。")

    except Exception as e:
        logging.getLogger(__name__).error(f"Error occurred during processing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
