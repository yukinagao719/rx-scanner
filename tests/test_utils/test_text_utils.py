"""
text_utils.py のテスト

テスト対象:
- normalize_to_katakana(): ひらがな→カタカナ変換
"""

import pytest

from rx_scanner.utils.text_utils import normalize_to_katakana

# =============================================================================
# 基本動作の確認
# =============================================================================


def test_basic_hiragana_to_katakana() -> None:
    """ひらがな→カタカナ変換"""
    input_text = "あいうえお"
    expected = "アイウエオ"

    result = normalize_to_katakana(input_text)

    assert result == expected


def test_katakana_remains_unchanged() -> None:
    """カタカナ入力の変換"""
    input_text = "カタカナ"
    expected = "カタカナ"

    result = normalize_to_katakana(input_text)

    assert result == expected


def test_mixed_text_conversion() -> None:
    """混在テキストの変換"""
    input_text = "これはテスト123日本です"
    expected = "コレハテスト123日本デス"

    result = normalize_to_katakana(input_text)

    assert result == expected


# =============================================================================
# 網羅的なパターンテスト
# =============================================================================


@pytest.mark.parametrize(
    "input_text, expected_output",
    [
        # 基本的な五十音
        ("あいうえお", "アイウエオ"),
        ("かきくけこ", "カキクケコ"),
        ("さしすせそ", "サシスセソ"),
        ("たちつてと", "タチツテト"),
        ("なにぬねの", "ナニヌネノ"),
        ("はひふへほ", "ハヒフヘホ"),
        ("まみむめも", "マミムメモ"),
        ("やゆよ", "ヤユヨ"),
        ("らりるれろ", "ラリルレロ"),
        ("わをん", "ワヲン"),
        # 濁音・半濁音
        ("がぎぐげご", "ガギグゲゴ"),
        ("ざじずぜぞ", "ザジズゼゾ"),
        ("だぢづでど", "ダヂヅデド"),
        ("ばびぶべぼ", "バビブベボ"),
        ("ぱぴぷぺぽ", "パピプペポ"),
        # 小文字
        ("きゃきゅきょ", "キャキュキョ"),
        ("しゃしゅしょ", "シャシュショ"),
        ("ちゃちゅちょ", "チャチュチョ"),
        ("にゃにゅにょ", "ニャニュニョ"),
        # カタカナ
        ("アイウエオ", "アイウエオ"),
        ("カタカナ", "カタカナ"),
        # 漢字
        ("漢字", "漢字"),
        ("日本語", "日本語"),
        # 英数字・記号
        ("abc123", "abc123"),
        ("ABC123", "ABC123"),
        ("!@#$%", "!@#$%"),
        # 混在パターン
        ("ひらがなとカタカナと漢字123", "ヒラガナトカタカナト漢字123"),
        ("あいうえお12345", "アイウエオ12345"),
    ],
)
def test_normalize_various_patterns(input_text: str, expected_output: str) -> None:
    """
    様々なパターンのテスト（パラメトライズド）

    Args:
        input_text: 入力テキスト
        expected_output: 期待される出力
    """
    result = normalize_to_katakana(input_text)

    assert result == expected_output


# =============================================================================
# エッジケースと境界値
# =============================================================================


def test_empty_string() -> None:
    """空文字列の処理"""
    result = normalize_to_katakana("")

    assert result == ""


def test_single_hiragana_character() -> None:
    """1文字のひらがな"""
    result = normalize_to_katakana("あ")

    assert result == "ア"


def test_long_text() -> None:
    """長いテキストの処理"""
    hiragana_chars = (
        "あいうえおかきくけこさしすせそたちつてとなにぬねの"
        "はひふへほまみむめもやゆよらりるれろわをん"
    )
    long_hiragana = hiragana_chars * 10

    result = normalize_to_katakana(long_hiragana)

    assert len(result) == len(long_hiragana)
    assert "あ" not in result
    assert "い" not in result


def test_special_characters_preserved() -> None:
    """特殊文字が保持される事を確認"""
    input_text = "あいうえお\n\t　.,!?"

    result = normalize_to_katakana(input_text)

    assert "アイウエオ" in result
    assert "\n" in result
    assert "\t" in result
    assert "　" in result
    assert "." in result
    assert "!" in result


def test_hiragana_boundary_characters() -> None:
    """
    ひらがなの境界文字のテスト

    Unicode範囲の境界値:
    - U+3041 (ぁ) - ひらがな範囲の開始
    - U+3096 (ゖ) - ひらがな範囲の終了
    """
    result_start = normalize_to_katakana("ぁ")
    result_end = normalize_to_katakana("ゖ")

    assert result_start != "ぁ"
    assert result_end != "ゖ"


# =============================================================================
# 実際の使用例
# =============================================================================


def test_medicine_name_normalization() -> None:
    """薬剤名の正規化"""
    ocr_result = "ろきそにん"

    normalized = normalize_to_katakana(ocr_result)

    assert normalized == "ロキソニン"


def test_mixed_input_from_ocr() -> None:
    """OCR結果の混在テキスト"""
    ocr_text = "ろきそにん錠60mg"

    normalized = normalize_to_katakana(ocr_text)

    assert normalized == "ロキソニン錠60mg"


@pytest.mark.parametrize(
    "medicine_name",
    [
        "あすぴりん",
        "かろなーる",
        "むこすた",
        "がすたー",
    ],
)
def test_common_medicine_names(medicine_name: str) -> None:
    """複数の薬剤名のテスト"""
    hiragana_chars = (
        "あいうえおかきくけこさしすせそたちつてとなにぬねの"
        "はひふへほまみむめもやゆよらりるれろわをん"
    )

    result = normalize_to_katakana(medicine_name)

    for char in hiragana_chars:
        assert char not in result
