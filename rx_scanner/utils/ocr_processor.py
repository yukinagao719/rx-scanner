"""
OCR処理クラス
TesseractとOpenCVを使用した文字認識処理
"""

import logging
import os
import platform
import re
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image


class OCRProcessor:
    """OCR処理クラス"""

    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)

        # Tesseractの設定
        self.tesseract_config = {
            "lang": "jpn+eng",
            # OCR Engine Mode 3（デフォルト（利用可能な最適エンジン））
            # Page Segmentation Mode 6（統一ブロックのテキスト）
            "config": "--oem 3 --psm 6",
        }

        self._setup_tesseract_path()

    def _setup_tesseract_path(self):
        """Tesseractのパスをクロスプラットフォームで設定"""

        # 環境変数をチェック
        tesseract_env = os.environ.get("TESSERACT_CMD")
        if tesseract_env and Path(tesseract_env).exists():
            pytesseract.pytesseract.tesseract_cmd = tesseract_env
            self.logger.info(
                f"Using TESSERACT_CMD environment variable: {tesseract_env}"
            )
            return

        # PATH環境変数で利用可能かチェック
        if shutil.which("tesseract"):
            self.logger.info("Tesseract found in PATH")
            return

        # OS別の候補パスを定義
        system = platform.system().lower()

        if system == "darwin":  # macOS
            possible_paths = [
                "/opt/homebrew/bin/tesseract",  # M1/M2 Mac (Homebrew)
                "/usr/local/bin/tesseract",  # Intel Mac (Homebrew)
                "/opt/local/bin/tesseract",  # MacPorts
            ]
        elif system == "windows":  # Windows
            possible_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                rf"C:\Users\{Path.home().name}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
            ]
        elif system == "linux":  # Linux
            possible_paths = [
                "/usr/bin/tesseract",  # APT/YUM
                "/usr/local/bin/tesseract",  # 手動インストール
                "/snap/bin/tesseract",  # Snap
                "/opt/tesseract/bin/tesseract",  # カスタムインストール
            ]
        else:
            # その他のOS
            possible_paths = ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]

        # 候補パスをチェック
        for path in possible_paths:
            if Path(path).exists():
                pytesseract.pytesseract.tesseract_cmd = path
                self.logger.info(f"Tesseract path set to: {path}")
                return

        # 見つからない場合のエラー
        self._log_installation_instructions()

    def _log_installation_instructions(self):
        """Tesseractインストール手順をログ出力"""
        self.logger.error(
            "Tesseract not found. Please install Tesseract OCR:\n"
            "macOS: brew install tesseract tesseract-lang\n"
            "Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki\n"
            "Linux: sudo apt-get install tesseract-ocr tesseract-ocr-jpn\n"
        )
        self.logger.info(
            "Alternative: Set TESSERACT_CMD environment variable to tesseract executable path"
        )

    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        画像前処理

        Args:
            image_path: 画像ファイルパス

        Returns:
            前処理済み画像（numpy配列）
        """
        try:
            # 画像の読み込み
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Cannot read image: {image_path}")

            # グレースケール処理
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # ノイズ除去
            denoised = cv2.medianBlur(gray, 3)

            # コントラスト調整
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)

            # 適応的二値化
            binary = cv2.adaptiveThreshold(
                enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            # モルフォロジー演算
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            self.logger.info("Image preprocessing completed")
            return cleaned

        except Exception as e:
            self.logger.error(f"image preprocessing failed: {e}")
            raise

    def extract_text_regions(self, image: np.ndarray) -> list[tuple[str, dict]]:
        """
        テキスト領域を抽出してOCR処理

        Args:
            image: 前処理済み画像

        Returns:
            (認識テキスト, 信頼度情報)のリスト
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

            # テキスト領域を抽出
            text_regions = []
            n_boxes = len(data["text"])

            for i in range(n_boxes):
                text = data["text"][i].strip()
                conf = int(data["conf"][i])

                # 信頼度が低い or 空のテキストはスキップ
                if conf < 30 or not text:
                    continue

                # 座標情報
                x, y, w, h = (
                    data["left"][i],
                    data["top"][i],
                    data["width"][i],
                    data["height"][i],
                )

                region_info = {
                    "confidence": conf,
                    "bbox": (x, y, w, h),
                    "block_num": data["block_num"][i],
                    "par_num": data["par_num"][i],
                    "line_num": data["line_num"][i],
                    "word_num": data["word_num"][i],
                }

                text_regions.append((text, region_info))

            self.logger.info(f"Extracted {len(text_regions)} text regions")
            return text_regions

        except Exception as e:
            self.logger.error(f"Text extraction failed: {e}")
            raise

    def parse_prescription_text(self, text_regions: list[tuple[str, dict]]) -> dict:
        """
        処方箋テキストを解析して構造化

        Args:
            text_regions: OCR結果のテキスト領域リスト

        Returns:
            解析済み処方箋データ
        """
        try:
            # 全テキストを結合
            all_text = " ".join([text for text, _ in text_regions])

            # 薬剤情報を抽出
            medicines = self._extract_medicines(all_text)

            # 患者情報を抽出
            patient_info = self._extract_patient_info(all_text)

            # 処方日等の情報
            prescription_info = self._extract_prescription_info(all_text)

            result = {
                "medicines": medicines,
                "patient_info": patient_info,
                "prescription_info": prescription_info,
                "raw_text": all_text,
                "confidence_summary": self._calculate_confidence_summary(text_regions),
            }

            self.logger.info(f"Parsed prescription: {len(medicines)} medicines found")
            return result

        except Exception as e:
            self.logger.error(f"Prescription parsing failed: {e}")
            raise

    def _extract_medicines(self, text: str) -> list[dict]:
        """薬剤情報を抽出"""
        medicines = []

        # 剤形の包括的パターン
        forms = (
            "錠|散|液|軟膏|点滴|注射|カプセル|細粒|顆粒|シロップ|ドライシロップ|"
            "内服液|口腔内崩壊錠|チュアブル|坐薬|坐剤|貼付剤|テープ|パップ|"
            "ゲル|クリーム|ローション|吸入|点眼|点鼻|点耳|噴霧|注"
        )

        # 単位の包括的パターン（全角・半角対応）
        units = (
            r"(?:[０-９\d]+(?:[．\.][０-９\d]+)?(?:mg|ｍｇ|g|ｇ|ml|ｍｌ|μg|μｇ|"
            r"％|%|単位|錠|カプセル|包|本|mL|ｍＬ|IU|国際単位)?)?"
        )

        # 薬剤名のパターン（優先度順）
        medicine_patterns = [
            # パターン1: フルネーム（剤形+用量）
            rf"([ア-ンヴガ-ゴザ-ゾダ-ドバ-ボパ-ポヤャユュヨョワヮヰヱヲッー]+(?:{forms}){units})",
            # パターン2: 英数字混在（剤形+用量）
            rf"([A-Za-z０-９\d][A-Za-zア-ンヴガ-ゴザ-ゾダ-ドバ-ボパ-ポヤャユュヨョワヮヰヱヲッー０-９\d]*(?:{forms}){units})",
            # パターン3: 数字先頭パターン（５－ＦＵ注等）
            rf"([０-９\d]{{1,2}}[－－-][A-Za-zＡ-Ｚａ-ｚ]{{1,3}}(?:{forms})?{units})",
            # パターン4: カタカナ+英字混在（ミヤＢＭ錠等）
            rf"([ア-ンヴガ-ゴザ-ゾダ-ドバ-ボパ-ポヤャユュヨョワヮヰヱヲッー]{{2,}}[A-Za-zＡ-Ｚａ-ｚ]{{1,3}}(?:{forms})?{units})",
            # パターン5: 全角英字パターン（ＨＭ散、ＫＭ散等）
            rf"([Ａ-Ｚａ-ｚ]{{2,3}}(?:{forms}){units})",
            # パターン6: 短縮名（2-3文字のカタカナ+剤形）
            rf"([ア-ンヴガ-ゴザ-ゾダ-ドバ-ボパ-ポヤャユュヨョワヮヰヱヲッー]{{2,3}}(?:{forms}){units})",
            # パターン7: 成分名+用量（剤形なし）
            r"([ア-ンヴガ-ゴザ-ゾダ-ドバ-ボパ-ポヤャユュヨョワヮヰヱヲッー]+[０-９\d]+(?:[．\.][０-９\d]+)?(?:mg|ｍｇ|g|ｇ|ml|ｍｌ|μg|μｇ|％|%|単位|mL|ｍＬ|IU|国際単位))",
            # パターン8: 商品名のみ（剤形・用量なし、カタカナ主体）
            r"([ア-ンヴガ-ゴザ-ゾダ-ドバ-ボパ-ポヤャユュヨョワヮヰヱヲッー]{3,})",
            # パターン9: 英語名+剤形
            rf"([A-Z][A-Za-z]{{2,}}(?:{forms})?{units})",
            # パターン10: ひらがな・漢字混在
            rf"([あ-んが-ござ-ぞだ-どば-ぼぱ-ぽやゃゆゅよょわゎゐゑをっー一-龯]{{2,}}(?:{forms})?{units})",
            # パターン11: 2文字カタカナのみ（ウズ、カシ等）
            r"([ア-ンヴガ-ゴザ-ゾダ-ドバ-ボパ-ポヤャユュヨョワヮヰヱヲッー]{2})",
        ]

        # 用法・用量のパターン（全角・半角対応）
        dosage_patterns = [
            r"([０-９\d]+回[０-９\d]+(?:錠|カプセル|包|ｇ|g|ｍｌ|ml))",
            r"([０-９\d]+日[０-９\d]+回)",
            r"(毎食[前後])",
            r"(朝夕食[前後])",
            r"(朝食[前後])",
            r"(昼食[前後])",
            r"(夕食[前後])",
            r"(食[前後])",
            r"(就寝前)",
            r"(起床時)",
            r"([０-９\d]+日分)",
            r"([０-９\d]+週間分)",
            r"(頓服)",
            r"(適量)",
            r"(１回[０-９\d]+(?:錠|カプセル|包|ｇ|g|ｍｌ|ml))",
        ]

        # 方法1: 薬剤名で分割して処理
        medicines_with_dosage = self._extract_by_medicine_splitting(
            text, medicine_patterns, dosage_patterns
        )

        # 方法2: 残った用法用量のみの部分を処理
        orphan_dosages = self._extract_orphan_dosages(
            text, medicine_patterns, dosage_patterns
        )

        # 方法3: データベース検索による補完
        database_matches = self._match_with_database(text)

        # 結果をマージ
        medicines.extend(medicines_with_dosage)
        medicines.extend(database_matches)

        # 薬剤名不明の用法用量も記録（後で手動確認用）
        for dosage in orphan_dosages:
            medicines.append(
                {
                    "name": "[薬剤名不明]",
                    "dosage": dosage,
                    "raw_line": f"[薬剤名不明] {dosage}",
                }
            )

        return medicines

    def _match_with_database(self, text: str) -> list[dict]:
        """
        データベース検索による薬剤名の補完

        Args:
            text: OCRテキスト

        Returns:
            データベースマッチした薬剤のリスト
        """
        try:
            from rx_scanner.database.db_manager import DatabaseManager

            db_manager = DatabaseManager()
            matches = []

            # テキストを単語に分割（スペース、改行、句読点で分割）
            words = re.findall(
                r"[ア-ンヴガ-ゴザ-ゾダ-ドバ-ボパ-ポヤャユュヨョワヮヰヱヲッー一-龯A-Za-z0-9０-９]{2,}",
                text,
            )

            for word in words:
                if len(word) >= 3:  # 3文字以上で検索
                    # データベースで検索
                    results = db_manager.search_medicines(word, limit=5)

                    for result in results:
                        # 信頼度計算（完全一致 > 部分一致）
                        confidence = 0.0
                        product_name = result.get("product_name", "")
                        ingredient_name = result.get("ingredient_name", "")

                        if word == product_name:
                            confidence = 0.95  # 商品名完全一致
                        elif word == ingredient_name:
                            confidence = 0.90  # 成分名完全一致
                        elif word in product_name:
                            confidence = 0.75  # 商品名部分一致
                        elif word in ingredient_name:
                            confidence = 0.70  # 成分名部分一致
                        else:
                            confidence = 0.50  # その他のマッチ

                        if confidence >= 0.70:  # 閾値以上のもののみ採用
                            matches.append(
                                {
                                    "name": product_name,
                                    "ingredient": ingredient_name,
                                    "specification": result.get("specification", ""),
                                    "manufacturer": result.get("manufacturer", ""),
                                    "price": result.get("price", 0.0),
                                    "confidence": confidence,
                                    "matched_word": word,
                                    "raw_line": f"[DB検索] {word} → {product_name}",
                                }
                            )

            self.logger.info(f"Database matching found {len(matches)} medicines")
            return matches

        except Exception as e:
            self.logger.warning(f"Database matching failed: {e}")
            return []

    def _extract_by_medicine_splitting(
        self, text: str, medicine_patterns: list, dosage_patterns: list
    ) -> list[dict]:
        """
        薬剤名で分割して用法用量を抽出

        Args:
            text: OCRテキスト
            medicine_patterns: 薬剤名パターンのリスト
            dosage_patterns: 用法用量パターンのリスト

        Returns:
            薬剤情報のリスト
        """

        medicines = []

        # 全ての薬剤名パターンでマッチを試行
        for pattern in medicine_patterns:
            matches = re.finditer(pattern, text)

            for match in matches:
                medicine_name = match.group(1)
                start_pos = match.end()

                # 薬剤名の後続テキストから用法用量を検索（次の薬剤名まで、最大50文字）
                following_text = self._get_following_text_until_next_medicine(
                    text, start_pos, medicine_patterns
                )

                dosage = self._find_dosage_in_text(following_text, dosage_patterns)

                medicines.append(
                    {
                        "name": medicine_name,
                        "dosage": dosage if dosage else "[用法用量不明]",
                        "raw_line": f"{medicine_name} {dosage if dosage else ''}",
                    }
                )

        return medicines

    def _get_following_text_until_next_medicine(
        self, text: str, start_pos: int, medicine_patterns: list, max_chars: int = 50
    ) -> str:
        """
        次の薬剤名までのテキストを取得（最大文字数制限付き）

        Args:
            text: 全テキスト
            start_pos: 開始位置
            medicine_patterns: 薬剤名パターンのリスト
            max_chars: 最大文字数

        Returns:
            次の薬剤名までのテキスト
        """
        # 最大文字数での切り出し
        end_pos = min(start_pos + max_chars, len(text))
        search_text = text[start_pos:end_pos]

        # 次の薬剤名を検索
        next_medicine_pos = None
        for pattern in medicine_patterns:
            match = re.search(pattern, search_text)
            if match:
                if next_medicine_pos is None or match.start() < next_medicine_pos:
                    next_medicine_pos = match.start()

        # 次の薬剤名が見つかった場合はそこまで、なければ全体
        if next_medicine_pos is not None:
            return search_text[:next_medicine_pos]
        else:
            return search_text

    def _extract_orphan_dosages(
        self, text: str, medicine_patterns: list, dosage_patterns: list
    ) -> list[str]:
        """
        薬剤名なしの用法用量を抽出

        Args:
            text: OCRテキスト
            medicine_patterns: 薬剤名パターンのリスト
            dosage_patterns: 用法用量パターンのリスト

        Returns:
            用法用量のリスト
        """
        orphan_dosages = []

        # 薬剤名がマッチした部分を除外
        text_without_medicines = text
        for pattern in medicine_patterns:
            text_without_medicines = re.sub(pattern, "", text_without_medicines)

        # 残ったテキストから用法用量を抽出
        for pattern in dosage_patterns:
            matches = re.findall(pattern, text_without_medicines)
            orphan_dosages.extend(matches)

        return orphan_dosages

    def _find_dosage_in_text(self, text: str, dosage_patterns: list) -> str:
        """
        テキストから用法用量を検索（複数パターンを結合）

        Args:
            text: 検索対象テキスト
            dosage_patterns: 用法用量パターンのリスト

        Returns:
            見つかった用法用量（複数ある場合はスペース区切りで結合）
        """
        found_dosages = []

        for pattern in dosage_patterns:
            matches = re.findall(pattern, text)
            found_dosages.extend(matches)

        # 重複を除去して結合
        unique_dosages = list(dict.fromkeys(found_dosages))
        return " ".join(unique_dosages) if unique_dosages else ""

    def _extract_patient_info(self, text: str) -> dict:
        """
        患者情報を抽出

        Args:
            text: OCRテキスト

        Returns:
            患者情報の辞書
        """
        patient_info = {}

        # 名前パターン（カタカナ、ひらがな、漢字）
        name_patterns = [
            r"([ア-ンヴ]{2,8})\s*様",
            r"([あ-ん]{2,8})\s*様",
            r"([一-龯]{2,4})\s*様",
        ]

        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                patient_info["name"] = match.group(1)
                break

        # 年齢パターン
        age_match = re.search(r"([0-9０-９]{1,3})\s*歳", text)
        if age_match:
            # 全角数字を半角に変換
            age_str = age_match.group(1)
            age_str = age_str.translate(
                str.maketrans("０１２３４５６７８９", "0123456789")
            )
            patient_info["age"] = int(age_str)

        # 生年月日パターン
        date_patterns = [
            r"(昭和|平成|令和)\s*([0-9０-９]{1,2})\s*年\s*([0-9０-９]{1,2})\s*月\s*([0-9０-９]{1,2})\s*日",
            r"([0-9０-９]{4})\s*年\s*([0-9０-９]{1,2})\s*月\s*([0-9０-９]{1,2})\s*日",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                patient_info["birth_date"] = match.group(0)
                break

        return patient_info

    def _extract_prescription_info(self, text: str) -> dict:
        """
        処方箋情報を抽出

        Args:
            text: OCRテキスト

        Returns:
            処方箋情報の辞書
        """
        prescription_info = {}

        # 処方日パターン
        date_patterns = [
            r"([0-9０-９]{4})\s*年\s*([0-9０-９]{1,2})\s*月\s*([0-9０-９]{1,2})\s*日",
            r"(令和|平成)\s*([0-9０-９]{1,2})\s*年\s*([0-9０-９]{1,2})\s*月\s*([0-9０-９]{1,2})\s*日",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                prescription_info["date"] = match.group(0)
                break

        # 医師名パターン
        doctor_patterns = [
            r"医師\s*([一-龯ア-ンヴ]{2,8})",
            r"Dr\.\s*([A-Za-z\s]{3,20})",
        ]

        for pattern in doctor_patterns:
            match = re.search(pattern, text)
            if match:
                prescription_info["doctor"] = match.group(1)
                break

        # 医療機関パターン
        facility_patterns = [
            r"([一-龯]{3,20}(?:病院|医院|クリニック|診療所))",
            r"([一-龯]{3,20}(?:内科|外科|整形外科|皮膚科|眼科|耳鼻科))",
        ]

        for pattern in facility_patterns:
            match = re.search(pattern, text)
            if match:
                prescription_info["facility"] = match.group(1)
                break

        return prescription_info

    def _calculate_confidence_summary(
        self, text_regions: list[tuple[str, dict]]
    ) -> dict:
        """
        信頼度の統計情報を計算

        Args:
            text_regions: OCR結果のテキスト領域リスト

        Returns:
            信頼度統計の辞書
        """
        if not text_regions:
            return {"average": 0.0, "min": 0.0, "max": 0.0, "count": 0}

        confidences = [region[1]["confidence"] for region in text_regions]

        return {
            "average": sum(confidences) / len(confidences),
            "min": min(confidences),
            "max": max(confidences),
            "count": len(confidences),
        }
