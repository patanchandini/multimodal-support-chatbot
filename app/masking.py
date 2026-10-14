import re
PATTERNS = [
    # CVV — check first, before other patterns consume the digits
    (re.compile(r"\bCVV\s*[:=]?\s*\d{3,4}\b", re.I), "CVV [CVV_REDACTED]"),

    # Credit cards
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "[CARD_REDACTED]"),
    # IBAN
    (re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"), "[IBAN_REDACTED]"),
    # Emails
    (re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b"), "[EMAIL_REDACTED]"),
    # Phones (loose)
    (re.compile(r"\b(?:\+?\d[\d\s\-]{8,}\d)\b"), "[PHONE_REDACTED]"),
    # National IDs (generic 9-12 digits)
    (re.compile(r"\b\d{9,12}\b"), "[ID_REDACTED]"),
]

def mask(text: str) -> str:
    if not text:
        return ""
    out = text
    for pat, repl in PATTERNS:
        out = pat.sub(repl, out)
    return out

def mask_dict(d: dict) -> dict:
    def _m(v):
        if isinstance(v, str):
            return mask(v)
        if isinstance(v, dict):
            return {k: _m(val) for k, val in v.items()}
        if isinstance(v, list):
            return [_m(x) for x in v]
        return v
    return _m(d)