"""テキスト処理ユーティリティ"""


def normalize_to_katakana(text: str) -> str:
    """
    ひらがなをカタカナに変換

    Args:
        text: 変換対象テキスト

    Returns:
        カタカナに変換されたテキスト
    """
    katakana = ""
    for char in text:
        code = ord(char)
        # ひらがな範囲（U+3041-U+3096）をカタカナに変換
        if 0x3041 <= code <= 0x3096:
            katakana += chr(code + 0x60)
        else:
            katakana += char
    return katakana
