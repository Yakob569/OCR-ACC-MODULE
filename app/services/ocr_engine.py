from __future__ import annotations

import re
import logging
import cv2
import numpy as np
from paddleocr import PaddleOCR

from app.schemas.response import OCRPassDebug

# Disable paddleocr logging to keep console clean
logging.getLogger("ppocr").setLevel(logging.ERROR)

class OCREngine:
    def __init__(self) -> None:
        # Initialize PaddleOCR once
        self.ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    def extract_text(self, images: dict[str, cv2.typing.MatLike]) -> tuple[str, list[str], list[OCRPassDebug]]:
        warnings: list[str] = []
        debug_passes: list[OCRPassDebug] = []

        best_text = ""
        best_score = -1
        
        for variant, image in images.items():
            # PaddleOCR expects BGR or RGB. Our preprocessor provides grayscale (MatLike).
            # Convert to BGR for PaddleOCR
            if len(image.shape) == 2:
                color_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            else:
                color_image = image

            # Perform OCR
            results = self.ocr.ocr(color_image, cls=True)
            
            # PaddleOCR returns a list of results (one per page/image)
            # Each result is a list of [box, (text, confidence)]
            text_lines = []
            if results and results[0]:
                for line in results[0]:
                    text_lines.append(line[1][0])
            
            text = "\n".join(text_lines)
            score = self._score_text(text)
            
            debug_passes.append(
                OCRPassDebug(
                    variant=variant,
                    config="default",
                    score=score,
                    preview=self._preview_text(text),
                )
            )
            
            if score > best_score:
                best_score = score
                best_text = text

        if not best_text.strip():
            warnings.append("OCR returned no readable text.")
        else:
            logger = logging.getLogger("ocr.engine")
            best_variant = next((p.variant for p in debug_passes if p.score == best_score), "unknown")
            logger.info("best_ocr_match variant=%s score=%d", best_variant, best_score)
            
        return best_text, warnings, sorted(debug_passes, key=lambda item: item.score, reverse=True)

    def _score_text(self, text: str) -> int:
        upper_text = text.upper()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        meaningful_lines = [line for line in lines if len(line) >= 4]
        short_lines = [line for line in lines if len(line) <= 2]

        score = min(len(text.strip()) // 20, 120)
        score += len(meaningful_lines) * 4
        score -= len(short_lines) * 6

        keywords = (
            "MEDICAL",
            "SERVICES",
            "PLC",
            "ADDIS",
            "INVOICE",
            "CUSTOMER",
            "CASH",
            "TOTAL",
            "FS",
        )
        score += sum(25 for token in keywords if token in upper_text)

        patterns = (
            r"\d{2}/\d{2}/\d{4}",
            r"\b\d{2}:\d{2}\b",
            r"TOTAL",
            r"INVOICE\s+NO",
            r"CUSTOMER\s+NAME",
            r"FS\s*NO",
        )
        score += sum(20 for pattern in patterns if self._has_pattern(upper_text, pattern))
        return score

    def _has_pattern(self, text: str, pattern: str) -> bool:
        return re.search(pattern, text) is not None

    def _preview_text(self, text: str) -> str:
        compact = " ".join(text.split())
        return compact[:180]
