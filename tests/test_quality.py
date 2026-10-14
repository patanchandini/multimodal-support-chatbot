from PIL import Image, ImageDraw
from app.ocr.quality import image_quality_report


def test_blank_white_image_fails():
    """Blank images have no content — should be flagged as blurry."""
    img = Image.new("RGB", (1600, 1200), "white")
    report = image_quality_report(img)
    assert report["ok"] is False
    assert report["reason"] == "image_too_blurry"


def test_image_with_text_passes():
    """An image with real text has edges — Laplacian finds them."""
    img = Image.new("RGB", (1600, 1200), "white")
    d = ImageDraw.Draw(img)
    d.text((50, 50), "INVOICE", fill="black")
    d.text((50, 100), "Order ID: ORD-12345", fill="black")
    d.text((50, 150), "Amount: USD 149.99", fill="black")
    report = image_quality_report(img)
    assert report["ok"] is True, f"reason: {report.get('reason')}"


def test_small_image_fails():
    img = Image.new("RGB", (400, 300), "white")
    report = image_quality_report(img)
    assert report["ok"] is False
    assert report["reason"] == "image_too_small"


def test_dark_image_fails():
    img = Image.new("RGB", (1600, 1200), (5, 5, 5))
    report = image_quality_report(img)
    assert report["ok"] is False