import re

# Order ID — also matches OCR-mangled variants (0RD instead of ORD)
ORDER_ID_RE = re.compile(
    r"\b((?:[O0]RD(?:ER)?|#)\s*[-:]?\s*[A-Z0-9]{5,20})\b",
    re.I,
)
# Date — ISO, US slash, or "Mon DD, YYYY"
DATE_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"[a-z]*\s+\d{1,2},?\s+\d{2,4})\b",
    re.I,
)

# Amount — optional currency + number (with or without decimals)
AMOUNT_RE = re.compile(
    r"(?:(USD|EUR|GBP|INR|\$|€|£|₹)\s*)?"
    r"(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?|\d+\.\d{2})"
)

CURRENCY_MAP = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}

# Error codes
ERROR_RE = re.compile(r"\b(?:ERR|ERROR|CODE)[-: ]?([A-Z0-9\-]{3,12})\b", re.I)

# Product names
PRODUCT_HINTS = re.compile(
    r"(?:product|item|description|sku)[:\s]+([A-Za-z0-9 ,\-\.]{3,60})", re.I
)


def parse_fields(text: str) -> dict:
    order_ids = list({m.group(1).upper() for m in ORDER_ID_RE.finditer(text)})
    dates = list({m.group(1) for m in DATE_RE.finditer(text)})
    error_codes = list({m.group(1).upper() for m in ERROR_RE.finditer(text)})

    amounts, currencies = [], []
    for m in AMOUNT_RE.finditer(text):
        raw = m.group(2)
        if not raw:
            continue
        try:
            val = float(raw.replace(",", "").replace(" ", ""))
        except ValueError:
            continue
        cur = m.group(1)
        if cur:
            cur = CURRENCY_MAP.get(cur, cur.upper())
        if cur or "." in raw:
            amounts.append(val)
            if cur:
                currencies.append(cur)

    products = [m.group(1).strip() for m in PRODUCT_HINTS.finditer(text)]

    return {
        "order_ids": order_ids,
        "dates": dates,
        "amounts": amounts,
        "currencies": list(set(currencies)),
        "product_names": products,
        "error_codes": error_codes,
    }