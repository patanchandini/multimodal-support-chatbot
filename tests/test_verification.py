from app.verification.comparator import compare


def test_match_when_order_ids_align():
    evidence = {"order_ids": ["ORD-12345"], "amounts": [149.99],
                "dates": ["2026-10-04"], "currencies": ["USD"],
                "product_names": [], "error_codes": [],
                "raw_text": "", "confidence": 100, "quality_ok": True,
                "quality_reason": None, "injection": False,
                "injection_reasons": []}
    result = compare("My order ORD-12345 for USD 149.99 on 2026-10-04", evidence)
    assert result.status == "match"
    assert "ORD-12345" in result.matched_fields.get("order_ids", [])


def test_conflict_when_order_ids_differ():
    evidence = {"order_ids": ["ORD-12345"], "amounts": [], "dates": [],
                "currencies": [], "product_names": [], "error_codes": [],
                "raw_text": "", "confidence": 100, "quality_ok": True,
                "quality_reason": None, "injection": False,
                "injection_reasons": []}
    result = compare("My order ORD-99999", evidence)
    assert result.status == "conflict"
    assert any("Order ID" in c for c in result.conflicts)


def test_conflict_on_amount_mismatch():
    evidence = {"order_ids": [], "amounts": [149.99], "dates": [],
                "currencies": [], "product_names": [], "error_codes": [],
                "raw_text": "", "confidence": 100, "quality_ok": True,
                "quality_reason": None, "injection": False,
                "injection_reasons": []}
    result = compare("My order was for 500.00", evidence)
    assert result.status == "conflict"


def test_insufficient_evidence_when_file_is_empty():
    evidence = {"order_ids": [], "amounts": [], "dates": [],
                "currencies": [], "product_names": [], "error_codes": [],
                "raw_text": "", "confidence": 0, "quality_ok": True,
                "quality_reason": None, "injection": False,
                "injection_reasons": []}
    result = compare("Help with my order", evidence)
    assert result.status == "insufficient_evidence"


def test_no_matched_fields_on_conflict():
    evidence = {"order_ids": ["ORD-12345"], "amounts": [], "dates": [],
                "currencies": [], "product_names": [], "error_codes": [],
                "raw_text": "", "confidence": 100, "quality_ok": True,
                "quality_reason": None, "injection": False,
                "injection_reasons": []}
    result = compare("My order ORD-99999", evidence)
    assert result.matched_fields.get("order_ids") is None