# Receipt OCR Service Architecture

## Goal

Build a Python-based backend service that accepts a receipt image, extracts structured receipt data, and exposes the result through an API that can be called from a web app or mobile app.

The first version should optimize for:

- known receipt template
- reliable OCR extraction
- simple deployment
- fast iteration
- clear API responses

We are **not** starting with true AI deblurring. For blurred or weak images, the first version should use image enhancement for OCR, then return confidence scores and processing warnings.

## Recommended Stack

- Language: Python
- API framework: FastAPI
- OCR/image processing:
  - OpenCV for preprocessing
  - **PaddleOCR** for the core OCR engine (significantly more robust than Tesseract for receipts)
- Data validation: Pydantic
- Background jobs: optional later with Celery/RQ if throughput grows
- Storage:
  - local disk in development
  - object storage later if needed
- Database:
  - not required for the first prototype
  - optional later for audit/history

## Why This Architecture

Python is the right fit because the difficult part of this project is not basic HTTP serving. The difficult part is image preprocessing, OCR quality, and template-aware extraction. Python has the strongest ecosystem for those parts.

FastAPI is a good fit because it gives:

- simple REST APIs
- typed request/response models
- automatic OpenAPI docs
- easy integration with web and mobile clients

## High-Level Architecture

```text
Web App / Mobile App
        |
        v
   FastAPI REST API
        |
        v
  OCR Processing Pipeline
        |
        +--> Image Validation
        +--> Image Preprocessing
        +--> OCR Engine
        +--> Template-Aware Field Extraction
        +--> Confidence Scoring
        +--> Structured JSON Response
```

## Service Boundaries

For the first version, keep everything in **one Python service**.

That means:

- one API service
- one OCR pipeline inside it
- one deployable backend

This is better than splitting into multiple microservices now because:

- faster to build
- easier to debug
- easier to test end-to-end
- no extra infra complexity

Later, if needed, we can split into:

- API layer
- OCR worker
- async job queue

But not in version 1.

## Main Request Flow

### 1. Upload

The client sends:

- receipt image file
- optional metadata
  - source app
  - customer id
  - receipt type

### 2. Validation

The backend checks:

- image format
- file size
- minimum resolution
- whether the image likely contains a receipt

If the image is too poor, return a structured failure with a reason.

### 3. Preprocessing

Apply OCR-focused enhancement:

- resize
- grayscale conversion
- contrast normalization
- noise reduction
- thresholding
- deskew
- perspective correction
- region cropping if receipt borders are detected

This step should improve OCR readability, not invent missing data.

### 4. OCR

Run OCR on:

- full receipt image
- optionally specific known regions if region-based extraction performs better

### 5. Template-Aware Parsing

Because the receipt format is known, parse with a rule-based extractor using:

- expected label patterns
- known field positions
- regex-based value extraction
- line grouping for item rows

### 6. Confidence Scoring

For each extracted field, estimate confidence using:

- OCR confidence
- label match quality
- positional consistency
- parsing success

### 7. API Response

Return structured JSON with:

- extracted fields
- item list
- totals
- confidence values
- warnings
- raw OCR text if we want debugging enabled

## Recommended Folder Structure

```text
backend/
  app/
    main.py
    api/
      routes/
        health.py
        ocr.py
    core/
      config.py
      logging.py
    schemas/
      request.py
      response.py
    services/
      image_preprocess.py
      ocr_engine.py
      template_parser.py
      confidence.py
      pipeline.py
    utils/
      file_io.py
      image_utils.py
      regex_utils.py
  tests/
    test_health.py
    test_ocr_api.py
    test_template_parser.py
  samples/
    receipts/
  requirements.txt
  OCR_ARCHITECTURE.md
```

## API Design

### Endpoint 1: Health Check

`GET /health`

Returns service status.

### Endpoint 2: OCR Extraction

`POST /api/v1/ocr/extract`

Accepts:

- multipart image upload

Returns:

- structured receipt data
- confidence
- processing warnings

### Optional Endpoint 3: Debug Extraction

`POST /api/v1/ocr/extract/debug`

Same extraction, but also returns:

- raw OCR lines
- intermediate preprocessing notes
- parser match details

This endpoint is useful during development and should probably be disabled in production.

## Response Shape

Recommended response:

```json
{
  "success": true,
  "receipt_type": "medical_services_receipt",
  "fields": {
    "merchant_name": {
      "value": "BFLC MEDICAL SERVICES PLC",
      "confidence": 0.96
    },
    "branch": {
      "value": "ADDIS ABABA",
      "confidence": 0.92
    },
    "receipt_number": {
      "value": "00002031",
      "confidence": 0.88
    },
    "invoice_number": {
      "value": "ACC-SINU-2025-50428",
      "confidence": 0.84
    },
    "customer_name": {
      "value": "HAREGEWOINE BITEW TEFERA",
      "confidence": 0.79
    },
    "date": {
      "value": "2025-08-02",
      "confidence": 0.90
    },
    "time": {
      "value": "13:02",
      "confidence": 0.91
    },
    "total_amount": {
      "value": 8000.00,
      "confidence": 0.95
    }
  },
  "items": [
    {
      "description": "Order lens Progressive Power / (N)",
      "quantity": 2,
      "unit_price": 2500.00,
      "line_total": 5000.00,
      "confidence": 0.81
    },
    {
      "description": "Frame P82228 (N)",
      "quantity": 1,
      "unit_price": 3000.00,
      "line_total": 3000.00,
      "confidence": 0.78
    }
  ],
  "warnings": [
    "Image quality is moderate",
    "Customer name confidence is lower than total amount"
  ]
}
```

## Parsing Strategy For This Receipt Type

Since this receipt template is mostly fixed, we should use a **hybrid extraction strategy**:

### Header zone

Extract:

- merchant name
- city/branch
- address lines
- phone

### Metadata zone

Extract:

- receipt number
- date
- time
- invoice number
- cashier
- customer name

### Item zone

Extract repeating rows:

- quantity
- unit price
- item name
- line total

### Totals zone

Extract:

- subtotal if available
- cash paid
- total

This region-based design is better than trying to infer all fields from one raw OCR text block.

## Handling Blurred Or Weak Images

The first version should support:

- blur detection
- quality scoring
- preprocessing retry with stronger enhancement settings

The first version should **not** claim to reconstruct hidden text.

If confidence remains too low after preprocessing, return:

- partial extracted data
- warnings
- low-confidence indicators

This is more honest and more maintainable than fake deblurring promises.

## AI Usage Recommendation

For version 1:

- do not depend on paid vision APIs for every request
- do not depend on unstable free API keys

Recommended approach:

- local OCR engine first
- local template parser second
- optional AI fallback later only for low-confidence edge cases

Why:

- lower cost
- better privacy
- more predictable latency
- easier production control

## Mobile And Web Integration

Expose the OCR through a standard REST API.

Clients:

- mobile app uploads image
- web app uploads image
- backend returns JSON

That means the frontend does not need OCR logic. It only needs:

- upload UI
- loading state
- display for extracted fields
- display for warnings/confidence

## Version 1 Scope

Build only these features first:

1. upload one receipt image
2. preprocess image
3. run OCR
4. parse known template
5. return structured JSON
6. include confidence and warnings

Do not add yet:

- user accounts
- dashboards
- queue workers
- multi-template support
- AI deblur models
- database history unless clearly needed

## Development Phases

### Phase 1: Prototype

- build FastAPI service
- add one OCR endpoint
- use sample receipts for testing
- implement one known template parser

### Phase 2: Stabilization

- improve preprocessing
- improve field matching
- add confidence thresholds
- add tests with multiple sample receipts

### Phase 3: Production Readiness

- add persistent storage if needed
- add auth if required
- add async jobs if OCR becomes slow
- add monitoring and logging

## Recommendation

Use a **single Python FastAPI service** with:

- OpenCV preprocessing
- OCR engine
- template-aware parser
- structured JSON API

This is the most workable architecture for now because it is simple, practical, and directly aligned with the receipt format you already know.

## Immediate Next Step

If we agree on this architecture, the next build step should be:

1. scaffold the FastAPI project
2. define request and response schemas
3. add a first `/api/v1/ocr/extract` endpoint
4. implement the preprocessing and OCR pipeline
5. test against the sample receipt images
