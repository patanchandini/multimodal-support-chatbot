import cv2
import numpy as np
from PIL import Image

def image_quality_report(pil_img: Image.Image) -> dict:
    """Return {ok, reason, sharpness, width, height}."""
    gray = np.array(pil_img.convert("L"))
    h, w = gray.shape
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
    ok = True
    reason = None
    if w < 800:
        ok, reason = False, "image_too_small"
    elif sharpness < 60:
        ok, reason = False, "image_too_blurry"
    elif gray.mean() < 25:
        ok, reason = False, "image_too_dark"
    return {"ok": ok, "reason": reason, "sharpness": float(sharpness),
            "width": w, "height": h}