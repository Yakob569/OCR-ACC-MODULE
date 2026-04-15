from pydantic import BaseModel, Field


class FieldValue(BaseModel):
    value: str | float | int | None
    confidence: float = Field(ge=0.0, le=1.0)


class Item(BaseModel):
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    line_total: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class OCRPassDebug(BaseModel):
    variant: str
    config: str
    score: int
    preview: str


class OCRDebugInfo(BaseModel):
    preprocess_notes: list[str]
    ocr_passes: list[OCRPassDebug]


class OCRResponse(BaseModel):
    success: bool
    receipt_type: str
    fields: dict[str, FieldValue]
    items: list[Item]
    warnings: list[str]
    raw_text: str | None = None
    debug: OCRDebugInfo | None = None
