FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for OpenCV and PaddleOCR
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libgl1 \
       libglib2.0-0 \
       libgomp1 \
       libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Adding httpx and croniter for health check
RUN pip install --no-cache-dir -r requirements.txt httpx croniter

COPY app ./app
COPY tests ./tests
COPY pytest.ini .
COPY README.md .
COPY OCR_ARCHITECTURE.md .
COPY .env.example .

EXPOSE 8000

# Render sets $PORT; fall back to 8000 for local runs.
CMD ["sh", "-c", "python3 app/health_checker.py & uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
