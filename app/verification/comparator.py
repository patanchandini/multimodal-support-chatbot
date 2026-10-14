import re
from app.ocr.parsers import ORDER_ID_RE, DATE_RE, AMOUNT_RE, ERROR_RE
from app.schemas import VerificationResult

def _parse_message(msg: str) -> dict:
    return {
        "order_ids": [m.group(1).upper() for m in ORDER_ID_RE.finditer(msg)],
        "dates":     [m.group(1) for m in DATE_RE.finditer(msg)],
        "amounts":   [float(m.group(2).replace(",", "").replace(" ", ""))
                      for m in AMOUNT_RE.finditer(msg)
                      if m.group(2) and ("." in m.group(2) or m.group(1))],
        "error_codes": [m.group(1).upper() for m in ERROR_RE.finditer(msg)],
        "products":  [],
    }

def _fuzzy_product(msg: str, products: list) -> bool:
    low = msg.lower()
    return any(p.lower() in low or low in p.lower() for p in products)

def compare(message: str, evidence: dict) -> VerificationResult:
    msg = _parse_message(message)
    matched, conflicts, missing, notes = {}, [], [], []

    # Order IDs
    if msg["order_ids"] and evidence["order_ids"]:
        inter = set(msg["order_ids"]) & set(evidence["order_ids"])
        if inter:
            matched["order_ids"] = sorted(inter)
        else:
            conflicts.append(
                f"Order ID mismatch: message={msg['order_ids']} "
                f"file={evidence['order_ids']}")
    elif evidence["order_ids"] and not msg["order_ids"]:
        notes.append(f"Order ID found only in file: {evidence['order_ids']}")
    elif msg["order_ids"] and not evidence["order_ids"]:
        missing.append("order_id_in_file")

    # Dates
    if msg["dates"] and evidence["dates"]:
        inter = set(msg["dates"]) & set(evidence["dates"])
        if inter:
            matched["dates"] = sorted(inter)
        else:
            conflicts.append(
                f"Date mismatch: message={msg['dates']} file={evidence['dates']}")
    elif msg["dates"] and not evidence["dates"]:
        missing.append("date_in_file")

    # Amounts — allow ±0.01 tolerance
    if msg["amounts"] and evidence["amounts"]:
        found = any(
            any(abs(a - b) < 0.01 for b in evidence["amounts"])
            for a in msg["amounts"]
        )
        if found:
            matched["amounts"] = evidence["amounts"]
        else:
            conflicts.append(
                f"Amount mismatch: message={msg['amounts']} "
                f"file={evidence['amounts']}")
    elif msg["amounts"] and not evidence["amounts"]:
        missing.append("amount_in_file")

    # Error codes (only check if mentioned)
    if msg["error_codes"] and evidence["error_codes"]:
        inter = set(msg["error_codes"]) & set(evidence["error_codes"])
        if inter:
            matched["error_codes"] = sorted(inter)
        else:
            conflicts.append(
                f"Error code mismatch: message={msg['error_codes']} "
                f"file={evidence['error_codes']}")

    # Products (fuzzy)
    if evidence["product_names"]:
        if _fuzzy_product(message, evidence["product_names"]):
            matched["product_names"] = evidence["product_names"]
        else:
            notes.append(
                f"Product names in file not referenced in message: "
                f"{evidence['product_names']}")

    if conflicts:
        status = "conflict"
    elif not matched and not evidence["order_ids"] \
         and not evidence["amounts"] and not evidence["dates"]:
        status = "insufficient_evidence"
    else:
        status = "match"

    return VerificationResult(
        status=status, matched_fields=matched,
        conflicts=conflicts, missing=missing, notes=notes
    )