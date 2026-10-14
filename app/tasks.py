from app.ocr import _tess  
import json
from celery import Celery
from app.config import settings
from app.ocr.extractor import extract
from app.chat.handler import decide

celery_app = Celery(
    "chatbot", broker=settings.redis_url, backend=settings.redis_url
)
celery_app.conf.update(
    task_time_limit=120,
    task_soft_time_limit=110,
    worker_prefetch_multiplier=1,
)

@celery_app.task(name="process_multimodal")
def process_multimodal(job_id: str, session_id: str, message: str,
                       file_path: str, mime: str):
    with open(file_path, "rb") as f:
        data = f.read()
    evidence = extract(data, mime)
    reply, verification, status = decide(message, evidence)
    return {
        "job_id": job_id,
        "session_id": session_id,
        "status": status,
        "reply": reply,
        "verification": verification.model_dump(),
    }