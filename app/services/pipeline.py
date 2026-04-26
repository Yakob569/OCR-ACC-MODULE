from __future__ import annotations

import logging
import time

from app.core.config import get_settings
from app.schemas.response import OCRDebugInfo, OCRResponse
from app.services.confidence import ConfidenceScorer
from app.services.image_preprocess import ImagePreprocessor
from app.services.ocr_engine import OCREngine
from app.services.template_parser import TemplateParser


class OCRPipeline:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.preprocessor = ImagePreprocessor()
        self.ocr_engine = OCREngine()
        self.template_parser = TemplateParser()
        self.confidence_scorer = ConfidenceScorer()

    def process(
        self,
        image_bytes: bytes,
        filename: str,
        content_type: str,
        debug: bool = False,
        request_id: str | None = None,
    ) -> OCRResponse:
        logger = logging.getLogger("ocr.pipeline")
        total_start = time.perf_counter()

        max_bytes = self.settings.max_upload_size_mb * 1024 * 1024
        if len(image_bytes) > max_bytes:
            raise ValueError(
                f"File exceeds the {self.settings.max_upload_size_mb} MB upload limit."
            )

        preprocess_start = time.perf_counter()
        preprocess_result = self.preprocessor.run(image_bytes)
        preprocess_ms = int((time.perf_counter() - preprocess_start) * 1000)

        ocr_start = time.perf_counter()
        text, ocr_warnings, ocr_passes = self.ocr_engine.extract_text(preprocess_result.ocr_images)
        ocr_ms = int((time.perf_counter() - ocr_start) * 1000)

        parse_start = time.perf_counter()
        fields, items, parse_warnings = self.template_parser.parse(text)
        parse_ms = int((time.perf_counter() - parse_start) * 1000)

        normalize_start = time.perf_counter()
        fields, items, final_warnings = self.confidence_scorer.normalize(
            fields,
            items,
            preprocess_result.warnings + ocr_warnings + parse_warnings,
        )
        normalize_ms = int((time.perf_counter() - normalize_start) * 1000)

        total_ms = int((time.perf_counter() - total_start) * 1000)
        logger.info(
            "timings request_id=%s filename=%s content_type=%s bytes=%d preprocess_ms=%d ocr_ms=%d parse_ms=%d normalize_ms=%d total_ms=%d warnings=%d",
            request_id,
            filename,
            content_type,
            len(image_bytes),
            preprocess_ms,
            ocr_ms,
            parse_ms,
            normalize_ms,
            total_ms,
            len(preprocess_result.warnings) + len(ocr_warnings) + len(parse_warnings),
        )

        emit_debug = debug or self.settings.debug_ocr_text
        raw_text = text if emit_debug else None
        success = any(field.value is not None for field in fields.values()) or bool(items)

        if not success and not final_warnings:
            final_warnings.append("Receipt data could not be extracted from the image.")

        return OCRResponse(
            success=success,
            receipt_type=self.template_parser.receipt_type,
            fields=fields,
            items=items,
            warnings=final_warnings,
            raw_text=raw_text,
            debug=OCRDebugInfo(
                preprocess_notes=preprocess_result.notes,
                ocr_passes=ocr_passes,
            )
            if emit_debug
            else None,
        )
