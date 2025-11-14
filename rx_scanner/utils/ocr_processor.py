"""
OCR処理クラス
TesseractとOpenCVを使用した文字認識処理
"""

import logging
import os
import platform
import re
import shutil
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image
from rapidfuzz import fuzz

from rx_scanner.database.db_manager import DatabaseManager
from rx_scanner.utils.text_utils import normalize_to_katakana


class OCRProcessor:
    """OCR処理クラス"""

    # 剤形リスト
    DOSAGE_FORMS = [
        "錠",
        "ＯＤ錠",
        "OD錠",
        "カプセル",
        "細粒",
        "顆粒",
        "散",
        "シロップ",
        "ドライシロップ",
        "ＤＳ",
        "DS",
        "懸濁",
        "ゼリー",
        "チュアブル",
        "トローチ",
        "ＯＤフィルム",
        "ODフィルム",
        "注",
        "液",
        "点眼",
        "軟膏",
        "クリーム",
        "点鼻",
        "坐剤",
        "坐薬",
        "吸入",
        "吸入用",
        "貼付",
        "点耳",
    ]

    # ストップワード
    STOP_WORDS = [
        "キット",
        "セット",
        "バッグ",
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # DB接続
        try:
            self.db_manager = DatabaseManager()
        except Exception as e:
            self.db_manager = None
            self.logger.error(f"Database initialization failed: {e}")

        # Tesseractの設定
        self.tesseract_config = {
            "lang": "jpn+eng",
            # OCR Engine Mode 1（LSTM）
            # Page Segmentation Mode 6（uniform text block）
            "config": "--oem 1 --psm 6",
        }

        # Tesseractのパスの設定
        self._setup_tesseract_path()

    def process_image(self, image_path: str) -> dict:
        """
        画像を処理してOCR結果を返す

        Args:
            image_path: 画像ファイルパス

        Returns:
            解析済み処方箋データ
        """
        # 前処理
        preprocessed = self._preprocess_image(image_path)

        # テキスト領域抽出
        text_regions = self._extract_text_regions(preprocessed)

        # 処方箋テキスト解析
        result = self._parse_prescription_text(text_regions)

        return result

    def _preprocess_image(
        self, image_path: str, scale: float = 2, denoise: int = 0
    ) -> np.ndarray:
        """
        画像前処理（最適化版）

        Args:
            image_path: 画像ファイルパス
            scale: 拡大率
            denoise: ノイズ除去強度（0 = なし）

        Returns:
            前処理済み画像（numpy配列）
        """
        try:
            # 画像の読み込み
            image = cv2.imread(image_path)
            if image is None:
                if not Path(image_path).exists():
                    raise FileNotFoundError(
                        f"画像ファイルが見つかりません: {image_path}"
                    )
                raise ValueError(f"画像形式が不正です: {image_path}")

            # グレースケール変換
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # 上下30%をクロップ（処方箋の中央部分のみを使用）
            height, width = gray.shape
            y_start = int(height * 0.30)
            y_end = int(height * 0.70)
            gray = gray[y_start:y_end, :]

            # 画像を拡大してOCR精度を向上
            height, width = gray.shape
            enlarged = cv2.resize(
                gray,
                (int(width * scale), int(height * scale)),
                interpolation=cv2.INTER_CUBIC,
            )

            # ノイズ除去
            denoised = cv2.fastNlMeansDenoising(enlarged, h=denoise)

            # 大津の二値化（自動閾値）
            _, binary = cv2.threshold(
                denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            self.logger.info(
                f"Image preprocessing completed (scale={scale}, denoise={denoise})"
            )
            return binary

        except Exception as e:
            self.logger.error(f"Image preprocessing failed: {e}")
            raise

    def _extract_text_regions(self, image: np.ndarray) -> list[tuple[str, int]]:
        """
        テキスト領域を抽出してOCR処理

        Args:
            image: 前処理済み画像

        Returns:
            (テキスト, 行番号)のタプルのリスト
        """
        try:
            # PILイメージに変換
            pil_image = Image.fromarray(image)

            # OCR実行
            data = pytesseract.image_to_data(
                pil_image,
                lang=self.tesseract_config["lang"],
                config=self.tesseract_config["config"],
                output_type=pytesseract.Output.DICT,
            )

            # テキストと行番号を抽出（信頼度でフィルタリング）
            text_regions = []
            n_boxes = len(data["text"])

            for i in range(n_boxes):
                text = data["text"][i].strip()
                conf = int(data["conf"][i])

                # 信頼度が低い or 空のテキストはスキップ
                if conf < 30 or not text:
                    continue

                line_num = data["line_num"][i]
                text_regions.append((text, line_num))

            self.logger.info(f"Extracted {len(text_regions)} text regions")
            return text_regions

        except Exception as e:
            self.logger.error(f"Text extraction failed: {e}")
            raise

    def _parse_prescription_text(self, text_regions: list[tuple[str, int]]) -> dict:
        """
        処方箋テキストを解析して構造化（行単位で処理）

        Args:
            text_regions: OCR結果の(テキスト, 行番号)のリスト

        Returns:
            解析済み処方箋データ
        """
        try:
            # UI表示用の全テキスト
            all_text = "".join([text for text, _ in text_regions])

            # 行ごとにグループ化
            lines = defaultdict(list)
            for text, line_num in text_regions:
                lines[line_num].append(text)

            # 各行から薬剤を抽出
            all_medicines = []
            for line_words in lines.values():
                line_text = "".join(line_words)

                # テキスト正規化（ひらがな→カタカナ）
                normalized_line_text = normalize_to_katakana(line_text)

                # この行から薬剤を抽出
                line_medicines = self._extract_medicines(normalized_line_text)

                all_medicines.extend(line_medicines)

            result = {
                "medicines": all_medicines,
                "raw_text": all_text,
            }

            self.logger.info(
                f"Parsed prescription: {len(all_medicines)} medicines found "
                f"from {len(lines)} lines"
            )
            return result

        except Exception as e:
            self.logger.error(f"Prescription parsing failed: {e}")
            raise

    def _setup_tesseract_path(self):
        """
        Tesseractのパスをクロスプラットフォームで設定

        検索順序:
        1. TESSERACT_CMD環境変数（カスタムパス）
        2. システムPATH
        3. OS別の標準インストール先（macOS/Windows）
        """
        # 環境変数チェック（最優先）
        tesseract_env = os.environ.get("TESSERACT_CMD")
        if tesseract_env and Path(tesseract_env).exists():
            pytesseract.pytesseract.tesseract_cmd = tesseract_env
            self.logger.info(f"Using TESSERACT_CMD: {tesseract_env}")
            return

        # PATHチェック
        if shutil.which("tesseract"):
            self.logger.info("Tesseract found in PATH")
            return

        # OS別の候補パスを定義
        system = platform.system().lower()

        if system == "darwin":  # macOS
            possible_paths = [
                "/opt/homebrew/bin/tesseract",  # Apple Silicon Mac (Homebrew)
                "/usr/local/bin/tesseract",  # Intel Mac (Homebrew)
                "/opt/local/bin/tesseract",  # MacPorts
            ]
        elif system == "windows":  # Windows
            possible_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
        else:
            # サポート対象外のOS（Linux）
            possible_paths = []
            self.logger.warning(
                f"OS '{system}' is not officially supported. "
                "Please set TESSERACT_CMD or add tesseract to PATH"
            )

        # 候補パスをチェック
        for path in possible_paths:
            if Path(path).exists():
                pytesseract.pytesseract.tesseract_cmd = path
                self.logger.info(f"Tesseract path set to: {path}")
                return

        # 見つからない場合
        self.logger.error("Tesseract not found")
        self.logger.info(
            "Please install Tesseract or set TESSERACT_CMD environment variable"
        )

    def _extract_medicines(self, text: str) -> list[dict]:
        """
        薬剤情報を抽出（1行単位で処理）

        Args:
            text: 1行分の正規化済みOCRテキスト

        Returns:
            抽出された薬剤情報のリスト
        """
        # DB検索
        database_matches = self._match_with_database(text)

        # 成分ごとに最適な薬剤を選択
        selected_medicines = self._select_best_medicine_per_ingredient(database_matches)

        # 薬剤データを拡充（代替薬剤情報・表示名を追加）
        enriched_medicines = self._enrich_medicine_data(selected_medicines)

        self.logger.info(f"Extracted {len(enriched_medicines)} unique medicines")
        return enriched_medicines

    def _match_with_database(self, text: str) -> list[dict]:
        """
        DB検索による薬剤名の補完（1行単位）

        Args:
            text: 1行単位のOCRテキスト

        Returns:
            DBマッチした薬剤のリスト（重複除去前）
        """
        try:
            # DB接続チェック
            if not self.db_manager:
                self.logger.warning("Database not available, skipping search")
                return []

            # OCRテキストから剤形・規格を抽出
            dosage_info = self._extract_dosage_forms_and_specs(text)
            ocr_forms = dosage_info["forms"]
            ocr_specs = dosage_info["specs"]

            self.logger.info(f"OCR extracted forms: {ocr_forms}, specs: {ocr_specs}")

            # カタカナ全字と漢字の連続を抽出
            words = re.findall(
                r"[ア-ンヴガ-ゴザ-ゾダ-ドバ-ボパ-ポヤャユュヨョワヮヰヱヲッー一-龯]+",
                text,
            )
            # 3文字以上のみフィルタ
            words = [word for word in words if len(word) >= 3]

            matches = []

            for word in words:
                # ストップワードはスキップ
                if word in self.STOP_WORDS:
                    self.logger.debug(f"Skipping stop word: {word}")
                    continue

                # DB検索
                results = self.db_manager.search_medicines(word, limit=5)

                # 7文字以上の単語の場合、類似度検索を追加（OCRエラー対応）
                if len(word) >= 7:
                    similarity_results = self._search_by_similarity(word)
                    results.extend(similarity_results)

                for result in results:
                    medicine_name = result["medicine_name"]
                    ingredient_name = result["ingredient_name"]
                    specification = result["specification"]

                    # 信頼度スコアリング（0.1刻みの4段階）:
                    # - 1.00: 商品名完全一致（メーカー名まで特定）
                    # - 0.90: 剤形+規格一致（規格まで特定）
                    # - 0.80: 成分名完全一致（成分のみ特定）
                    # - 0.70: 部分一致・類似度検索
                    # 閾値: 0.70以上で採用、0.90以上で薬剤名表示
                    confidence = 0.0

                    if word == medicine_name:
                        confidence = 1.00  # 商品名完全一致
                    elif word == ingredient_name:
                        # 成分名完全一致（剤形・規格一致で0.90に引き上げ）
                        confidence = 0.80
                    elif word in medicine_name or word in ingredient_name:
                        confidence = 0.70  # 部分一致
                    elif result.get("is_similarity_match"):
                        confidence = 0.70
                    else:
                        continue

                    # 剤形・規格マッチングによる信頼度向上
                    # （商品名完全一致は既に最高信頼度なのでスキップ）
                    if confidence < 1.00:
                        form_match = False
                        spec_match = False

                        # 剤形マッチング
                        if ocr_forms and ocr_forms[0] in medicine_name:
                            form_match = True

                        # 規格マッチング
                        if ocr_specs:
                            # 薬剤名を正規化（全角→半角）
                            medicine_normalized = (
                                medicine_name.replace("ｍｇ", "mg")
                                .replace("ｇ", "g")
                                .replace("ｍＬ", "mL")
                                .replace("％", "%")
                                .translate(
                                    str.maketrans(
                                        "０１２３４５６７８９．", "0123456789."
                                    )
                                )
                            )

                            # 正規表現で完全一致
                            pattern = r"(?<![0-9.])" + re.escape(ocr_specs[0])
                            if re.search(pattern, medicine_normalized):
                                spec_match = True

                        # 剤形・規格の両方がマッチした場合、信頼度を向上
                        if form_match and spec_match:
                            # 剤形+規格が一致すれば0.90に引き上げ
                            confidence = 0.90
                            self.logger.debug(
                                f"Form+Spec match: {medicine_name} "
                                f"(confidence: {confidence})"
                            )

                    # 閾値以上のもののみ採用
                    if confidence >= 0.70:
                        matches.append(
                            {
                                "medicine_name": medicine_name,
                                "ingredient_name": ingredient_name,
                                "specification": specification,
                                "manufacturer": result["manufacturer"],
                                "medicine_type": result["medicine_type"],
                                "price": result["price"],
                                "confidence": confidence,
                                "matched_word": word,
                            }
                        )

            self.logger.info(f"Database matching found {len(matches)} medicines")
            return matches

        except Exception as e:
            self.logger.warning(f"Database matching failed: {e}")
            return []

    def _extract_dosage_forms_and_specs(self, text: str) -> dict:
        """
        OCRテキストから剤形と規格を抽出

        Args:
            text: OCRテキスト

        Returns:
            {"forms": [...], "specs": [...]} の辞書
        """
        # 剤形を抽出
        found_forms = []
        for form in self.DOSAGE_FORMS:
            if form in text:
                found_forms.append(form)

        # 最長の剤形のみ採用（"錠"と"OD錠"が両方マッチした場合は"OD錠"を優先）
        if found_forms:
            found_forms = [max(found_forms, key=len)]

        # 規格を抽出
        spec_pattern = (
            r"([\d０-９]+(?:[．\.][\d０-９]+)?(?:mg|ｍｇ|g|ｇ|mL|ｍＬ|ml|μg|μｇ|％|%))"
        )
        found_specs = [
            spec.replace("ｍｇ", "mg")
            .replace("ｍＬ", "mL")
            .replace("ｇ", "g")
            .replace("％", "%")
            .translate(str.maketrans("０１２３４５６７８９．", "0123456789."))
            for spec in re.findall(spec_pattern, text)
        ]

        # 最初の規格のみ採用（1行に1つの規格が基本）
        if found_specs:
            found_specs = [found_specs[0]]

        self.logger.debug(f"Extracted forms: {found_forms}, specs: {found_specs}")

        return {"forms": found_forms, "specs": found_specs}

    def _search_by_similarity(
        self, keyword: str, min_similarity: float = 0.70
    ) -> list[dict]:
        """
        類似度検索（OCRエラー対応）

        Args:
            keyword: 検索キーワード
            min_similarity: 最小類似度（0.0〜1.0）

        Returns:
            類似度でフィルタされた検索結果のリスト
        """
        try:
            # DB接続チェック
            if not self.db_manager:
                return []

            # 長い単語のみ対象（7文字以上）
            if len(keyword) < 7:
                return []

            # FTS検索で候補取得（前方3文字）
            prefix = keyword[:3]
            candidates = self.db_manager.search_medicines(prefix, limit=100)

            # 類似度を計算してフィルタ
            results = []
            for candidate in candidates:
                ingredient_name = candidate["ingredient_name"]
                medicine_name = candidate["medicine_name"]

                # キーワードと同じ長さで比較（長さの違いによる類似度低下を防ぐ）
                keyword_len = len(keyword)

                # 成分名との類似度
                ingredient_name_short = ingredient_name[:keyword_len]
                ingredient_similarity = self._calculate_similarity(
                    keyword, ingredient_name_short
                )

                # 薬剤名との類似度
                medicine_name_short = medicine_name[:keyword_len]
                medicine_similarity = self._calculate_similarity(
                    keyword, medicine_name_short
                )

                # 高い方を採用
                similarity = max(ingredient_similarity, medicine_similarity)

                if similarity >= min_similarity:
                    # 類似度検索でヒットしたことを示すフラグのみ設定
                    candidate["is_similarity_match"] = True
                    results.append(candidate)

            self.logger.debug(
                f"Similarity search '{keyword}' "
                f"(min={min_similarity:.2f}) returned {len(results)} results"
            )

            return results

        except Exception as e:
            self.logger.warning(f"Similarity search failed for '{keyword}': {e}")
            return []

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """
        文字列の類似度を計算（0.0〜1.0）

        Args:
            s1: 文字列1
            s2: 文字列2

        Returns:
            類似度（1.0 = 完全一致、0.0 = 全く異なる）
        """
        if not s1 or not s2:
            return 0.0

        # rapidfuzzのレーベンシュタイン距離ベースの類似度を使用
        # fuzz.ratio()は0-100の範囲を返すので、100で割って0.0-1.0に変換
        return fuzz.ratio(s1, s2) / 100.0

    def _select_best_medicine_per_ingredient(self, medicines: list[dict]) -> list[dict]:
        """
        成分ごとに最適な薬剤を1つ選択（2段階）

        第1段階: (成分名, 規格) で重複除去 → 信頼度が高い方を優先
        第2段階: 成分ごとに1つ選択 → 信頼度が高い方、同じなら規格値が低い方を優先

        Args:
            medicines: 薬剤情報のリスト

        Returns:
            成分ごとに最適な薬剤のリスト
        """
        if not medicines:
            return []

        # 第1段階: (成分名, 規格) で重複除去
        by_ingredient_and_spec = {}
        for medicine in medicines:
            ingredient = medicine["ingredient_name"]
            specification = medicine["specification"]

            key = (ingredient, specification)
            if key not in by_ingredient_and_spec:
                by_ingredient_and_spec[key] = medicine
            else:
                # 信頼度が高い方を残す
                existing = by_ingredient_and_spec[key]
                if medicine["confidence"] > existing["confidence"]:
                    by_ingredient_and_spec[key] = medicine

        # 第2段階: 成分名のみで重複除去（規格違いを除外）
        by_ingredient = {}
        for medicine in by_ingredient_and_spec.values():
            ingredient = medicine["ingredient_name"]
            if ingredient not in by_ingredient:
                by_ingredient[ingredient] = medicine
            else:
                existing = by_ingredient[ingredient]
                new_confidence = medicine.get("confidence", 0.0)
                existing_confidence = existing.get("confidence", 0.0)

                # 信頼度が高い方を優先
                should_replace = False
                if new_confidence > existing_confidence:
                    should_replace = True
                elif new_confidence == existing_confidence:
                    # 信頼度が同じ場合、規格値が低い方を優先
                    new_spec_value = self._extract_spec_value(medicine["specification"])
                    existing_spec_value = self._extract_spec_value(
                        existing["specification"]
                    )
                    should_replace = new_spec_value < existing_spec_value

                if should_replace:
                    by_ingredient[ingredient] = medicine

        return list(by_ingredient.values())

    def _extract_spec_value(self, specification: str) -> float:
        """
        規格から数値を抽出（例: "５ｍｇ１錠" → 5.0）

        Args:
            specification: 規格文字列

        Returns:
            抽出された数値（数値がない場合はfloat("inf")）
        """
        # 全角を半角に変換
        spec_normalized = specification.translate(
            str.maketrans("０１２３４５６７８９．", "0123456789.")
        )

        # 最初の数値を抽出
        match = re.search(r"(\d+(?:\.\d+)?)", spec_normalized)
        return float(match.group(1)) if match else float("inf")

    def _enrich_medicine_data(self, medicines: list[dict]) -> list[dict]:
        """
        薬剤データを拡充（代替薬剤情報・表示名を追加）

        代替薬剤情報を取得し、信頼度に基づいて表示名を設定する。
        - 信頼度 >= 0.90: 薬剤名を表示
        - 信頼度 < 0.90 かつ 代替薬あり: 成分名を表示
        - 信頼度 < 0.90 かつ 代替薬なし: 薬剤名を表示

        Args:
            medicines: 薬剤情報のリスト

        Returns:
            拡充された薬剤リスト
        """
        try:
            # DB接続チェック
            if not self.db_manager:
                self.logger.warning(
                    "Database not available, skipping alternative medicines"
                )

            result = []

            for medicine in medicines:
                medicine_name = medicine["medicine_name"]
                ingredient_name = medicine["ingredient_name"]

                # 代替薬剤情報を取得
                if self.db_manager:
                    alternatives = self.db_manager.get_medicine_alternatives(
                        ingredient_name, exclude_medicine_name=medicine_name
                    )
                else:
                    alternatives = []

                # 代替薬剤があるかチェック
                has_alternatives = len(alternatives) > 0

                # 薬剤データに代替薬剤情報を追加
                medicine_with_alt = medicine.copy()
                medicine_with_alt["has_alternatives"] = has_alternatives
                medicine_with_alt["alternative_medicines"] = alternatives

                # display_name設定ロジック
                confidence = medicine.get("confidence", 0.0)

                # 信頼度が高い場合（成分名完全一致以上 or 剤形+規格一致）は薬剤名表示
                if confidence >= 0.90:
                    medicine_with_alt["display_name"] = medicine_name
                else:
                    # 信頼度が低い場合
                    if not has_alternatives:
                        # 代替薬がない場合は薬剤名を表示
                        medicine_with_alt["display_name"] = medicine_name
                    else:
                        # 代替薬がある場合は成分名を表示
                        medicine_with_alt["display_name"] = ingredient_name

                result.append(medicine_with_alt)

            self.logger.info(
                f"Enriched {len(result)} medicines with alternatives and display names"
            )
            return result

        except Exception as e:
            self.logger.warning(f"Failed to enrich medicine data: {e}")
            return medicines
