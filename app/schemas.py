from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ExtractedEvidence(BaseModel):
    order_ids: List[str] = []
    dates: List[str] = []
    amounts: List[float] = []
    currencies: List[str] = []
    product_names: List[str] = []
    error_codes: List[str] = []
    raw_text: str = ""
    confidence: float = 0.0
    quality_ok: bool = True
    quality_reason: Optional[str] = None

class VerificationResult(BaseModel):
    status: str          # match | conflict | insufficient_evidence
    matched_fields: Dict[str, Any] = {}
    conflicts: List[str] = []
    missing: List[str] = []
    notes: List[str] = []

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    status: str          # answered | needs_clarification | rejected | queued
    job_id: Optional[str] = None
    verification: Optional[VerificationResult] = None