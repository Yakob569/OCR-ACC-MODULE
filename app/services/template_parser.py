from __future__ import annotations

import re

from app.schemas.response import FieldValue, Item


class TemplateParser:
    receipt_type = "retail_receipt"

    def parse(self, text: str) -> tuple[dict[str, FieldValue], list[Item], list[str]]:
        raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
        upper_lines = [line.upper() for line in raw_lines]
        flattened_text = " ".join(raw_lines)
        warnings: list[str] = []

        fields: dict[str, FieldValue] = {
            "merchant_name": FieldValue(
                value=self._extract_merchant_name(upper_lines),
                confidence=0.70 if text.strip() else 0.0,
            ),
            "receipt_number": FieldValue(
                value=self._extract_receipt_number(raw_lines),
                confidence=0.75 if "FS" in text.upper() else 0.0,
            ),
            "invoice_number": FieldValue(
                value=self._extract_invoice_number(flattened_text),
                confidence=0.65 if "INVOICE" in text.upper() else 0.0,
            ),
            "customer_name": FieldValue(
                value=self._extract_customer_name(flattened_text),
                confidence=0.60 if "CUSTOMER" in text.upper() else 0.0,
            ),
            "date": FieldValue(
                value=self._extract_group(flattened_text, r"(\d{2}[\/\-]\d{2}[\/\-]\d{4})"),
                confidence=0.70 if re.search(r"\d{2}[\/\-]\d{2}[\/\-]\d{4}", text) else 0.0,
            ),
            "time": FieldValue(
                value=self._extract_time(raw_lines),
                confidence=0.70 if re.search(r"\b\d{2}:\d{2}\b", text) else 0.0,
            ),
            "total_amount": FieldValue(
                value=self._extract_amount_near_total(raw_lines),
                confidence=0.85 if any("TOTAL" in line for line in upper_lines) else 0.0,
            ),
        }

        if not text.strip():
            warnings.append("No OCR text was available for template parsing.")

        return fields, self._extract_items(raw_lines), warnings

    def _extract_merchant_name(self, lines: list[str]) -> str | None:
        # Skip lines that look like TIN, address, or metadata
        skip_patterns = [
            r"TIN[:\-\s]*\d+",
            r"FS\s*NO",
            r"TEL[:\-\s]*\d+",
            r"ADDIS",
            r"MALL",
            r"STREET",
            r"CASH\s*INVOICE",
            r"===",
            r"\d{2}/\d{2}/\d{4}",
        ]
        
        for line in lines[:5]:  # Look at the first 5 lines
            if any(re.search(p, line, re.IGNORECASE) for p in skip_patterns):
                continue
            if len(line) > 3:
                # Clean up name if it has extra symbols
                return line.strip(" =-").strip()
        return lines[0] if lines else None

    def _extract_group(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None
        return match.group(1).strip()

    def _extract_amount_near_total(self, lines: list[str]) -> float | None:
        upper_lines = [line.upper() for line in lines]
        for index, line in enumerate(upper_lines):
            if "TOTAL" not in line:
                continue
            
            # 1. Try to find amount on the same line
            line_cleaned = line.replace("*", "").replace("TOTAL", "").strip()
            # Match decimal numbers like 2,056.02
            amounts = re.findall(r"(\d[0-9,\.]*\.\d{2})\b", line_cleaned)
            if amounts:
                return self._parse_amount(amounts[-1])

            # 2. Look at subsequent lines
            for offset in range(1, 4):
                if index + offset >= len(lines):
                    break
                next_line = lines[index + offset].replace("*", "").strip()
                match = re.search(r"(\d[0-9,\.]*\.\d{2})\b", next_line)
                if match:
                    val = self._parse_amount(match.group(1))
                    if val and val < 1000000:
                        return val
        return None

    def _extract_items(self, lines: list[str]) -> list[Item]:
        items: list[Item] = []
        
        # Pattern for: qty unit_price *total (e.g. 2 807.830 *1615.66)
        retail_pattern = re.compile(
            r"(?P<qty>\d+)\s+(?P<unit>\d[\d,\.]*)\s+\*(?P<total>\d[\d,\.]*)",
            re.MULTILINE
        )

        for i, line in enumerate(lines):
            match = retail_pattern.search(line)
            if match:
                qty = self._parse_number(match.group("qty"))
                unit_price = self._parse_amount(match.group("unit"))
                line_total = self._parse_amount(match.group("total"))
                
                # Description is usually on the line ABOVE
                description = "Unknown item"
                if i > 0:
                    description = lines[i-1].strip(" =-")
                
                items.append(Item(
                    description=description,
                    quantity=qty or 1.0,
                    unit_price=unit_price or 0.0,
                    line_total=line_total or 0.0,
                    confidence=0.75
                ))
        
        return items

    def _parse_number(self, value: str) -> float | None:
        normalized = value.replace(",", ".")
        try:
            return float(normalized)
        except ValueError:
            return None

    def _parse_amount(self, value: str) -> float | None:
        cleaned = re.sub(r"[^0-9,\.]", "", value)
        if not cleaned:
            return None

        separators = [index for index, char in enumerate(cleaned) if char in ",."]
        if not separators:
            try:
                return float(cleaned)
            except ValueError:
                return None

        decimal_index = separators[-1]
        integer_part = re.sub(r"[^0-9]", "", cleaned[:decimal_index]) or "0"
        fractional_part = re.sub(r"[^0-9]", "", cleaned[decimal_index + 1 :])

        if len(fractional_part) == 2:
            normalized = f"{integer_part}.{fractional_part}"
        elif len(fractional_part) == 3 and len(integer_part) >= 1:
            # Likely 807.830 -> 807.83
            normalized = f"{integer_part}.{fractional_part[:2]}"
        else:
            normalized = f"{integer_part}.{fractional_part[:2]}" if fractional_part else integer_part

        try:
            return float(normalized)
        except ValueError:
            return None

    def _extract_receipt_number(self, lines: list[str]) -> str | None:
        for line in lines:
            upper_line = line.upper()
            if "FS" not in upper_line:
                continue
            digit_groups = re.findall(r"(\d{4,})", line)
            if digit_groups:
                return digit_groups[-1].lstrip("0") or digit_groups[-1]
        return None

    def _extract_invoice_number(self, text: str) -> str | None:
        explicit = self._extract_group(
            text,
            r"INVOICE\.?\s*NO\.?\s*[:\-]?\s*([A-Z0-9\-\/]+)",
        )
        if explicit is not None:
            return explicit

        fallback = re.search(r"\b([A-Z]{2,4}\-[A-Z]{2,8}\-\d{4}\-\d{3,6})\b", text, flags=re.IGNORECASE)
        if fallback:
            return fallback.group(1).upper()
        return None

    def _extract_customer_name(self, text: str) -> str | None:
        match = re.search(
            r"CUSTOMER[^A-Z0-9]{0,6}NAM[A-Z]*\s*[:\-]?\s*([A-Z !\?]+?)(?:CASHIER|SALES|ITEM|TOTAL|$)",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            cleaned = re.sub(r"[^A-Z ]", " ", match.group(1).upper())
            cleaned = " ".join(cleaned.split())
            return cleaned or None
        return None

    def _extract_time(self, lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if re.search(r"\d{2}[\/\-]\d{2}[\/\-]\d{4}", line):
                candidate_block = " ".join(lines[index : index + 3])
                match = re.search(r"\b(\d{2}:\d{2})\b", candidate_block)
                if match:
                    return match.group(1)
        return None
