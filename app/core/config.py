from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Receipt OCR Backend"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    max_upload_size_mb: int = 10
    debug_ocr_text: bool = False
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_prefix="OCR_", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
