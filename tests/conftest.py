"""
共通テストフィクスチャ

pytest が自動的にこのファイルを読み込み、
すべてのテストファイルでフィクスチャが利用可能になります。
"""

from pathlib import Path

import pytest
from pytest import Config

from rx_scanner.database.db_manager import DatabaseManager

# =============================================================================
# pytest 設定
# =============================================================================


def pytest_configure(config: Config) -> None:
    """pytest のカスタム設定"""
    config.addinivalue_line("markers", "slow: 実行に時間がかかるテスト（スキップ可能）")
    config.addinivalue_line(
        "markers", "integration: 統合テスト（複数コンポーネント連携）"
    )
    config.addinivalue_line("markers", "ui: UIテスト（PySide6/Qt 必須）")
    config.addinivalue_line(
        "markers", "requires_tesseract: Tesseract OCR のインストールが必須"
    )


# =============================================================================
# DBテスト用フィクスチャ
# =============================================================================


@pytest.fixture
def tmp_db(tmp_path: Path) -> DatabaseManager:
    """
    一時的なテスト用DB

    Args:
        tmp_path: pytest提供の一時ディレクトリ

    Returns:
        DatabaseManager: テスト用DBManager
    """
    db_path = tmp_path / "test.db"
    return DatabaseManager(str(db_path))


@pytest.fixture
def sample_medicines() -> list[dict]:
    """
    サンプル薬剤データ（CSV実在データ）

    テストケース:
    - カロナール錠200（後発品）- アセトアミノフェン
    - アムロジン錠10mg（先発品）- アムロジピン
    - アムロジピン錠10mg「トーワ」（後発品・特殊文字テスト）- アムロジピン

    Returns:
        薬剤データのリスト
    """
    return [
        {
            "classification": "内用薬",
            "ingredient_name": "アセトアミノフェン",
            "specification": "２００ｍｇ１錠",
            "medicine_name": "カロナール錠２００",
            "manufacturer": "あゆみ製薬",
            "price": 6.70,
            "medicine_type": "後発品",
        },
        {
            "classification": "内用薬",
            "ingredient_name": "アムロジピンベシル酸塩",
            "specification": "１０ｍｇ１錠",
            "medicine_name": "アムロジン錠１０ｍｇ",
            "manufacturer": "住友ファーマ",
            "price": 16.30,
            "medicine_type": "先発品",
        },
        {
            "classification": "内用薬",
            "ingredient_name": "アムロジピンベシル酸塩",
            "specification": "１０ｍｇ１錠",
            "medicine_name": "アムロジピン錠１０ｍｇ「トーワ」",
            "manufacturer": "東和薬品",
            "price": 12.80,
            "medicine_type": "後発品",
        },
    ]


@pytest.fixture
def db_with_sample_data(
    tmp_db: DatabaseManager, sample_medicines: list[dict]
) -> DatabaseManager:
    """
    サンプルデータ投入済みDB

    Args:
        tmp_db: 空のテスト用DB
        sample_medicines: サンプル薬剤データ

    Returns:
        DatabaseManager: データ投入済みDBManager
    """
    tmp_db.replace_all_medicines(sample_medicines)
    return tmp_db
