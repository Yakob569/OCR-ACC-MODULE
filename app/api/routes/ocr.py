from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.response import OCRResponse
from app.services.pipeline import OCRPipeline


router = APIRouter(prefix="/ocr", tags=["ocr"])
pipeline = OCRPipeline()


@router.post("/extract", response_model=OCRResponse)
async def extract_receipt(file: UploadFile = File(...)) -> OCRResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image uploads are supported.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        return pipeline.process(
            image_bytes=image_bytes,
            filename=file.filename or "upload",
            content_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

