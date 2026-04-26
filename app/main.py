import logging

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.ocr import router as ocr_router
from app.core.config import get_settings
from app.core.logging import configure_logging


settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("ocr-app")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Receipt OCR service for known receipt templates.",
)

app.include_router(health_router)
app.include_router(ocr_router, prefix=settings.api_v1_prefix)
