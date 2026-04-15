from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class PreprocessResult:
    image: np.ndarray
    warnings: list[str]


class ImagePreprocessor:
    def run(self, image_bytes: bytes) -> PreprocessResult:
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("The uploaded file could not be decoded as an image.")

        warnings: list[str] = []
        height, width = image.shape[:2]
        if min(height, width) < 500:
            warnings.append("Image resolution is low and may reduce OCR quality.")

        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        normalized = cv2.equalizeHist(grayscale)
        denoised = cv2.GaussianBlur(normalized, (3, 3), 0)
        processed = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )

        return PreprocessResult(image=processed, warnings=warnings)
