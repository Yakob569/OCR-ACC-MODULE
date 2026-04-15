from __future__ import annotations

import re

from app.schemas.response import FieldValue, Item


class TemplateParser:
    receipt_type = "medical_services_receipt"

    def parse(self, text: str) -> tuple[dict[str, FieldValue], list[Item], list[str]]:
        raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
        upper_lines = [line.upper() for line in raw_lines]
        flattened_text = " ".join(raw_lines)
        warnings: list[str] = []

        fields: dict[str, FieldValue] = {
            "merchant_name": FieldValue(
                value=self._first_matching_line(upper_lines, ("MEDICAL SERVICES", "PLC")),
                confidence=0.55 if text.strip() else 0.0,
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
        upper_lines = [line.upper() for line in lines]
        for index, line in enumerate(upper_lines):
            if "TOTAL" not in line:
                continue
            candidate_block = " ".join(lines[index : index + 8])
            amounts = re.findall(r"([0-9][0-9,\.]*[0-9])", candidate_block.replace("*", ""))
            for raw_amount in reversed(amounts):
                parsed = self._parse_amount(raw_amount)
                if parsed is not None:
                    return parsed
        return None

    def _extract_items(self, lines: list[str]) -> list[Item]:
        items: list[Item] = []
        item_pattern = re.compile(
            r"(?P<qty>\d[\d,\.]*)\s*x\s*(?P<unit>\d[\d,\.]*)",
            re.IGNORECASE,
        )

        for line in lines:
            match = item_pattern.search(line)
            if not match:
                continue

            qty = self._parse_number(match.group("qty"))
            unit_price = self._parse_amount(match.group("unit"))
            if qty is None or unit_price is None:
                continue

            description = line[match.end() :].strip(" =-") or "Unknown item"
            trailing_amounts = re.findall(r"([0-9][0-9,\.]*[0-9])", line[match.end() :])
            line_total = None
            if trailing_amounts:
                line_total = self._parse_amount(trailing_amounts[-1])
            if line_total is None:
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

        if len(fractional_part) == 0:
            normalized = integer_part
        elif len(fractional_part) == 2:
            normalized = f"{integer_part}.{fractional_part}"
        elif len(fractional_part) == 3 and len(integer_part) >= 1:
            normalized = f"{integer_part}{fractional_part}"
        else:
            normalized = f"{integer_part}.{fractional_part[:2]}"

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
