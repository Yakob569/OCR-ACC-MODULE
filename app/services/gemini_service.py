import os
import json
import logging
import time
import google.generativeai as genai
from app.schemas.response import OCRResponse, FieldValue, Item, MerchantDetails, TransactionDetails, Totals
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("ocr-app")

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel(settings.gemini_model)

async def extract_receipt(image_bytes: bytes, filename: str) -> OCRResponse:
    start_time = time.perf_counter()
    logger.info(f"[{filename}] Starting extraction process. Image size: {len(image_bytes)/1024:.2f} KB")
    
    prompt = """
    Act as an expert financial OCR system. Analyze the provided receipt image and extract data with high precision.
    
    Structure your extraction as follows:
    1. Merchant: Look for TIN (Tax Identification Number) first. Then Company Name, Address, and Phone.
    2. Transaction: Extract Date (DD/MM/YYYY), Invoice/Receipt Number, FS Number (look for 'FS NO' label), Customer Name, Cashier Name, and Machine ID (look for labels like 'Machine ID', 'Terminal ID', or unique codes near 'ET' at the bottom).
    3. Items: Extract a list of products/services bought. For each, get Description, Quantity, Unit Price, Line Total, and any Tax per item.
    4. Totals: Extract Subtotal, Total Tax, and Grand Total.

    Return ONLY a valid JSON object with this exact structure:
    {
      "receipt_type": "string",
      "merchant": {
        "name": {"value": "string", "confidence": float},
        "tin": {"value": "string", "confidence": float},
        "address": {"value": "string", "confidence": float},
        "phone": {"value": "string", "confidence": float}
      },
      "transaction": {
        "date": {"value": "string", "confidence": float},
        "invoice_number": {"value": "string", "confidence": float},
        "fs_number": {"value": "string", "confidence": float},
        "customer_name": {"value": "string", "confidence": float},
        "cashier_name": {"value": "string", "confidence": float},
        "machine_id": {"value": "string", "confidence": float}
      },
      "items": [
        {
          "description": "string",
          "quantity": float,
          "unit_price": float,
          "line_total": float,
          "tax_amount": float,
          "confidence": float,
          "metadata": {}
        }
      ],
      "totals": {
        "subtotal": {"value": float, "confidence": float},
        "tax_total": {"value": float, "confidence": float},
        "grand_total": {"value": float, "confidence": float}
      },
      "warnings": ["string"]
    }

    Rules:
    - Numerical values must be floats or null.
    - Confidence scores between 0.0 and 1.0.
    - If a field is not found, use null for the value.
    - If the item table has extra columns, put them in 'metadata'.
    """
    
    try:
        api_start = time.perf_counter()
        logger.info(f"[{filename}] Sending request to Gemini API ({settings.gemini_model})...")
        
        # Note: generate_content is synchronous and blocks the thread.
        response = model.generate_content([
            prompt, 
            {"mime_type": "image/jpeg", "data": image_bytes}
        ])
        
        api_duration = time.perf_counter() - api_start
        logger.info(f"[{filename}] Gemini API responded in {api_duration:.2f}s")
        
        parse_start = time.perf_counter()
        text_content = response.text.strip()
        if "```json" in text_content:
            text_content = text_content.split("```json")[1].split("```")[0].strip()
        
        data = json.loads(text_content)
        
        def to_field(d):
            if not d: return None
            return FieldValue(value=d.get("value"), confidence=d.get("confidence", 0.0))

        result = OCRResponse(
            success=True,
            filename=filename,
            receipt_type=data.get("receipt_type", "unknown"),
            merchant=MerchantDetails(
                name=to_field(data.get("merchant", {}).get("name")),
                tin=to_field(data.get("merchant", {}).get("tin")),
                address=to_field(data.get("merchant", {}).get("address")),
                phone=to_field(data.get("merchant", {}).get("phone"))
            ),
            transaction=TransactionDetails(
                date=to_field(data.get("transaction", {}).get("date")),
                invoice_number=to_field(data.get("transaction", {}).get("invoice_number")),
                fs_number=to_field(data.get("transaction", {}).get("fs_number")),
                customer_name=to_field(data.get("transaction", {}).get("customer_name")),
                cashier_name=to_field(data.get("transaction", {}).get("cashier_name")),
                machine_id=to_field(data.get("transaction", {}).get("machine_id"))
            ),
            items=[
                Item(
                    description=it.get("description", "Unknown"),
                    quantity=it.get("quantity"),
                    unit_price=it.get("unit_price"),
                    line_total=it.get("line_total"),
                    tax_amount=it.get("tax_amount"),
                    confidence=it.get("confidence", 0.0),
                    metadata=it.get("metadata", {})
                ) for it in data.get("items", [])
            ],
            totals=Totals(
                subtotal=to_field(data.get("totals", {}).get("subtotal")),
                tax_total=to_field(data.get("totals", {}).get("tax_total")),
                grand_total=to_field(data.get("totals", {}).get("grand_total"))
            ),
            warnings=data.get("warnings", [])
        )
        
        total_duration = time.perf_counter() - start_time
        logger.info(f"[{filename}] Total processing time: {total_duration:.2f}s (Parse time: {time.perf_counter() - parse_start:.4f}s)")
        return result
        
    except Exception as e:
        logger.error(f"[{filename}] Error during Gemini extraction: {str(e)}", exc_info=True)
        raise

