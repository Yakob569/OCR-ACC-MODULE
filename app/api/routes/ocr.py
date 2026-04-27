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
    logger.info(f"Starting batch extraction for {len(files)} files")
    
    results = []
    for file in files:
        try:
            file_start = time.perf_counter()
            image_bytes = await file.read()
            result = await extract_receipt(image_bytes, filename=file.filename)
            results.append(result)
            
            file_duration = time.perf_counter() - file_start
            logger.info(f"Processed {file.filename} in {file_duration:.2f}s")
            
            if len(files) > 1 and file != files[-1]:
                await asyncio.sleep(2) # Reduced from 4s to 2s
        except Exception as e:
            logger.error(f"Failed to process {file.filename} in batch: {str(e)}", exc_info=True)
            
    total_duration = time.perf_counter() - start_time
    logger.info(f"Batch processing completed in {total_duration:.2f}s")
    return results
