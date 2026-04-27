from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class FieldValue(BaseModel):
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)


class MerchantDetails(BaseModel):
    name: FieldValue
    tin: Optional[FieldValue] = None
    address: Optional[FieldValue] = None
    phone: Optional[FieldValue] = None


class TransactionDetails(BaseModel):
    date: FieldValue
    invoice_number: Optional[FieldValue] = None
    customer_name: Optional[FieldValue] = None
    cashier_name: Optional[FieldValue] = None


class Item(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    line_total: Optional[float] = None
    tax_amount: Optional[float] = None
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Totals(BaseModel):
    subtotal: Optional[FieldValue] = None
    tax_total: Optional[FieldValue] = None
    grand_total: FieldValue


class OCRResponse(BaseModel):
    success: bool
    filename: str
    receipt_type: str
    merchant: MerchantDetails
    transaction: TransactionDetails
    items: List[Item]
    totals: Totals
    warnings: List[str]
    raw_text: Optional[str] = None
