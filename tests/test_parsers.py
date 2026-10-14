from app.ocr.parsers import parse_fields


def test_extracts_order_id():
    fields = parse_fields("Order ID: ORD-12345")
    assert "ORD-12345" in fields["order_ids"]


def test_extracts_amount_with_currency():
    fields = parse_fields("Amount: USD 149.99")
    assert 149.99 in fields["amounts"]
    assert "USD" in fields["currencies"]


def test_extracts_iso_date():
    fields = parse_fields("Date: 2026-10-04")
    assert "2026-10-04" in fields["dates"]


def test_extracts_us_date():
    fields = parse_fields("Date: 10/04/2026")
    assert any("2026" in d for d in fields["dates"])


def test_extracts_error_code():
    fields = parse_fields("Error: ERR-5001")
    assert "5001" in fields["error_codes"] or "ERR-5001" in fields["error_codes"]


def test_extracts_product_name():
    fields = parse_fields("Product: Wireless Keyboard")
    assert any("Wireless" in p for p in fields["product_names"])


def test_empty_text_returns_empty_fields():
    fields = parse_fields("")
    for key in fields:
        assert fields[key] == []


def test_no_false_positives_on_plain_text():
    fields = parse_fields("Thank you for your business.")
    assert fields["order_ids"] == []
    assert fields["amounts"] == []
