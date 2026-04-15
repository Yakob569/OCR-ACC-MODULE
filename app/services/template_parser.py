from __future__ import annotations

import re

from app.schemas.response import FieldValue, Item


class TemplateParser:
    receipt_type = "medical_services_receipt"

    def parse(self, text: str) -> tuple[dict[str, FieldValue], list[Item], list[str]]:
        raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
        upper_lines = [line.upper() for line in raw_lines]
        warnings: list[str] = []

        fields: dict[str, FieldValue] = {
            "merchant_name": FieldValue(
                value=self._first_matching_line(upper_lines, ("MEDICAL SERVICES", "PLC")),
                confidence=0.55 if text.strip() else 0.0,
            ),
            "receipt_number": FieldValue(
                value=self._extract_group(text, r"FS\s*NO\.?\s*0*([0-9]+)"),
                confidence=0.75 if "FS" in text.upper() else 0.0,
            ),
            "invoice_number": FieldValue(
                value=self._extract_group(text, r"INVOICE\s+NO\.?\s*[:\-]?\s*([A-Z0-9\-\/]+)"),
                confidence=0.65 if "INVOICE" in text.upper() else 0.0,
            ),
            "customer_name": FieldValue(
                value=self._extract_group(text, r"CUSTOMER\s+NAME\s*[:\-]?\s*([A-Z .]+)"),
                confidence=0.60 if "CUSTOMER" in text.upper() else 0.0,
            ),
            "date": FieldValue(
                value=self._extract_group(text, r"(\d{2}/\d{2}/\d{4})"),
                confidence=0.70 if re.search(r"\d{2}/\d{2}/\d{4}", text) else 0.0,
            ),
            "time": FieldValue(
                value=self._extract_group(text, r"\b(\d{2}:\d{2})\b"),
                confidence=0.70 if re.search(r"\b\d{2}:\d{2}\b", text) else 0.0,
            ),
            "total_amount": FieldValue(
                value=self._extract_amount_near_total(upper_lines),
                confidence=0.80 if any("TOTAL" in line for line in upper_lines) else 0.0,
            ),
        }

        if not text.strip():
            warnings.append("No OCR text was available for template parsing.")

        return fields, self._extract_items(raw_lines), warnings

    def _first_matching_line(self, lines: list[str], required_tokens: tuple[str, ...]) -> str | None:
        for line in lines:
            if all(token in line for token in required_tokens):
                return line
        return lines[0] if lines else None

    def _extract_group(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None
        return match.group(1).strip()

    def _extract_amount_near_total(self, lines: list[str]) -> float | None:
        for line in lines:
            if "TOTAL" not in line:
                continue
            amount_match = re.search(r"([0-9][0-9,]*\.\d{2})", line.replace("*", ""))
            if amount_match:
                return float(amount_match.group(1).replace(",", ""))
        return None

    def _extract_items(self, lines: list[str]) -> list[Item]:
        items: list[Item] = []
        item_pattern = re.compile(r"(?P<qty>\d+(?:\.\d+)?)\s*x\s*(?P<unit>\d[\d,]*\.\d{2})", re.IGNORECASE)

        for line in lines:
            match = item_pattern.search(line)
            if not match:
                continue

            qty = float(match.group("qty"))
            unit_price = float(match.group("unit").replace(",", ""))
            description = line[match.end() :].strip(" =-") or "Unknown item"
            line_total = qty * unit_price
            items.append(
                Item(
                    description=description,
                    quantity=qty,
                    unit_price=unit_price,
                    line_total=line_total,
                    confidence=0.55,
                )
            )

        return items

