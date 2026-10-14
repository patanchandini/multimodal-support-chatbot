import hashlib, os, re
from fastapi import UploadFile, HTTPException
import filetype

MAGIC_OK = {"image/png", "image/jpeg", "image/webp", "application/pdf"}

# Prompt-injection style phrases commonly seen inside image text
INJECTION_PATTERNS = [
    re.compile(r"ignore (all )?previous instructions", re.I),
    re.compile(r"disregard (the )?(system|prior) (prompt|message)", re.I),
    re.compile(r"you are now", re.I),
    re.compile(r"system\s*:\s*", re.I),
    re.compile(r"assistant\s*:\s*", re.I),
    re.compile(r"</?script", re.I),
    re.compile(r"execute (this )?(code|command)", re.I),
    re.compile(r"reveal (your )?(system )?prompt", re.I),
    re.compile(r"send (the )?(customer'?s )?(card|password|cvv)", re.I),
]

def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sniff_mime(data: bytes, filename: str) -> str:
    kind = filetype.guess(data)
    if kind:
        return kind.mime
    # Fallback: trust extension only if magic failed
    if filename.lower().endswith(".pdf"):
        return "application/pdf"
    raise HTTPException(400, "Unsupported or unrecognised file type")

def validate_upload(data: bytes, filename: str, max_mb: int) -> str:
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {max_mb} MB")
    mime = sniff_mime(data, filename)
    if mime not in MAGIC_OK:
        raise HTTPException(415, f"Disallowed mime {mime}")
    return mime

def detect_injection(text: str) -> bool:
    for pat in INJECTION_PATTERNS:
        if pat.search(text or ""):
            return True
    return False

def injection_reasons(text: str) -> list:
    return [pat.pattern for pat in INJECTION_PATTERNS if pat.search(text or "")]
