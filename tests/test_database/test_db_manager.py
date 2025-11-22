"""
db_manager.py のテスト

テスト対象:
- DatabaseManager: 薬剤DB管理クラス
"""

from pathlib import Path

import pytest

from rx_scanner.database.db_manager import DatabaseManager

# =============================================================================
# 基本動作の確認
# =============================================================================


def test_init_database(tmp_db: DatabaseManager) -> None:
    """DB初期化によりファイルが作成される"""
    assert tmp_db is not None
    assert tmp_db.db_path.exists()


def test_database_path_custom(tmp_path: Path) -> None:
    """カスタムパスでのDB作成"""
    custom_path = tmp_path / "custom" / "medicine.db"
    custom_path.parent.mkdir(parents=True)

    db = DatabaseManager(str(custom_path))

    assert db.db_path == custom_path
    assert custom_path.exists()


# =============================================================================
# search_medicines
# =============================================================================


def test_search_medicines_basic(db_with_sample_data: DatabaseManager) -> None:
    """基本的な検索"""
    results = db_with_sample_data.search_medicines("アムロ")

    assert len(results) == 2
    assert all("アムロ" in result["medicine_name"] for result in results)


def test_search_medicines_empty_query(db_with_sample_data: DatabaseManager) -> None:
    """空クエリは空リスト"""
    results = db_with_sample_data.search_medicines("")

    assert results == []


def test_search_medicines_single_char(db_with_sample_data: DatabaseManager) -> None:
    """1文字は空リスト"""
    results = db_with_sample_data.search_medicines("ア")

    assert results == []


def test_search_medicines_two_chars(db_with_sample_data: DatabaseManager) -> None:
    """2文字以上で検索"""
    results = db_with_sample_data.search_medicines("カロ")

    assert len(results) >= 1


def test_search_medicines_no_results(db_with_sample_data: DatabaseManager) -> None:
    """結果なし"""
    results = db_with_sample_data.search_medicines("存在しない薬剤名")

    assert results == []


def test_search_medicines_limit(db_with_sample_data: DatabaseManager) -> None:
    """検索結果の上限"""
    results = db_with_sample_data.search_medicines("アムロ", limit=1)

    assert len(results) == 1


def test_search_with_special_characters(db_with_sample_data: DatabaseManager) -> None:
    """特殊文字（鉤括弧）を含む検索クエリの処理"""
    # 特殊文字「」を含む検索クエリでも正しく動作する
    results = db_with_sample_data.search_medicines("「トーワ")

    assert len(results) == 1
    assert results[0]["medicine_name"] == "アムロジピン錠１０ｍｇ「トーワ」"


# =============================================================================
# get_medicine_alternatives
# =============================================================================


def test_get_medicine_alternatives(db_with_sample_data: DatabaseManager) -> None:
    """代替薬剤の取得"""
    alternatives = db_with_sample_data.get_medicine_alternatives(
        ingredient_name="アムロジピンベシル酸塩",
        exclude_medicine_name="アムロジン錠１０ｍｇ",
    )

    assert len(alternatives) == 1
    assert alternatives[0]["medicine_name"] == "アムロジピン錠１０ｍｇ「トーワ」"


def test_get_medicine_alternatives_no_alternatives(
    db_with_sample_data: DatabaseManager,
) -> None:
    """代替薬剤なし（成分が1種類のみの薬剤を除外）"""
    # アセトアミノフェンはカロナールのみなので、除外すると代替なし
    alternatives = db_with_sample_data.get_medicine_alternatives(
        ingredient_name="アセトアミノフェン",
        exclude_medicine_name="カロナール錠２００",
    )

    assert len(alternatives) == 0


def test_get_medicine_alternatives_nonexistent_ingredient(
    db_with_sample_data: DatabaseManager,
) -> None:
    """存在しない成分名"""
    alternatives = db_with_sample_data.get_medicine_alternatives(
        ingredient_name="存在しない成分", exclude_medicine_name="存在しない薬剤"
    )

    assert alternatives == []


def test_get_medicine_alternatives_sorted_by_type_and_price(
    tmp_db: DatabaseManager,
) -> None:
    """薬剤タイプと価格でソート"""
    medicines = [
        # 先発品グループ（価格: 200, 150, 100）
        {
            "classification": "内用薬",
            "ingredient_name": "テスト成分",
            "specification": "10mg",
            "medicine_name": "先発品A",
            "manufacturer": "A社",
            "price": 200.0,
            "medicine_type": "先発品",
        },
        {
            "classification": "内用薬",
            "ingredient_name": "テスト成分",
            "specification": "10mg",
            "medicine_name": "先発品B",
            "manufacturer": "B社",
            "price": 100.0,
            "medicine_type": "先発品",
        },
        {
            "classification": "内用薬",
            "ingredient_name": "テスト成分",
            "specification": "10mg",
            "medicine_name": "先発品C",
            "manufacturer": "C社",
            "price": 150.0,
            "medicine_type": "先発品",
        },
        # 後発品グループ（価格: 80, 50, 60）
        {
            "classification": "内用薬",
            "ingredient_name": "テスト成分",
            "specification": "10mg",
            "medicine_name": "後発品A",
            "manufacturer": "D社",
            "price": 80.0,
            "medicine_type": "後発品",
        },
        {
            "classification": "内用薬",
            "ingredient_name": "テスト成分",
            "specification": "10mg",
            "medicine_name": "後発品B",
            "manufacturer": "E社",
            "price": 50.0,
            "medicine_type": "後発品",
        },
        {
            "classification": "内用薬",
            "ingredient_name": "テスト成分",
            "specification": "10mg",
            "medicine_name": "後発品C",
            "manufacturer": "F社",
            "price": 60.0,
            "medicine_type": "後発品",
        },
    ]
    tmp_db.replace_all_medicines(medicines)

    alternatives = tmp_db.get_medicine_alternatives(
        ingredient_name="テスト成分", exclude_medicine_name="先発品B"
    )

    assert len(alternatives) == 5

    # 先発品グループ（price昇順: 150 → 200）
    assert alternatives[0]["medicine_type"] == "先発品"
    assert alternatives[0]["price"] == 150.0
    assert alternatives[1]["medicine_type"] == "先発品"
    assert alternatives[1]["price"] == 200.0

    # 後発品グループ（price昇順: 50 → 60 → 80）
    assert alternatives[2]["medicine_type"] == "後発品"
    assert alternatives[2]["price"] == 50.0
    assert alternatives[3]["medicine_type"] == "後発品"
    assert alternatives[3]["price"] == 60.0
    assert alternatives[4]["medicine_type"] == "後発品"
    assert alternatives[4]["price"] == 80.0


# =============================================================================
# replace_all_medicines
# =============================================================================


def test_replace_all_medicines(
    tmp_db: DatabaseManager, sample_medicines: list[dict]
) -> None:
    """薬剤データの一括置換"""
    count = tmp_db.replace_all_medicines(sample_medicines)

    assert count == 3


def test_replace_all_medicines_twice(
    tmp_db: DatabaseManager, sample_medicines: list[dict]
) -> None:
    """2回置換すると上書きされる"""
    tmp_db.replace_all_medicines(sample_medicines)

    new_medicines = [
        {
            "classification": "内用薬",
            "ingredient_name": "アセトアミノフェン",
            "specification": "３００ｍｇ１錠",
            "medicine_name": "カロナール錠３００",
            "manufacturer": "あゆみ製薬",
            "price": 7.00,
            "medicine_type": "後発品",
        }
    ]
    count = tmp_db.replace_all_medicines(new_medicines)

    assert count == 1


def test_replace_all_medicines_empty_data(tmp_db: DatabaseManager) -> None:
    """空データでの置換はエラー"""
    with pytest.raises(ValueError, match="置換データが指定されていません"):
        tmp_db.replace_all_medicines([])


# =============================================================================
# get_statistics
# =============================================================================


def test_get_statistics_empty(tmp_db: DatabaseManager) -> None:
    """空DBの統計"""
    stats = tmp_db.get_statistics()

    assert stats["total_medicines"] == 0
    assert stats["total_ingredients"] == 0
    assert stats["classification_breakdown"] == {}
    assert stats["medicine_type_breakdown"] == {}
    assert stats["db_size"] > 0


def test_get_statistics_with_data(db_with_sample_data: DatabaseManager) -> None:
    """データありDBの統計"""
    stats = db_with_sample_data.get_statistics()

    assert stats["total_medicines"] == 3
    assert stats["total_ingredients"] == 2
    assert stats["classification_breakdown"]["内用薬"] == 3
    assert stats["medicine_type_breakdown"]["先発品"] == 1
    assert stats["medicine_type_breakdown"]["後発品"] == 2


# =============================================================================
# エラーハンドリング
# =============================================================================


def test_connection_error_handling(tmp_path: Path) -> None:
    """接続エラーのハンドリング"""
    invalid_path = tmp_path / "nonexistent" / "dir" / "db.db"

    with pytest.raises(RuntimeError):
        db = DatabaseManager(str(invalid_path))
        db.search_medicines("test")
