from app.ocr import _tess  # noqa: F401

import pytesseract
import io
from PIL import Image, ImageOps, ImageFilter
import pdfplumber
from app.config import settings
from app.ocr.parsers import parse_fields
from app.ocr.quality import image_quality_report
from app.security import detect_injection, injection_reasons
def _preprocess(img: Image.Image) -> Image.Image:
    # 1. Convert to grayscale
    img = img.convert("L")
    # 2. Upscale if too small (Tesseract likes ~300 DPI)
    w, h = img.size
    target_w = 2000
    if w < target_w:
        scale = target_w / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    # 3. Autocontrast to normalize lighting
    img = ImageOps.autocontrast(img)
    # 4. Binarize (helps a lot with anti-aliased synthetic text)
    img = img.point(lambda p: 255 if p > 160 else 0)
    return img

def _ocr_image(img: Image.Image) -> tuple[str, float]:
    data = pytesseract.image_to_data(
        img,
        output_type=pytesseract.Output.DICT,
        config=(
            "--oem 3 --psm 6 "
            "-c tessedit_char_whitelist="
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz"
            "0123456789"
            "-:.,$# "
            "-c preserve_interword_spaces=1"
        ),
    )
    texts, confs = [], []
    for t, c in zip(data["text"], data["conf"]):
        if t and t.strip():
            texts.append(t)
            try:
                confs.append(float(c))
            except ValueError:
                pass
    text = " ".join(texts)
    avg_conf = sum(confs) / len(confs) if confs else 0.0
    return text, avg_conf

    
def extract_from_image(data: bytes) -> dict:
    img = Image.open(io.BytesIO(data))
    quality = image_quality_report(img)

    if not quality["ok"]:
        return {
            "raw_text": "", "confidence": 0.0,
            "quality_ok": False, "quality_reason": quality["reason"],
            "injection": False, "injection_reasons": [],
            **{k: [] for k in
               ("order_ids","dates","amounts","currencies",
                "product_names","error_codes")}
        }

    proc = _preprocess(img)
    text, conf = _ocr_image(proc)
    fields = parse_fields(text)

    inj = detect_injection(text)
    return {
        **fields,
        "raw_text": text,
        "confidence": conf,
        "quality_ok": conf >= settings.ocr_min_confidence,
        "quality_reason": None if conf >= settings.ocr_min_confidence
                          else "low_ocr_confidence",
        "injection": inj,
        "injection_reasons": injection_reasons(text),
    }

def extract_from_pdf(data: bytes) -> dict:
    text_parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages[:20]:  # cap
            t = page.extract_text() or ""
            text_parts.append(t)
    text = "\n".join(text_parts)
    fields = parse_fields(text)
    inj = detect_injection(text)
    return {
        **fields,
        "raw_text": text,
        "confidence": 100.0 if text.strip() else 0.0,
        "quality_ok": bool(text.strip()),
        "quality_reason": None if text.strip() else "no_extractable_text",
        "injection": inj,
        "injection_reasons": injection_reasons(text),
    }

def extract(data: bytes, mime: str) -> dict:
    if mime == "application/pdf":
        return extract_from_pdf(data)
    return extract_from_image(data)