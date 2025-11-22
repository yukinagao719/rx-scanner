"""
import_csv.py のテスト

テスト対象:
- CSVImporter: CSV薬剤データインポートクラス
"""

from pathlib import Path

import pytest

from rx_scanner.database.db_manager import DatabaseManager
from rx_scanner.database.import_csv import CSVImporter

# =============================================================================
# 基本動作の確認
# =============================================================================


def test_csvimporter_init() -> None:
    """CSVImporterの初期化"""
    importer = CSVImporter()

    assert importer.db_manager is not None


def test_csvimporter_with_custom_db(tmp_db: DatabaseManager) -> None:
    """カスタムDBでの初期化"""
    importer = CSVImporter(tmp_db)

    assert importer.db_manager == tmp_db


# =============================================================================
# import_to_database
# =============================================================================


def test_import_to_database(tmp_path: Path, tmp_db: DatabaseManager) -> None:
    """DBへのインポート"""
    csv_content = (
        "classification,ingredient_name,specification,"
        "medicine_name,manufacturer,price,medicine_type\n"
        "内用薬,アセトアミノフェン,２００ｍｇ１錠,カロナール錠２００,あゆみ製薬,6.70,後発品\n"
    )
    csv_file = tmp_path / "medicines.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    importer = CSVImporter(tmp_db)
    count = importer.import_to_database(csv_file)

    assert count == 1


def test_import_to_database_empty_csv(tmp_path: Path, tmp_db: DatabaseManager) -> None:
    """空のCSVファイル"""
    csv_content = (
        "classification,ingredient_name,specification,"
        "medicine_name,manufacturer,price,medicine_type\n"
    )
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    importer = CSVImporter(tmp_db)
    count = importer.import_to_database(csv_file)

    assert count == 0


def test_import_large_csv(tmp_path: Path, tmp_db: DatabaseManager) -> None:
    """大量データのインポート（実データの約40%: 5000件）"""
    lines = [
        "classification,ingredient_name,specification,medicine_name,manufacturer,price,medicine_type"
    ]
    for i in range(5000):
        lines.append(f"内用薬,成分{i},10mg,薬{i},製薬{i},{i}.0,後発品")

    csv_file = tmp_path / "large.csv"
    csv_file.write_text("\n".join(lines), encoding="utf-8")

    importer = CSVImporter(tmp_db)
    count = importer.import_to_database(csv_file)

    assert count == 5000


# =============================================================================
# preview_csv_data
# =============================================================================


def test_preview_csv_data(tmp_path: Path) -> None:
    """CSVデータのプレビュー"""
    csv_content = (
        "classification,ingredient_name,specification,"
        "medicine_name,manufacturer,price,medicine_type\n"
        "内用薬,アセトアミノフェン,２００ｍｇ１錠,カロナール錠２００,あゆみ製薬,6.70,後発品\n"
        "内用薬,アムロジピンベシル酸塩,１０ｍｇ１錠,"
        "アムロジン錠１０ｍｇ,住友ファーマ,16.30,先発品\n"
        "内用薬,アムロジピンベシル酸塩,１０ｍｇ１錠,"
        "アムロジピン錠１０ｍｇ「トーワ」,東和薬品,12.80,後発品\n"
    )
    csv_file = tmp_path / "medicines.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    importer = CSVImporter()
    preview = importer.preview_csv_data(csv_file, limit=2)

    assert len(preview) == 2
    assert preview[0]["medicine_name"] == "カロナール錠２００"
    assert preview[1]["medicine_name"] == "アムロジン錠１０ｍｇ"


# =============================================================================
# _read_csv_data
# =============================================================================


def test_read_csv_data_valid(tmp_path: Path) -> None:
    """正常なCSVの読み込み"""
    csv_content = (
        "classification,ingredient_name,specification,"
        "medicine_name,manufacturer,price,medicine_type\n"
        "内用薬,アセトアミノフェン,２００ｍｇ１錠,カロナール錠２００,あゆみ製薬,6.70,後発品\n"
        "内用薬,アムロジピンベシル酸塩,１０ｍｇ１錠,"
        "アムロジン錠１０ｍｇ,住友ファーマ,16.30,先発品\n"
    )
    csv_file = tmp_path / "medicines.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    importer = CSVImporter()
    medicines = importer._read_csv_data(csv_file)

    assert len(medicines) == 2
    assert medicines[0]["medicine_name"] == "カロナール錠２００"
    assert medicines[1]["medicine_name"] == "アムロジン錠１０ｍｇ"


def test_read_csv_data_with_empty_rows(tmp_path: Path) -> None:
    """空行を含むCSV"""
    csv_content = (
        "classification,ingredient_name,specification,"
        "medicine_name,manufacturer,price,medicine_type\n"
        "内用薬,アセトアミノフェン,２００ｍｇ１錠,カロナール錠２００,あゆみ製薬,6.70,後発品\n"
        ",,,,,,\n"
        "内用薬,アムロジピンベシル酸塩,１０ｍｇ１錠,"
        "アムロジン錠１０ｍｇ,住友ファーマ,16.30,先発品\n"
    )
    csv_file = tmp_path / "medicines.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    importer = CSVImporter()
    medicines = importer._read_csv_data(csv_file)

    assert len(medicines) == 2


def test_read_csv_data_with_missing_columns(tmp_path: Path) -> None:
    """必須列不足のCSV"""
    csv_content = "medicine_name,price\nアスピリン錠,5.90\n"
    csv_file = tmp_path / "invalid.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    importer = CSVImporter()

    with pytest.raises(ValueError, match="必要な列が不足しています"):
        importer._read_csv_data(csv_file)


def test_read_csv_data_file_not_found() -> None:
    """ファイルが存在しない"""
    importer = CSVImporter()

    with pytest.raises(FileNotFoundError):
        importer._read_csv_data("/nonexistent/file.csv")


def test_read_csv_with_optional_fields_empty(tmp_path: Path) -> None:
    """項目が空のCSV（デフォルト値テスト）"""
    csv_content = (
        "classification,ingredient_name,specification,"
        "medicine_name,manufacturer,price,medicine_type\n"
        ",,,薬A錠,,5.90,\n"
    )
    csv_file = tmp_path / "partial.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    importer = CSVImporter()
    medicines = importer._read_csv_data(csv_file)

    assert len(medicines) == 1
    assert medicines[0]["classification"] == "未分類"
    assert medicines[0]["ingredient_name"] == ""
    assert medicines[0]["specification"] == ""
    assert medicines[0]["manufacturer"] == "不明"
    assert medicines[0]["medicine_type"] == "その他"


def test_read_csv_with_quotes(tmp_path: Path) -> None:
    """引用符を含むCSV"""
    csv_content = (
        "classification,ingredient_name,specification,"
        "medicine_name,manufacturer,price,medicine_type\n"
        '内用薬,"アスピリン, 配合",100mg1錠,'
        '"アスピリン錠100mg「テスト」",テスト製薬,5.90,後発品\n'
    )
    csv_file = tmp_path / "quoted.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    importer = CSVImporter()
    medicines = importer._read_csv_data(csv_file)

    assert len(medicines) == 1
    assert "," in medicines[0]["ingredient_name"]


# =============================================================================
# _parse_price
# =============================================================================


def test_parse_price_normal() -> None:
    """通常の価格"""
    importer = CSVImporter()

    assert importer._parse_price("10.5") == 10.5
    assert importer._parse_price(10.5) == 10.5
    assert importer._parse_price(10) == 10.0


def test_parse_price_with_comma() -> None:
    """カンマ区切りの価格"""
    importer = CSVImporter()

    assert importer._parse_price("1,234.56") == 1234.56
    assert importer._parse_price("10,000") == 10000.0


def test_parse_price_with_spaces() -> None:
    """スペース含む価格"""
    importer = CSVImporter()

    assert importer._parse_price(" 10.5 ") == 10.5
    assert importer._parse_price("1 234") == 1234.0


def test_parse_price_empty() -> None:
    """空の価格"""
    importer = CSVImporter()

    assert importer._parse_price("") == 0.0
    assert importer._parse_price(None) == 0.0


def test_parse_price_invalid() -> None:
    """不正な価格"""
    importer = CSVImporter()

    assert importer._parse_price("invalid") == 0.0
    assert importer._parse_price("abc") == 0.0
