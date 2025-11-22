"""
ocr_processor.py のテスト

テスト対象:
- OCRProcessor: OCR処理クラス
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from rx_scanner.utils.ocr_processor import OCRProcessor

# =============================================================================
# 基本動作の確認
# =============================================================================


def test_ocrprocessor_init() -> None:
    """OCRProcessorの初期化"""
    processor = OCRProcessor()

    assert processor is not None
    assert processor.tesseract_config["lang"] == "jpn+eng"
    assert "--oem 1 --psm 6" in processor.tesseract_config["config"]


def test_ocrprocessor_dosage_forms_list() -> None:
    """剤形リストの確認"""
    processor = OCRProcessor()

    assert "錠" in processor.DOSAGE_FORMS
    assert "OD錠" in processor.DOSAGE_FORMS
    assert "カプセル" in processor.DOSAGE_FORMS
    assert len(processor.DOSAGE_FORMS) == 29


def test_ocrprocessor_stop_words_list() -> None:
    """ストップワードリストの確認"""
    processor = OCRProcessor()

    assert "キット" in processor.STOP_WORDS
    assert "セット" in processor.STOP_WORDS
    assert "バッグ" in processor.STOP_WORDS
    assert len(processor.STOP_WORDS) == 3


# =============================================================================
# process_image
# =============================================================================


@pytest.mark.requires_tesseract
@pytest.mark.slow
def test_process_image_integration() -> None:
    """画像処理の統合テスト"""
    sample_image = Path(
        "/Users/yuki/Development/Projects/2025/rx-scanner/samples/prescription_1.jpg"
    )

    if not sample_image.exists():
        pytest.skip("Sample image not found")

    processor = OCRProcessor()
    result = processor.process_image(str(sample_image))

    assert "medicines" in result
    assert "raw_text" in result


# =============================================================================
# _preprocess_image
# =============================================================================


@pytest.mark.requires_tesseract
def test_preprocess_image_basic(tmp_path: Path) -> None:
    """基本的な画像前処理"""
    # テスト用画像を作成（白背景に黒矩形）
    image = np.ones((600, 800, 3), dtype=np.uint8) * 255
    cv2.rectangle(image, (100, 250), (700, 350), (0, 0, 0), -1)

    image_path = tmp_path / "test.png"
    cv2.imwrite(str(image_path), image)

    processor = OCRProcessor()

    # 期待値（上下30%クロップ後に2倍拡大）
    expected_height = int(600 * 0.4 * 2)
    expected_width = int(800 * 2)

    result = processor._preprocess_image(str(image_path))

    assert isinstance(result, np.ndarray)
    assert len(result.shape) == 2
    assert result.shape[0] == expected_height
    assert result.shape[1] == expected_width


@pytest.mark.requires_tesseract
def test_preprocess_image_with_scale(tmp_path: Path) -> None:
    """カスタム拡大率指定"""
    # テスト用画像を作成（白背景に黒矩形）
    image = np.ones((600, 800, 3), dtype=np.uint8) * 255
    cv2.rectangle(image, (100, 250), (700, 350), (0, 0, 0), -1)

    image_path = tmp_path / "test.png"
    cv2.imwrite(str(image_path), image)

    processor = OCRProcessor()

    # 期待値（上下30%クロップ後に3倍拡大）
    expected_height = int(600 * 0.4 * 3)
    expected_width = int(800 * 3)

    result = processor._preprocess_image(str(image_path), scale=3)

    # 検証
    assert isinstance(result, np.ndarray)
    assert len(result.shape) == 2
    assert result.shape[0] == expected_height
    assert result.shape[1] == expected_width


@pytest.mark.requires_tesseract
def test_preprocess_image_file_not_found() -> None:
    """画像ファイル不存在"""
    processor = OCRProcessor()

    with pytest.raises(FileNotFoundError):
        processor._preprocess_image("/nonexistent/image.png")


@pytest.mark.requires_tesseract
def test_preprocess_image_invalid_format(tmp_path: Path) -> None:
    """不正な画像形式"""
    invalid_file = tmp_path / "invalid.txt"
    invalid_file.write_text("not an image")

    processor = OCRProcessor()

    with pytest.raises(ValueError, match="画像形式が不正です"):
        processor._preprocess_image(str(invalid_file))


# =============================================================================
# _extract_text_regions
# =============================================================================


@pytest.mark.requires_tesseract
def test_extract_text_regions_basic() -> None:
    """基本的なテキスト抽出"""
    # 白背景の画像
    image = np.ones((600, 800), dtype=np.uint8) * 255

    processor = OCRProcessor()

    with patch("pytesseract.image_to_data") as mock_ocr:
        mock_ocr.return_value = {
            "text": ["ロキソニン", "錠", "60mg", ""],
            "conf": [90, 85, 92, -1],
            "line_num": [1, 1, 1, 2],
        }

        result = processor._extract_text_regions(image)

    assert len(result) == 3
    assert result[0] == ("ロキソニン", 1)
    assert result[1] == ("錠", 1)
    assert result[2] == ("60mg", 1)


@pytest.mark.requires_tesseract
def test_extract_text_regions_low_confidence_filtered() -> None:
    """低信頼度テキストのフィルタリング"""
    image = np.ones((600, 800), dtype=np.uint8) * 255

    processor = OCRProcessor()

    with patch("pytesseract.image_to_data") as mock_ocr:
        mock_ocr.return_value = {
            "text": ["高信頼度", "低信頼度", ""],
            "conf": [90, 20, 95],
            "line_num": [1, 2, 3],
        }

        result = processor._extract_text_regions(image)

    assert len(result) == 1
    assert result[0] == ("高信頼度", 1)


# =============================================================================
# _parse_prescription_text
# =============================================================================


@pytest.mark.requires_tesseract
def test_parse_prescription_text_basic() -> None:
    """基本的な処方箋テキスト解析"""
    processor = OCRProcessor()

    # DBManagerをモック
    mock_db = MagicMock()
    mock_db.search_medicines.return_value = [
        {
            "medicine_name": "トラゼンタ錠５ｍｇ",
            "ingredient_name": "リナグリプチン",
            "specification": "５ｍｇ１錠",
            "manufacturer": "日本ベーリンガーインゲルハイム",
            "medicine_type": "先発品",
            "price": 118.90,
        }
    ]
    mock_db.get_medicine_alternatives.return_value = []
    processor.db_manager = mock_db

    text_regions = [
        ("トラゼンタ", 1),
        ("錠", 1),
        ("５ｍｇ", 1),
    ]

    result = processor._parse_prescription_text(text_regions)

    assert "medicines" in result
    assert "raw_text" in result
    assert result["raw_text"] == "トラゼンタ錠５ｍｇ"


# =============================================================================
# _match_with_database
# =============================================================================


def test_match_with_database_no_db() -> None:
    """DB未接続時の処理"""
    processor = OCRProcessor()
    processor.db_manager = None

    result = processor._match_with_database("ロキソニン錠60mg")

    assert result == []


def test_match_with_database_basic() -> None:
    """基本的なDB検索"""
    processor = OCRProcessor()

    # DBManagerをモック
    mock_db = MagicMock()
    mock_db.search_medicines.return_value = [
        {
            "medicine_name": "アムロジン錠１０ｍｇ",
            "ingredient_name": "アムロジピンベシル酸塩",
            "specification": "１０ｍｇ１錠",
            "manufacturer": "住友ファーマ",
            "medicine_type": "先発品",
            "price": 16.30,
        }
    ]
    processor.db_manager = mock_db

    result = processor._match_with_database("アムロジン錠１０ｍｇ")

    assert len(result) > 0
    assert result[0]["medicine_name"] == "アムロジン錠１０ｍｇ"
    assert result[0]["confidence"] >= 0.70


def test_match_with_database_stop_words() -> None:
    """ストップワードのスキップ"""
    processor = OCRProcessor()

    mock_db = MagicMock()
    mock_db.search_medicines.return_value = []
    processor.db_manager = mock_db

    processor._match_with_database("キット")

    assert mock_db.search_medicines.call_count == 0


# =============================================================================
# _extract_dosage_forms_and_specs
# =============================================================================


@pytest.mark.parametrize(
    "text, expected_forms, expected_specs",
    [
        # 基本的なパターン
        ("ロキソニン錠60mg", ["錠"], ["60mg"]),
        ("アスピリン腸溶錠100mg", ["錠"], ["100mg"]),
        ("ムコスタ顆粒20%", ["顆粒"], ["20%"]),
        # 剤形なし
        ("ビタミンC", [], []),
        # 規格なし
        ("アスピリン錠", ["錠"], []),
        # OD錠（最長の剤形を優先）
        ("ロキソニンOD錠60mg", ["OD錠"], ["60mg"]),
        # 複数規格（最初のみ）
        ("配合剤10mg5mg", [], ["10mg"]),
        # 全角規格
        ("アスピリン錠１００ｍｇ", ["錠"], ["100mg"]),
        # 小数点
        ("薬剤0.5mg", [], ["0.5mg"]),
        # mL規格
        ("シロップ5mL", ["シロップ"], ["5mL"]),
    ],
)
def test_extract_dosage_forms_and_specs(
    text: str, expected_forms: list, expected_specs: list
) -> None:
    """剤形と規格の抽出"""
    processor = OCRProcessor()

    result = processor._extract_dosage_forms_and_specs(text)

    assert result["forms"] == expected_forms
    assert result["specs"] == expected_specs


def test_extract_dosage_forms_multiple_forms() -> None:
    """複数剤形の処理（最長優先）"""
    processor = OCRProcessor()

    result = processor._extract_dosage_forms_and_specs("薬剤錠OD錠")

    # "錠"と"OD錠"が両方マッチするが、最長の"OD錠"を優先
    assert result["forms"] == ["OD錠"]


# =============================================================================
# _search_by_similarity
# =============================================================================


def test_search_by_similarity_short_keyword() -> None:
    """短いキーワードの類似度検索"""
    processor = OCRProcessor()

    mock_db = MagicMock()
    processor.db_manager = mock_db

    result = processor._search_by_similarity("短い")

    # 7文字未満は検索しない
    assert result == []
    assert mock_db.search_medicines.call_count == 0


def test_search_by_similarity_basic() -> None:
    """基本的な類似度検索"""
    processor = OCRProcessor()

    mock_db = MagicMock()
    mock_db.search_medicines.return_value = [
        {
            "medicine_name": "アムロジピン錠１０ｍｇ「トーワ」",
            "ingredient_name": "アムロジピンベシル酸塩",
            "specification": "１０ｍｇ１錠",
            "manufacturer": "東和薬品",
            "medicine_type": "後発品",
            "price": 12.80,
        }
    ]
    processor.db_manager = mock_db

    result = processor._search_by_similarity("アムロジピンベシル")

    assert len(result) > 0
    assert result[0]["is_similarity_match"] is True


# =============================================================================
# _calculate_similarity
# =============================================================================


@pytest.mark.parametrize(
    "s1, s2, expected",
    [
        ("アムロジン", "アムロジン", 1.0),
        ("完全一致", "完全一致", 1.0),
        ("", "", 0.0),
        ("", "テスト", 0.0),
        ("テスト", "", 0.0),
    ],
)
def test_calculate_similarity(s1: str, s2: str, expected: float) -> None:
    """類似度計算（確定的なケース）"""
    processor = OCRProcessor()

    result = processor._calculate_similarity(s1, s2)

    assert result == expected


def test_calculate_similarity_partial_match() -> None:
    """類似度計算（部分一致）"""
    processor = OCRProcessor()

    result1 = processor._calculate_similarity("アムロジピン", "アムロジピン錠")
    result2 = processor._calculate_similarity("類似", "頬似")

    assert 0.0 < result1 < 1.0
    assert 0.0 < result2 < 1.0


# =============================================================================
# _select_best_medicine_per_ingredient
# =============================================================================


def test_select_best_medicine_per_ingredient_empty() -> None:
    """空リストの処理"""
    processor = OCRProcessor()

    result = processor._select_best_medicine_per_ingredient([])

    assert result == []


def test_select_best_medicine_per_ingredient_single() -> None:
    """1件のみの処理"""
    processor = OCRProcessor()
    medicines = [
        {
            "medicine_name": "アムロジン錠１０ｍｇ",
            "ingredient_name": "アムロジピンベシル酸塩",
            "specification": "１０ｍｇ１錠",
            "confidence": 0.90,
        }
    ]

    result = processor._select_best_medicine_per_ingredient(medicines)

    assert len(result) == 1
    assert result[0]["medicine_name"] == "アムロジン錠１０ｍｇ"


def test_select_best_medicine_per_ingredient_duplicate_same_spec() -> None:
    """同一成分・同一規格の重複除去"""
    processor = OCRProcessor()
    medicines = [
        {
            "medicine_name": "アムロジピン錠１０ｍｇ「サワイ」",
            "ingredient_name": "アムロジピンベシル酸塩",
            "specification": "１０ｍｇ１錠",
            "confidence": 0.80,
        },
        {
            "medicine_name": "アムロジピン錠１０ｍｇ「トーワ」",
            "ingredient_name": "アムロジピンベシル酸塩",
            "specification": "１０ｍｇ１錠",
            "confidence": 0.90,
        },
    ]

    result = processor._select_best_medicine_per_ingredient(medicines)

    assert len(result) == 1
    assert result[0]["medicine_name"] == "アムロジピン錠１０ｍｇ「トーワ」"
    assert result[0]["confidence"] == 0.90


def test_select_best_medicine_per_ingredient_different_specs() -> None:
    """同一成分・異なる規格の選択"""
    processor = OCRProcessor()
    medicines = [
        {
            "medicine_name": "アムロジピン錠１０ｍｇ",
            "ingredient_name": "アムロジピンベシル酸塩",
            "specification": "１０ｍｇ１錠",
            "confidence": 0.90,
        },
        {
            "medicine_name": "アムロジピン錠５ｍｇ",
            "ingredient_name": "アムロジピンベシル酸塩",
            "specification": "５ｍｇ１錠",
            "confidence": 0.90,
        },
    ]

    result = processor._select_best_medicine_per_ingredient(medicines)

    assert len(result) == 1
    assert result[0]["specification"] == "５ｍｇ１錠"


def test_select_best_medicine_per_ingredient_multiple_ingredients() -> None:
    """複数成分の処理"""
    processor = OCRProcessor()
    medicines = [
        {
            "medicine_name": "アムロジン錠１０ｍｇ",
            "ingredient_name": "アムロジピンベシル酸塩",
            "specification": "１０ｍｇ１錠",
            "confidence": 0.90,
        },
        {
            "medicine_name": "トラゼンタ錠５ｍｇ",
            "ingredient_name": "リナグリプチン",
            "specification": "５ｍｇ１錠",
            "confidence": 0.95,
        },
    ]

    result = processor._select_best_medicine_per_ingredient(medicines)

    assert len(result) == 2


# =============================================================================
# _extract_spec_value
# =============================================================================


@pytest.mark.parametrize(
    "specification, expected",
    [
        ("100mg1錠", 100.0),
        ("5mg1カプセル", 5.0),
        ("0.5mg", 0.5),
        ("１０ｍｇ", 10.0),
        ("20.5mg", 20.5),
        ("規格なし", float("inf")),
        ("", float("inf")),
    ],
)
def test_extract_spec_value(specification: str, expected: float) -> None:
    """規格値の抽出"""
    processor = OCRProcessor()

    result = processor._extract_spec_value(specification)

    assert result == expected


# =============================================================================
# _enrich_medicine_data
# =============================================================================


def test_enrich_medicine_data_no_db() -> None:
    """DB未接続時のデータ拡充"""
    processor = OCRProcessor()
    processor.db_manager = None

    medicines = [
        {
            "medicine_name": "アスピリン錠100mg",
            "ingredient_name": "アスピリン",
            "confidence": 0.90,
        }
    ]

    result = processor._enrich_medicine_data(medicines)

    assert len(result) == 1
    assert result[0]["has_alternatives"] is False
    assert result[0]["alternative_medicines"] == []
    assert result[0]["display_name"] == "アスピリン錠100mg"


def test_enrich_medicine_data_low_confidence_with_alternatives() -> None:
    """低信頼度・代替薬ありの表示名"""
    processor = OCRProcessor()

    mock_db = MagicMock()
    mock_db.get_medicine_alternatives.return_value = [
        {"medicine_name": "アムロジピン錠１０ｍｇ「トーワ」"},
    ]
    processor.db_manager = mock_db

    medicines = [
        {
            "medicine_name": "アムロジン錠１０ｍｇ",
            "ingredient_name": "アムロジピンベシル酸塩",
            "confidence": 0.70,
        }
    ]

    result = processor._enrich_medicine_data(medicines)

    assert result[0]["display_name"] == "アムロジピンベシル酸塩"
    assert result[0]["has_alternatives"] is True


def test_enrich_medicine_data_low_confidence_no_alternatives() -> None:
    """低信頼度・代替薬なしの表示名"""
    processor = OCRProcessor()

    mock_db = MagicMock()
    mock_db.get_medicine_alternatives.return_value = []
    processor.db_manager = mock_db

    medicines = [
        {
            "medicine_name": "トラゼンタ錠５ｍｇ",
            "ingredient_name": "リナグリプチン",
            "confidence": 0.70,
        }
    ]

    result = processor._enrich_medicine_data(medicines)

    assert result[0]["display_name"] == "トラゼンタ錠５ｍｇ"
    assert result[0]["has_alternatives"] is False
