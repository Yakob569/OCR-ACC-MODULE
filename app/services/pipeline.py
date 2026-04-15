from __future__ import annotations

from app.core.config import get_settings
from app.schemas.response import OCRResponse
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

    def process(self, image_bytes: bytes, filename: str, content_type: str) -> OCRResponse:
        max_bytes = self.settings.max_upload_size_mb * 1024 * 1024
        if len(image_bytes) > max_bytes:
            raise ValueError(
                f"File exceeds the {self.settings.max_upload_size_mb} MB upload limit."
            )

        preprocess_result = self.preprocessor.run(image_bytes)
        text, ocr_warnings = self.ocr_engine.extract_text(preprocess_result.image)
        fields, items, parse_warnings = self.template_parser.parse(text)
        fields, items, final_warnings = self.confidence_scorer.normalize(
            fields,
            items,
            preprocess_result.warnings + ocr_warnings + parse_warnings,
        )

        raw_text = text if self.settings.debug_ocr_text else None
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
        )

