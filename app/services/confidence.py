from __future__ import annotations

from app.schemas.response import FieldValue, Item


class ConfidenceScorer:
    def normalize(
        self,
        fields: dict[str, FieldValue],
        items: list[Item],
        warnings: list[str],
    ) -> tuple[dict[str, FieldValue], list[Item], list[str]]:
        if not any(field.value is not None for field in fields.values()):
            warnings.append("No structured fields were confidently extracted.")

        normalized_items: list[Item] = []
        for item in items:
            confidence = item.confidence
            if not item.description or item.description == "Unknown item":
                confidence = min(confidence, 0.35)
            normalized_items.append(item.model_copy(update={"confidence": confidence}))

        return fields, normalized_items, warnings

