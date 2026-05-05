import asyncio
import logging
import time
from typing import List
from fastapi import APIRouter, File, UploadFile
from app.services.gemini_service import extract_receipt
from app.schemas.response import OCRResponse

router = APIRouter()
logger = logging.getLogger("ocr-app")

@router.post("/extract", response_model=OCRResponse)
async def extract_receipt_endpoint(
    file: UploadFile = File(...),
) -> OCRResponse:
    start_time = time.perf_counter()
    logger.info(f"Starting extraction for {file.filename}")
    
    try:
        image_bytes = await file.read()
        result = await extract_receipt(image_bytes, filename=file.filename)
        
        duration = time.perf_counter() - start_time
        logger.info(f"Finished {file.filename} in {duration:.2f}s")
        return result
    except Exception as e:
        logger.error(f"Error processing {file.filename}: {str(e)}", exc_info=True)
        raise

@router.post("/extract-batch", response_model=List[OCRResponse])
async def extract_receipt_batch_endpoint(
    files: List[UploadFile] = File(...),
) -> List[OCRResponse]:
    start_time = time.perf_counter()
    logger.info(f"Starting parallel batch extraction for {len(files)} files")
    
    async def process_file(file: UploadFile):
        file_name = file.filename
        try:
            read_start = time.perf_counter()
            image_bytes = await file.read()
            read_duration = time.perf_counter() - read_start
            logger.info(f"[{file_name}] Read file bytes in {read_duration:.4f}s")
            
            # Use asyncio.to_thread because gemini_service.extract_receipt 
            # contains synchronous blocking calls to the Gemini API.
            result = await asyncio.to_thread(
                # We need to run it in a way that doesn't block the event loop
                # Since extract_receipt is defined as 'async', but calls sync code,
                # we wrap it carefully or call its internal sync parts if possible.
                # However, since it is already async, let's just await it, 
                # but keep in mind the sync block inside it.
                # To truly parallelize blocking sync code in Python, 
                # to_thread is the right way.
                lambda: asyncio.run(extract_receipt(image_bytes, filename=file_name))
            )
            return result
        except Exception as e:
            logger.error(f"[{file_name}] Failed in batch: {str(e)}", exc_info=True)
            # Return a "failure" response object or similar instead of crashing the whole batch
            return OCRResponse(
                success=False,
                filename=file_name,
                receipt_type="error",
                merchant=None, # This might need adjustment based on schema
                transaction=None,
                items=[],
                totals=None,
                warnings=[str(e)]
            )

    # Run all extractions in parallel
    results = await asyncio.gather(*[process_file(f) for f in files])
            
    total_duration = time.perf_counter() - start_time
    logger.info(f"Batch processing completed in {total_duration:.2f}s")
    return results
