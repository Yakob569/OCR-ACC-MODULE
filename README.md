# Receipt OCR Backend

Python FastAPI backend for template-aware receipt OCR.

## Primary Run Path: Docker

```bash
docker build -t receipt-ocr-backend .
docker run -d --name receipt-ocr-backend-test -p 8000:8000 receipt-ocr-backend
```

The container is the primary startup path because it includes the OCR system dependency and keeps runtime setup consistent.

## Docker Control

Start the app:

```bash
docker build -t receipt-ocr-backend .
docker run -d --name receipt-ocr-backend-test -p 8000:8000 receipt-ocr-backend
```

Stop the running app:

```bash
docker stop receipt-ocr-backend-test
```

Remove the stopped container:

```bash
docker rm receipt-ocr-backend-test
```

Stop and remove it in one command:

```bash
docker rm -f receipt-ocr-backend-test
```

See running containers:

```bash
docker ps
```

See app logs:

```bash
docker logs -f receipt-ocr-backend-test
```

## Local Run

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## OCR Runtime Note

The repo currently uses:

- `opencv-python` for preprocessing
- `paddleocr` for OCR engine
- `paddlepaddle` (CPU version) for inference

## API

- `GET /health`
- `POST /api/v1/ocr/extract`

## Notes

- The first version is scaffolded for one known receipt template.
- OCR extraction now uses **PaddleOCR** for improved robustness on rotated or low-quality receipt images.
- Sample receipt images currently live in the repo root and can be used for manual testing.

## Environment

Copy `.env.example` to `.env` if you want to override defaults.

## Docker

The repo includes a `Dockerfile` that installs:

- Python dependencies
- System libraries for OpenCV and Paddle (libgl1, libglib2.0, libssl)

Example build and run:

```bash
docker build -t receipt-ocr-backend .
docker run -d --name receipt-ocr-backend-test -p 8000:8000 receipt-ocr-backend
```

Example test request:

```bash
curl -X POST "http://localhost:8000/api/v1/ocr/extract" \
  -F "file=@photo_2026-04-15_09-49-48.jpg"
```

Example test request with a different image:

```bash
curl -X POST "http://localhost:8000/api/v1/ocr/extract" \
  -F "file=@photo_2026-04-15_09-49-49.jpg"
```
