"""
データベース初期化スクリプト
薬剤マスタデータの初期化を行う
"""

import logging
import sys

from rx_scanner.database.db_manager import DatabaseManager


class DatabaseSetup:
    """データベース初期化クラス"""

    def __init__(self, db_manager: DatabaseManager | None = None):
        """
        初期化

        Args:
        db_manager: DatabaseManagerインスタンス（Noneの場合は新規作成）
        """
        self.db_manager = db_manager or DatabaseManager()
        self.logger = logging.getLogger(__name__)

    def create_sample_data(self) -> list[dict]:
        """
        サンプル薬剤データ作成
        - 実際の薬剤マスタが取得できない場合のフォールバック

        Returns:
        サンプル薬剤データリスト
        """
        sample_medicines = [
            {
                "product_name": "アスピリン錠100mg",
                "ingredient_name": "アスピリン",
                "specification": "100mg1錠",
                "classification": "内用薬",
                "price": 5.90,
                "manufacturer": "バイエル薬品株式会社",
            },
            {
                "product_name": "アスピリン錠81mg",
                "ingredient_name": "アスピリン",
                "specification": "81mg1錠",
                "classification": "内用薬",
                "price": 5.40,
                "manufacturer": "バイエル薬品株式会社",
            },
            {
                "product_name": "アスピリン腸溶錠100mg",
                "ingredient_name": "アスピリン",
                "specification": "100mg1錠",
                "classification": "内用薬",
                "price": 6.10,
                "manufacturer": "武田薬品工業株式会社",
            },
            {
                "product_name": "ロキソニン錠60mg",
                "ingredient_name": "ロキソプロフェンナトリウム水和物",
                "specification": "60mg1錠",
                "classification": "内用薬",
                "price": 22.10,
                "manufacturer": "第一三共株式会社",
            },
            {
                "product_name": "ロキソプロフェン錠60mg",
                "ingredient_name": "ロキソプロフェンナトリウム水和物",
                "specification": "60mg1錠",
                "classification": "内用薬",
                "price": 9.60,
                "manufacturer": "東和薬品株式会社",
            },
            {
                "product_name": "カロナール錠20mg",
                "ingredient_name": "アセトアミノフェン",
                "specification": "200mg1錠",
                "classification": "内用薬",
                "price": 5.70,
                "manufacturer": "あゆみ製薬株式会社",
            },
            {
                "product_name": "カロナール錠300mg",
                "ingredient_name": "アセトアミノフェン",
                "specification": "300mg1錠",
                "classification": "内用薬",
                "price": 6.20,
                "manufacturer": "あゆみ製薬株式会社",
            },
            {
                "product_name": "タイレノールA",
                "ingredient_name": "アセトアミノフェン",
                "specification": "300mg1錠",
                "classification": "内用薬",
                "price": 15.80,
                "manufacturer": "東亜薬品株式会社",
            },
            {
                "product_name": "ガスター10",
                "ingredient_name": "ファモチジン",
                "specification": "10mg1錠",
                "classification": "内用薬",
                "price": 24.50,
                "manufacturer": "第一三共ヘルスケア株式会社",
            },
            {
                "product_name": "ムコダイン錠250mg",
                "ingredient_name": "L-カルボシステイン",
                "specification": "250mg1錠",
                "classification": "内用薬",
                "price": 9.10,
                "manufacturer": "キョーリン製薬株式会社",
            },
            # さらに追加のサンプルデータ...
            {
                "product_name": "アムロジン錠2.5mg",
                "ingredient_name": "アムロジピンベシル酸塩",
                "specification": "2.5mg1錠",
                "classification": "内用薬",
                "price": 23.80,
                "manufacturer": "大日本住友製薬株式会社",
            },
            {
                "product_name": "アムロジピン錠2.5mg",
                "ingredient_name": "アムロジピンベシル酸塩",
                "specification": "2.5mg1錠",
                "classification": "内用薬",
                "price": 12.40,
                "manufacturer": "沢井製薬株式会社",
            },
            # 注射薬のサンプル
            {
                "product_name": "ソルデム３Ａ輸液500mL",
                "ingredient_name": "維持輸液用電解質液",
                "specification": "500mL1袋",
                "classification": "注射薬",
                "price": 125.00,
                "manufacturer": "テルモ株式会社",
            },
            # 外用薬のサンプル
            {
                "product_name": "ロキソニンゲル1％",
                "ingredient_name": "ロキソプロフェンナトリウム水和物",
                "specification": "1％25g",
                "classification": "外用薬",
                "price": 24.70,
                "manufacturer": "第一三共株式会社",
            },
        ]

        return sample_medicines

    def setup_database(self) -> bool:
        """データベースセットアップ実行"""
        try:
            medicines = self.create_sample_data()
            count = self.db_manager.bulk_replace_medicines(medicines)

            self.logger.info(f"Sample data setup completed: {count} medicines")
            return True

        except Exception as e:
            self.logger.error(f"Setup failed: {e}")
            return False


def main():
    """メイン関数"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    setup = DatabaseSetup()
    success = setup.setup_database()

    if success:
        print("Database setup completed!")
    else:
        print("Setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
