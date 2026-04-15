from app.services.template_parser import TemplateParser


def test_template_parser_extracts_known_fields() -> None:
    parser = TemplateParser()
    sample_text = """
    BFLC MEDICAL SERVICES PLC
    ADDIS ABABA
    FS No.00002031
    02/08/2025 13:02
    Invoice No.: ACC-SINU-2025-50428
    Customer Name : HAREGEWOINE BITEW TEFERA
    TOTAL: *8,000.00
    """

    fields, items, warnings = parser.parse(sample_text)

    assert fields["merchant_name"].value == "BFLC MEDICAL SERVICES PLC"
    assert fields["receipt_number"].value == "2031"
    assert fields["invoice_number"].value == "ACC-SINU-2025-50428"
    assert fields["date"].value == "02/08/2025"
    assert fields["time"].value == "13:02"
    assert fields["total_amount"].value == 8000.00
    assert items == []
    assert warnings == []

