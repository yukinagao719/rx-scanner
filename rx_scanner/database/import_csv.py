"""
CSV薬剤データをデータベースにインポートするスクリプト
product_list.csvを読み込み、薬剤マスタデータベースに登録する
"""

import logging
import sys
from pathlib import Path

import pandas as pd

from rx_scanner.database.db_manager import DatabaseManager


class CSVImporter:
    """CSV薬剤データインポートクラス"""

    def __init__(self, db_manager: DatabaseManager | None = None):
        """
        初期化

        Args:
            db_manager: DatabaseManagerインスタンス（Noneの場合は新規作成）
        """
        self.db_manager = db_manager or DatabaseManager()
        self.logger = logging.getLogger(__name__)

    def _parse_price(self, price_str) -> float:
        """
        価格文字列をfloatに変換
        カンマ区切りや空白を除去して変換

        Args:
            price_str: 価格文字列

        Returns:
            float値の価格
        """
        if pd.isna(price_str) or price_str == "":
            return 0.0

        try:
            # 文字列に変換してカンマと空白を除去
            clean_price = str(price_str).strip().replace(",", "").replace(" ", "")
            return float(clean_price)
        except (ValueError, TypeError):
            self.logger.warning(f"価格変換エラー: {price_str} -> 0.0")
            return 0.0

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
            self.logger.info(f"CSVファイルを読み込み: {len(df)}行")

            # 必要な列が存在するかチェック
            required_columns = [
                "classification",
                "ingredient_name",
                "specification",
                "product_name",
                "manufacturer",
                "price",
            ]

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"必要な列が不足しています: {missing_columns}")

            # データを辞書のリストに変換
            medicines = []
            for _, row in df.iterrows():
                # 空行をスキップ
                if pd.isna(row["product_name"]) or not str(row["product_name"]).strip():
                    self.logger.warning(f"商品名が空のためスキップ: {row}")
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
                    "product_name": str(row["product_name"]).strip(),
                    "manufacturer": str(row["manufacturer"]).strip()
                    if pd.notna(row["manufacturer"])
                    else "不明",
                    "price": self._parse_price(row["price"])
                    if pd.notna(row["price"]) and row["price"] != ""
                    else 0.0,
                }

                medicines.append(medicine)

            self.logger.info(f"有効な薬剤データ: {len(medicines)}件")
            return medicines

        except Exception as e:
            self.logger.error(f"CSVファイル読み込みエラー: {e}")
            raise

    def import_to_database(self, csv_path: str | Path) -> int:
        """
        CSVデータをデータベースにインポート（全置換）

        Args:
            csv_path: CSVファイルのパス

        Returns:
            インポートした件数

        Raises:
            Exception: インポート処理中にエラーが発生した場合
        """
        try:
            # CSVデータを読み込み
            medicines = self.read_csv_data(csv_path)

            if not medicines:
                self.logger.warning("インポートするデータがありません")
                return 0

            # データベースに一括置換でインポート
            self.logger.info("薬剤マスタを全置換でインポートを開始")
            count = self.db_manager.bulk_replace_medicines(medicines)

            self.logger.info(f"インポート完了: {count}件")
            return count

        except Exception as e:
            self.logger.error(f"インポート処理エラー: {e}")
            raise

    def validate_import(self) -> dict:
        """
        インポート後のデータ検証

        Returns:
            検証結果の統計情報
        """
        try:
            stats = self.db_manager.get_statistics()

            # 簡単な検索テストも実行
            test_results = self.db_manager.search_medicines("アスピリン", limit=5)
            stats["search_test_count"] = len(test_results)

            self.logger.info(
                f"検証完了: 総薬剤数={stats['total_medicines']}, "
                f"検索テスト結果={stats['search_test_count']}件"
            )
            return stats

        except Exception as e:
            self.logger.error(f"検証エラー: {e}")
            return {}

    def preview_csv_data(self, csv_path: str | Path, limit: int = 10) -> list[dict]:
        """
        CSVデータのプレビュー表示

        Args:
            csv_path: CSVファイルのパス
            limit: 表示する件数

        Returns:
            プレビューデータのリスト
        """
        try:
            medicines = self.read_csv_data(csv_path)
            preview_data = medicines[:limit]

            self.logger.info(
                f"プレビュー表示: {len(preview_data)}件 (全{len(medicines)}件中)"
            )
            return preview_data

        except Exception as e:
            self.logger.error(f"プレビューエラー: {e}")
            return []


def main():
    """メイン関数"""
    import argparse

    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(
        description="CSV薬剤データをデータベースにインポート"
    )
    parser.add_argument(
        "csv_file",
        help="インポートするCSVファイルのパス",
        default="product_list.csv",
        nargs="?",
    )
    parser.add_argument(
        "--preview", action="store_true", help="データのプレビューのみ実行"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細ログを表示")

    args = parser.parse_args()

    # ログ設定
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger(__name__)

    try:
        importer = CSVImporter()

        if args.preview:
            # プレビューモード
            logger.info("プレビューモードで実行")
            preview_data = importer.preview_csv_data(args.csv_file, limit=10)

            print("\n=== データプレビュー ===")
            for i, medicine in enumerate(preview_data, 1):
                print(f"{i:2d}. {medicine['product_name']}")
                print(f"     成分: {medicine['ingredient_name']}")
                print(f"     規格: {medicine['specification']}")
                print(f"     区分: {medicine['classification']}")
                print(f"     価格: ¥{medicine['price']}")
                print(f"     メーカー: {medicine['manufacturer']}")
                print()

        else:
            # インポートモード（全置換のみ）
            logger.info(f"インポートを開始: {args.csv_file}")
            count = importer.import_to_database(args.csv_file)

            # インポート後の検証
            stats = importer.validate_import()

            print("\n=== インポート結果 ===")
            print(f"インポート件数: {count}件")
            print(f"総薬剤数: {stats.get('total_medicines', 'N/A')}件")
            print(f"メーカー数: {stats.get('total_manufacturers', 'N/A')}社")
            print(f"成分数: {stats.get('total_ingredients', 'N/A')}種類")
            print(f"検索テスト: {stats.get('search_test_count', 'N/A')}件ヒット")

        print("処理が完了しました。")

    except Exception as e:
        logger.error(f"処理中にエラーが発生: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
