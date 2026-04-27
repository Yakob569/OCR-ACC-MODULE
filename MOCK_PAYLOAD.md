# Mock OCR Response Payload

This is a sample of the detailed JSON payload returned by the `/api/v1/extract` endpoint using Gemini 3.1 Flash Lite.

```json
{
  "success": true,
  "receipt_type": "medical",
  "merchant": {
    "name": {
      "value": "WGGA MEDICAL SERVICES PLC",
      "confidence": 0.98
    },
    "tin": {
      "value": "0012345678",
      "confidence": 0.95
    },
    "address": {
      "value": "Ethio-China St, Addis Ababa, Ethiopia",
      "confidence": 0.9
    },
    "phone": {
      "value": "+251 11 123 4567",
      "confidence": 0.92
    }
  },
  "transaction": {
    "date": {
      "value": "02/08/2025",
      "confidence": 0.99
    },
    "invoice_number": {
      "value": "00082031",
      "confidence": 0.95
    },
    "customer_name": {
      "value": "HAREGEWOYINE BITEW TEFERA",
      "confidence": 0.98
    },
    "cashier_name": {
      "value": "Mulugeta A.",
      "confidence": 0.85
    }
  },
  "items": [
    {
      "description": "Order lens Progressive Power / (N)",
      "quantity": 2.0,
      "unit_price": 2500.0,
      "line_total": 5000.0,
      "tax_amount": 0.0,
      "confidence": 0.95,
      "metadata": {
        "tax_status": "(N)"
      }
    },
    {
      "description": "Frame P82228 (N)",
      "quantity": 1.0,
      "unit_price": 3000.0,
      "line_total": 3000.0,
      "tax_amount": 0.0,
      "confidence": 0.95,
      "metadata": {
        "tax_status": "(N)"
      }
    }
  ],
  "totals": {
    "subtotal": {
      "value": 8000.0,
      "confidence": 0.95
    },
    "tax_total": {
      "value": 0.0,
      "confidence": 0.9
    },
    "grand_total": {
      "value": 8000.0,
      "confidence": 1.0
    }
  },
  "warnings": [
    "Tax amount marked as NOTXBL (not taxable)."
  ]
}
```
