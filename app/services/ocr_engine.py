from __future__ import annotations

import shutil
from importlib import import_module

import cv2


class OCREngine:
    def __init__(self) -> None:
        self.binary_available = shutil.which("tesseract") is not None
        self.python_backend = self._load_backend()

    def _load_backend(self):
        try:
            return import_module("pytesseract")
        except ModuleNotFoundError:
            return None

    def extract_text(self, image) -> tuple[str, list[str]]:
        warnings: list[str] = []
        if not self.binary_available:
            warnings.append("Tesseract is not installed; OCR text extraction was skipped.")
            return "", warnings

        if self.python_backend is None:
            warnings.append("The pytesseract package is not installed; OCR text extraction was skipped.")
            return "", warnings

        rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        text = self.python_backend.image_to_string(rgb_image)
        if not text.strip():
            warnings.append("OCR returned no readable text.")
        return text, warnings
