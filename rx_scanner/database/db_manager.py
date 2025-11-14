"""
薬剤DB管理クラス
薬剤の検索・操作を担当
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class DatabaseManager:
    """薬剤DB管理クラス"""

    def __init__(self, db_path: str | None = None):
        """
        Args:
            db_path: DBファイルパス（指定なしの場合はデフォルト）
        """
        self.logger = logging.getLogger(__name__)

        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            self.db_path = project_root / "data" / "medicine_data.db"
        else:
            self.db_path = Path(db_path)

        # DB初期化
        self.init_database()

    @contextmanager
    def get_connection(self):
        """DB接続のコンテキストマネージャー"""
        conn = None

        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.row_factory = sqlite3.Row
            yield conn

        except sqlite3.Error as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            self.logger.error(f"Database error: {e}")
            raise RuntimeError(f"DBエラー: {e}") from e

        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            self.logger.error(f"Unexpected database error: {e}")
            raise

        finally:
            if conn:
                conn.close()

    def init_database(self):
        """DBテーブルの初期化"""
        with self.get_connection() as conn:
            # 薬剤マスタテーブル作成
            conn.execute("""
            CREATE TABLE IF NOT EXISTS medicines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                classification TEXT NOT NULL,
                ingredient_name TEXT NOT NULL,
                specification TEXT NOT NULL,
                medicine_name TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                price REAL NOT NULL,
                medicine_type TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """)

            # インデックス作成（ingredient_nameの完全一致検索用）
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ingredient_name
                ON medicines(ingredient_name)
            """)

            # FTS用の仮想テーブル
            conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS medicines_fts USING fts5(
                medicine_name,
                ingredient_name,
                content="medicines",
                content_rowid="id"
            )
            """)

            conn.commit()
            self.logger.info("Database initialized successfully")

    def search_medicines(self, query: str, limit: int = 50) -> list[dict]:
        """
        薬剤検索（FTS5全文検索）

        Args:
            query: 検索クエリ
            limit: 結果件数上限

        Returns:
            検索結果のリスト
        """
        query = query.strip()

        if not query or len(query) < 2:
            return []

        with self.get_connection() as conn:
            # 検索クエリのFTS5全文検索（関連度スコア順）
            sql = """
                SELECT m.* from medicines m
                JOIN medicines_fts fts ON m.id = fts.rowid
                WHERE medicines_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            cursor = conn.execute(sql, (f'"{query}"*', limit))
            results = [dict(row) for row in cursor.fetchall()]
            self.logger.info(f"Search '{query}' returned {len(results)} results")
        return results

    def get_medicine_alternatives(
        self, ingredient_name: str, exclude_medicine_name: str
    ) -> list[dict]:
        """
        代替薬剤を取得

        Args:
            ingredient_name: 成分名
            exclude_medicine_name: 除外する薬剤名（検索結果から除く）

        Returns:
            代替薬剤のリスト
        """
        try:
            with self.get_connection() as conn:
                # 同一成分の全薬剤を取得（価格順）
                sql = """
                    SELECT * FROM medicines
                    WHERE ingredient_name = ?
                    ORDER BY medicine_type, price ASC
                """
                cursor = conn.execute(sql, (ingredient_name,))
                same_ingredient_medicines = [dict(row) for row in cursor.fetchall()]

                # 除外薬剤以外を代替薬剤として抽出
                alternatives = [
                    medicine
                    for medicine in same_ingredient_medicines
                    if medicine["medicine_name"] != exclude_medicine_name
                ]

                self.logger.info(
                    f"Found {len(alternatives)} alternatives "
                    f"for ingredient '{ingredient_name}'"
                )

                return alternatives

        except Exception as e:
            self.logger.error(
                f"Error getting alternatives for ingredient '{ingredient_name}': {e}"
            )
            return []

    def replace_all_medicines(self, medicines: list[dict]) -> int:
        """
        薬剤マスタ全体の置換
        - 薬価改定時（年1回）
        - 新薬収載時（年4-7回）

        Args:
            medicines: 新しい薬剤データのリスト

        Returns:
            挿入された件数

        Raises:
            ValueError: データが空の場合
        """
        if not medicines:
            raise ValueError("置換データが指定されていません")

        with self.get_connection() as conn:
            self.logger.info(
                f"Starting full medicine replacement: {len(medicines)} records"
            )

            # 1.既存データを全削除
            sql = "DELETE FROM medicines"
            conn.execute(sql)
            self.logger.debug("Existing medicine data deleted")

            # 2.FTSテーブルを全削除
            sql = "DELETE FROM medicines_fts"
            conn.execute(sql)
            self.logger.debug("FTS table deleted")

            # 3.新しいデータを一括挿入
            insert_data = []
            for medicine in medicines:
                insert_data.append(
                    (
                        medicine.get("classification"),
                        medicine.get("ingredient_name"),
                        medicine.get("specification"),
                        medicine.get("medicine_name"),
                        medicine.get("manufacturer"),
                        medicine.get("price"),
                        medicine.get("medicine_type"),
                    )
                )

            sql = """
                INSERT INTO medicines (
                    classification, ingredient_name, specification, medicine_name,
                    manufacturer, price, medicine_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor = conn.executemany(sql, insert_data)
            inserted_count = cursor.rowcount
            self.logger.info(f"New medicine data inserted: {inserted_count} records")

            # 4.FTSインデックス再構築
            sql = "INSERT INTO medicines_fts(medicines_fts) VALUES('rebuild')"
            conn.execute(sql)
            self.logger.debug("FTS index rebuilt")

            conn.commit()

        self.logger.info(
            f"Full medicine replacement completed: {inserted_count} records"
        )

        return inserted_count

    def get_statistics(self) -> dict:
        """
        DB統計情報を取得

        Returns:
            統計情報辞書
        """
        with self.get_connection() as conn:
            stats = {}

            # 総薬剤数
            sql = "SELECT COUNT(*) FROM medicines"
            cursor = conn.execute(sql)
            stats["total_medicines"] = cursor.fetchone()[0]

            # 成分数
            sql = "SELECT COUNT(DISTINCT ingredient_name) FROM medicines"
            cursor = conn.execute(sql)
            stats["total_ingredients"] = cursor.fetchone()[0]

            # 区分別内訳
            sql = """
                SELECT classification, COUNT(*)
                FROM medicines
                GROUP BY classification
                ORDER BY COUNT(*) DESC
            """
            cursor = conn.execute(sql)
            stats["classification_breakdown"] = {
                row[0]: row[1] for row in cursor.fetchall()
            }

            # 薬剤タイプ別内訳
            sql = """
                SELECT medicine_type, COUNT(*)
                FROM medicines
                GROUP BY medicine_type
                ORDER BY COUNT(*) DESC
            """
            cursor = conn.execute(sql)
            stats["medicine_type_breakdown"] = {
                row[0]: row[1] for row in cursor.fetchall()
            }

            # DBサイズ
            stats["db_size"] = self.db_path.stat().st_size

        return stats
