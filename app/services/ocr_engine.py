from __future__ import annotations

import re
import shutil
from importlib import import_module

import cv2

from app.schemas.response import OCRPassDebug


class OCREngine:
    def __init__(self) -> None:
        self.binary_available = shutil.which("tesseract") is not None
        self.python_backend = self._load_backend()
        self.configs = (
            ("psm6", "--oem 3 --psm 6"),
            ("psm11", "--oem 3 --psm 11"),
            ("psm4", "--oem 3 --psm 4"),
        )

    def _load_backend(self):
        try:
            return import_module("pytesseract")
        except ModuleNotFoundError:
            return None

    def extract_text(self, images: dict[str, cv2.typing.MatLike]) -> tuple[str, list[str], list[OCRPassDebug]]:
        warnings: list[str] = []
        debug_passes: list[OCRPassDebug] = []
        if not self.binary_available:
            warnings.append("Tesseract is not installed; OCR text extraction was skipped.")
            return "", warnings, debug_passes

        if self.python_backend is None:
            warnings.append("The pytesseract package is not installed; OCR text extraction was skipped.")
            return "", warnings, debug_passes

        best_text = ""
        best_score = -1
        for variant, image in images.items():
            rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            for config_name, config in self.configs:
                text = self.python_backend.image_to_string(rgb_image, config=config)
                score = self._score_text(text)
                debug_passes.append(
                    OCRPassDebug(
                        variant=variant,
                        config=config_name,
                        score=score,
                        preview=self._preview_text(text),
                    )
                )
                if score > best_score:
                    best_score = score
                    best_text = text

        if not best_text.strip():
            warnings.append("OCR returned no readable text.")
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
