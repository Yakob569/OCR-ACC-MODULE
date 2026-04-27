# OCR Module Integration Guide (v2.0)

## Overview
This module has been upgraded to use **Gemini 3.1 Flash Lite**. It now supports batch processing, detailed financial field extraction, and explicit file tracking.

## New Features
- **Batch Processing:** Send multiple images in one request.
- **File Tracking:** Every response object now includes a `filename` field to map data back to the source image.
- **Detailed Schema:** Includes TIN, Merchant details, Transaction metadata, and granular Line Items.
- **Throttling:** The service automatically handles rate limiting (15 RPM) with built-in delays for batch requests.

## Endpoints

### 1. Batch Extraction
**URL:** `/api/v1/extract-batch`  
**Method:** `POST`  
**Content-Type:** `multipart/form-data`  

**Example CURL:**
```bash
curl -X POST \
  -F "files=@receipt1.jpg" \
  -F "files=@receipt2.jpg" \
  http://localhost:8000/api/v1/extract-batch
```

### 2. Single Extraction (Legacy Support)
**URL:** `/api/v1/extract`  
**Method:** `POST`  

---

## Response Schema (JSON)
The response is a **list of objects**. Each object follows this structure:

| Field | Type | Description |
| :--- | :--- | :--- |
| `success` | boolean | True if processing succeeded |
| `filename` | string | **Crucial:** The name of the file provided in the request |
| `receipt_type` | string | e.g., "medical", "retail", "restaurant" |
| `merchant` | object | Contains `name`, `tin`, `address`, `phone` |
| `transaction` | object | Contains `date`, `invoice_number`, `customer_name`, `cashier_name` |
| `items` | array | List of items with `description`, `quantity`, `unit_price`, `line_total`, `tax_amount`, `metadata` |
| `totals` | object | Contains `subtotal`, `tax_total`, `grand_total` |

### Field Detail
Most fields are objects containing:
- `value`: The actual data (string, float, or null).
- `confidence`: AI certainty score (0.0 to 1.0).

---

## Example Response snippet
```json
[
  {
    "success": true,
    "filename": "photo_1.jpg",
    "merchant": {
       "tin": { "value": "12345678", "confidence": 0.98 }
    },
    ...
  }
]
```
