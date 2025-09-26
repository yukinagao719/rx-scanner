"""
薬剤データベース管理クラス
薬剤マスタ検索・操作を担当
"""

import datetime
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class DatabaseManager:
    """薬剤データベース管理クラス"""

    def __init__(self, db_path: str | None = None):
        """
        初期化
        Args:
            db_path: データベースファイルパス（指定なしの場合はデフォルト）
        """
        if db_path is None:
            # デフォルトパス： database/medicine_data.db
            self.db_path = Path(__file__).parent / "medicine_data.db"
        else:
            self.db_path = Path(db_path)

        # ログ設定
        self.logger = logging.getLogger(__name__)

        # データベース初期化
        self.init_database()

    @contextmanager
    def get_connection(self):
        """データベース接続のコンテキストマネージャー"""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            yield conn

        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def init_database(self):
        """データベーステーブルの初期化"""
        with self.get_connection() as conn:
            # 薬剤マスタテーブル作成
            conn.execute("""
            CREATE TABLE IF NOT EXISTS medicines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                ingredient_name TEXT NOT NULL,
                specification TEXT,
                classification TEXT NOT NULL,
                price REAL NOT NULL,
                manufacturer TEXT DEFAULT "不明",
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # インデックス作成
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_product_name ON medicines(product_name)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ingredient_name
                ON medicines(ingredient_name)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_classification
                ON medicines(classification)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_specification
                ON medicines(specification)
            """)

            # FTS用の仮想テーブル
            conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS medicines_fts USING fts5(
                product_name,
                ingredient_name,
                specification,
                manufacturer,
                content="medicines",
                content_rowid="id"
            )
            """)

            # FTS用トリガー
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS medicines_ai AFTER INSERT ON medicines
            BEGIN
                INSERT INTO medicines_fts(
                    rowid, product_name, ingredient_name, specification, manufacturer
                )
                VALUES(
                    new.id, new.product_name, new.ingredient_name,
                    new.specification, new.manufacturer
                );
            END
            """)

            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS medicines_ad AFTER DELETE ON medicines
            BEGIN
                INSERT INTO medicines_fts
                (
                    medicines_fts, rowid, product_name, ingredient_name,
                    specification, manufacturer
                )
                VALUES
                (
                    'delete', old.id, old.product_name,
                    old.ingredient_name, old.specification, old.manufacturer
                );
            END
            """)

            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS medicines_au AFTER UPDATE ON medicines
            BEGIN
                INSERT INTO medicines_fts
                (
                    medicines_fts, rowid, product_name, ingredient_name,
                    specification, manufacturer
                )
                VALUES
                (
                    'delete', old.id, old.product_name,
                    old.ingredient_name, old.specification, old.manufacturer
                );
                INSERT INTO medicines_fts(
                    rowid, product_name, ingredient_name, specification, manufacturer
                )
                VALUES (
                    new.id, new.product_name, new.ingredient_name,
                    new.specification, new.manufacturer
                );
            END
            """)

            conn.commit()
            self.logger.info("Database initialized successfully")

    def search_medicines(
        self, query: str, limit: int = 100, use_fts: bool = True
    ) -> list[dict]:
        """
        薬品検索

        Args:
            query: 検索クエリ
            limit: 結果件数上限
            use_fts: 全文検索を使用するかどうか
        Returns:
            検索結果のリスト
        """
        if not query or len(query.strip()) < 2:
            return []

        query = query.strip()
        results = []

        with self.get_connection() as conn:
            if use_fts:
                # FTSを使用
                sql = """
                    SELECT m.* from medicines m
                    JOIN medicines_fts fts ON m.id = fts.rowid
                    WHERE medicines_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """
                cursor = conn.execute(sql, (f'"{query}"*', limit))
            else:
                # LIKE検索を使用
                sql = """
                    SELECT * FROM medicines
                    WHERE product_name LIKE ?
                    OR ingredient_name LIKE ?
                    OR manufacturer LIKE ?
                    ORDER BY
                    CASE
                    WHEN product_name LIKE ? THEN 1
                    WHEN ingredient_name LIKE ? THEN 2
                    ELSE 3
                    END,
                    product_name
                    LIMIT ?
                """
                like_query = f"%{query}%"
                exact_query = f"{query}%"
                cursor = conn.execute(
                    sql,
                    (
                        like_query,
                        like_query,
                        like_query,
                        exact_query,
                        exact_query,
                        limit,
                    ),
                )
            results = [dict(row) for row in cursor.fetchall()]
            self.logger.info(f"Search '{query}' returned {len(results)} results")
        return results

    def insert_medicine(self, medicine_data: dict) -> int:
        """
        薬剤情報を挿入

        Args:
            medicine_data: 薬剤データ

        Returns:
            挿入されたレコードのID
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO medicines (
                    product_name, ingredient_name, specification,
                    classification, price, manufacturer
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    medicine_data.get("product_name"),
                    medicine_data.get("ingredient_name"),
                    medicine_data.get("specification"),
                    medicine_data.get("classification"),
                    medicine_data.get("price"),
                    medicine_data.get("manufacturer", "不明"),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def bulk_replace_medicines(
        self, medicines: list[dict], create_backup: bool = True
    ) -> int:
        """
        薬剤マスタ全体の置き換え
        - 薬価改定時
        - マスタデータの月次更新
        - システム移行時のデータ移行

        Args:
            medicines: 新しい薬剤データのリスト
            create_backup: バックアップを作成の有無

        Returns:
            挿入された件数

        Raises:
            ValueError: データが空の場合
            Exception: 処理中にエラーが発生した場合
        """
        if not medicines:
            raise ValueError("置き換えるデータがありません。")

        # バックアップ作成
        backup_count = 0
        if create_backup:
            backup_count = self._create_backup()

        try:
            with self.get_connection() as conn:
                self.logger.info(f"薬剤マスタ全置換を開始：{len(medicines)}件")

                # 1.既存データを全削除
                conn.execute("DELETE FROM medicines")
                self.logger.debug("既存薬剤データを削除完了")

                # 2.FTSテーブルも全削除
                conn.execute("DELETE FROM medicines_fts")
                self.logger.debug("FTSテーブルを削除完了")

                # 3.新しいデータを一括挿入
                insert_data = []
                for medicine in medicines:
                    insert_data.append(
                        (
                            medicine.get("product_name"),
                            medicine.get("ingredient_name"),
                            medicine.get("specification"),
                            medicine.get("classification"),
                            medicine.get("price"),
                            medicine.get("manufacturer", "不明"),
                        )
                    )

                cursor = conn.executemany(
                    """
                    INSERT INTO medicines (
                        product_name, ingredient_name, specification, classification,
                        price, manufacturer
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    insert_data,
                )

                inserted_count = cursor.rowcount
                self.logger.info(f"新しい薬剤データを挿入完了：{inserted_count}件")

                # 4.FTSインデックス再構築
                conn.execute(
                    "INSERT INTO medicines_fts(medicines_fts) VALUES('rebuild')"
                )
                self.logger.debug("FTSインデックス再構築完了")

                # 5.コミット
                conn.commit()

        except Exception as e:
            self.logger.error(f"薬剤マスタ置換中のエラー発生：{e}")
            if create_backup and backup_count > 0:
                self.logger.error(
                    f"バックアップ({backup_count}件)からの復元を検討してください"
                )
            raise

        # 成功時のログ
        self.logger.info(f"薬品マスタ全置換完了: {inserted_count}件")
        if create_backup:
            self.logger.info(f"バックアップも作成済み: {backup_count}件")

        return inserted_count

    def bulk_insert_medicines(self, medicines: list[dict]) -> int:
        """
        薬剤情報を追加挿入（既存データは削除しない）
        - 通常の薬剤追加やインポート時に使用

        Args:
            medicines: 薬剤データのリスト

        Returns:
            挿入された件数
        """
        if not medicines:
            return 0

        inserted_count = 0

        try:
            with self.get_connection() as conn:
                for medicine in medicines:
                    conn.execute(
                        """
                        INSERT INTO medicines (
                            product_name, ingredient_name, specification,
                            classification, price, manufacturer
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            medicine.get("product_name"),
                            medicine.get("ingredient_name"),
                            medicine.get("specification"),
                            medicine.get("classification"),
                            medicine.get("price"),
                            medicine.get("manufacturer", "不明"),
                        ),
                    )

                    inserted_count += 1

                conn.commit()
        except Exception as e:
            self.logger.error(f"一括挿入中にエラー発生: {e}")
            raise

        # 成功時のログ
        self.logger.info(f"薬剤を追加挿入: {inserted_count}件")
        return inserted_count

    def _create_backup(self) -> int:
        """
        現在の薬剤データのバックアップ作成

        Returns:
            バックアップしたレコード数
        """
        try:
            with self.get_connection() as conn:
                # 現在のデータを取得
                cursor = conn.execute("SELECT * FROM medicines")
                backup_data = cursor.fetchall()

                if not backup_data:
                    self.logger.info("バックアップ対象のデータがありません")
                    return 0

                # バックアップファイル名を生成
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.db_path.parent / f"medicines_backup_{timestamp}.db"

                # バックアップDB作成
                backup_conn = sqlite3.connect(str(backup_path))
                backup_conn.execute(
                    """
                    CREATE TABLE medicines AS
                    SELECT * FROM medicines
                """,
                )

                # 元DBからバックアップDBにデータコピー
                conn.backup(backup_conn)
                backup_conn.close()

                backup_count = len(backup_data)
                self.logger.info(
                    f"バックアップ作成完了: {backup_path} ({backup_count}件)"
                )
                return backup_count

        except Exception as e:
            self.logger.warning(f"バックアップ作成に失敗: {e}")
            return 0

    def get_statistics(self) -> dict:
        """
        データベース統計情報を取得

        Returns:
            統計情報辞書
        """
        with self.get_connection() as conn:
            stats = {}

            # 総薬品数
            cursor = conn.execute("SELECT COUNT(*) FROM medicines")
            stats["total_medicines"] = cursor.fetchone()[0]

            # メーカー数
            cursor = conn.execute("SELECT COUNT(DISTINCT manufacturer) FROM medicines")
            stats["total_manufacturers"] = cursor.fetchone()[0]

            # 成分数
            cursor = conn.execute(
                "SELECT COUNT(DISTINCT ingredient_name) FROM medicines"
            )
            stats["total_ingredients"] = cursor.fetchone()[0]

            # 区分数
            cursor = conn.execute(
                "SELECT COUNT(DISTINCT classification) FROM medicines"
            )
            stats["total_classifications"] = cursor.fetchone()[0]

            # データベースサイズ
            stats["db_size"] = (
                self.db_path.stat().st_size if self.db_path.exists() else 0
            )

        return stats
