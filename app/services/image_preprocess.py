from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class PreprocessResult:
    image: np.ndarray
    ocr_images: dict[str, np.ndarray]
    warnings: list[str]
    notes: list[str]


class ImagePreprocessor:
    def run(self, image_bytes: bytes) -> PreprocessResult:
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("The uploaded file could not be decoded as an image.")

        warnings: list[str] = []
        notes: list[str] = []
        height, width = image.shape[:2]
        if min(height, width) < 500:
            warnings.append("Image resolution is low and may reduce OCR quality.")

        working = self._resize_for_ocr(image, notes)
        document = self._extract_document(working, notes)
        grayscale = cv2.cvtColor(document, cv2.COLOR_BGR2GRAY)
        normalized = self._normalize_lighting(grayscale)
        sharpened = self._sharpen(normalized)
        denoised = cv2.GaussianBlur(sharpened, (3, 3), 0)

        adaptive = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )
        otsu = cv2.threshold(
            denoised,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )[1]
        inverted = cv2.bitwise_not(adaptive)

        notes.append("Generated OCR variants: enhanced_gray, adaptive_threshold, otsu_threshold, inverted_threshold.")
        return PreprocessResult(
            image=adaptive,
            ocr_images={
                "enhanced_gray": denoised,
                "adaptive_threshold": adaptive,
                "otsu_threshold": otsu,
                "inverted_threshold": inverted,
            },
            warnings=warnings,
            notes=notes,
        )

    def _resize_for_ocr(self, image: np.ndarray, notes: list[str]) -> np.ndarray:
        height, width = image.shape[:2]
        target_width = 1600
        if width >= target_width:
            notes.append("Kept original image size for OCR preprocessing.")
            return image

        scale = target_width / width
        resized = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        notes.append(f"Upscaled image by {scale:.2f}x for OCR.")
        return resized

    def _extract_document(self, image: np.ndarray, notes: list[str]) -> np.ndarray:
        grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(grayscale, (5, 5), 0)
        edges = cv2.Canny(blurred, 75, 200)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edges = cv2.dilate(edges, kernel, iterations=2)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        image_area = image.shape[0] * image.shape[1]

        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
            perimeter = cv2.arcLength(contour, True)
            approximation = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            if len(approximation) != 4:
                continue
            if cv2.contourArea(approximation) < image_area * 0.15:
                continue

            notes.append("Detected receipt contour and applied perspective correction.")
            return self._warp_perspective(image, approximation.reshape(4, 2).astype(np.float32))

        notes.append("Receipt contour was not confidently detected; using full image.")
        return image

    def _normalize_lighting(self, grayscale: np.ndarray) -> np.ndarray:
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        return clahe.apply(grayscale)

    def _sharpen(self, image: np.ndarray) -> np.ndarray:
        blurred = cv2.GaussianBlur(image, (0, 0), 3)
        return cv2.addWeighted(image, 1.5, blurred, -0.5, 0)

    def _warp_perspective(self, image: np.ndarray, points: np.ndarray) -> np.ndarray:
        rect = self._order_points(points)
        top_left, top_right, bottom_right, bottom_left = rect

        width_top = np.linalg.norm(top_right - top_left)
        width_bottom = np.linalg.norm(bottom_right - bottom_left)
        height_right = np.linalg.norm(top_right - bottom_right)
        height_left = np.linalg.norm(top_left - bottom_left)

        max_width = int(max(width_top, width_bottom))
        max_height = int(max(height_left, height_right))
        destination = np.array(
            [
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1],
            ],
            dtype=np.float32,
        )

        matrix = cv2.getPerspectiveTransform(rect, destination)
        return cv2.warpPerspective(image, matrix, (max_width, max_height))

    def _order_points(self, points: np.ndarray) -> np.ndarray:
        rect = np.zeros((4, 2), dtype=np.float32)
        sums = points.sum(axis=1)
        diffs = np.diff(points, axis=1)

        rect[0] = points[np.argmin(sums)]
        rect[2] = points[np.argmax(sums)]
        rect[1] = points[np.argmin(diffs)]
        rect[3] = points[np.argmax(diffs)]
        return rect
