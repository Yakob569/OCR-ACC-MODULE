import logging
import time
import uuid

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status

from app.schemas.response import OCRResponse
from app.services.pipeline import OCRPipeline


router = APIRouter(prefix="/ocr", tags=["ocr"])
pipeline = OCRPipeline()
logger = logging.getLogger("ocr.extract")


@router.post("/extract", response_model=OCRResponse)
async def extract_receipt(
    request: Request,
    file: UploadFile = File(...),
    debug: bool = Query(default=False),
) -> OCRResponse:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id

    cf_ray = request.headers.get("cf-ray")
    forwarded_for = request.headers.get("x-forwarded-for")
    client_host = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else None)

    start = time.perf_counter()
    logger.info(
        "start request_id=%s method=%s path=%s client_ip=%s cf_ray=%s content_type=%s filename=%s debug=%s",
        request_id,
        request.method,
        request.url.path,
        client_host,
        cf_ray,
        file.content_type,
        file.filename,
        debug,
    )

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
        result = pipeline.process(
            image_bytes=image_bytes,
            filename=file.filename or "upload",
            content_type=file.content_type,
            debug=debug,
            request_id=request_id,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        
        if result.success:
            print(f"SUCCESS request_id={request_id} receipt_type={result.receipt_type} elapsed_ms={elapsed_ms} fields_found={len([f for f in result.fields.values() if f.value is not None])}", flush=True)
        else:
            print(f"EXTRACTION_FAILED request_id={request_id} receipt_type={result.receipt_type} elapsed_ms={elapsed_ms} warnings={', '.join(result.warnings)}", flush=True)
            
        return result
    except ValueError as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.warning(
            "CLIENT_ERROR request_id=%s kind=value_error bytes=%d elapsed_ms=%d detail=%s",
            request_id,
            len(image_bytes),
            elapsed_ms,
            str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.exception(
            "SERVER_ERROR request_id=%s kind=unhandled bytes=%d elapsed_ms=%d error=%s",
            request_id,
            len(image_bytes),
            elapsed_ms,
            str(exc)
        )
        raise
