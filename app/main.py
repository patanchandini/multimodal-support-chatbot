from app.ocr import _tess  # noqa: F401
import os, uuid, time, json, asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.models import Base, UploadedFile, Job, AuditLog
from app.schemas import ChatResponse
from app.security import validate_upload, sha256_of
from app.masking import mask, mask_dict
from app.ocr.extractor import extract
from app.chat.handler import decide
from app.cleanup import sweep_expired
from app.tasks import process_multimodal, celery_app

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)

app = FastAPI(title=settings.app_name)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def log(db: Session, session_id: str, event: str, details: dict):
    db.add(AuditLog(session_id=session_id, event=event,
                    details=mask_dict(details)))
    db.commit()

@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}

@app.post("/chat", response_model=ChatResponse)
async def chat(
    session_id: str = Form(...),
    message: str = Form(""),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    started = time.perf_counter()
    log(db, session_id, "incoming_message",
        {"message": message, "has_file": bool(file)})

    # No file → text-only path
    if file is None:
        return ChatResponse(session_id=session_id,
                            reply=("Please describe your issue or attach a "
                                   "screenshot, invoice, or product image."),
                            status="answered")

    data = await file.read()
    try:
        mime = validate_upload(data, file.filename or "", settings.max_file_size_mb)
    except HTTPException as e:
        log(db, session_id, "upload_rejected", {"reason": e.detail})
        raise

    # Save with retention
    fid = uuid.uuid4().hex
    safe_name = f"{fid}_{os.path.basename(file.filename or 'upload')}"
    path = os.path.join(settings.upload_dir, safe_name)
    os.makedirs(settings.upload_dir, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)

    record = UploadedFile(
        id=fid, session_id=session_id, path=path, mime=mime,
        size=len(data), sha256=sha256_of(data),
        expires_at=datetime.utcnow() + timedelta(seconds=settings.retention_seconds),
    )
    db.add(record); db.commit()

    # Fast path: try sync with 30s budget
    try:
        evidence = await asyncio.wait_for(
            asyncio.to_thread(extract, data, mime),
            timeout=settings.processing_timeout_seconds,
        )
    except asyncio.TimeoutError:
        # Queue for background processing
        job_id = uuid.uuid4().hex
        db.add(Job(id=job_id, session_id=session_id, status="queued",
                   payload={"message": message, "path": path, "mime": mime}))
        db.commit()
        process_multimodal.delay(job_id, session_id, message, path, mime)
        log(db, session_id, "queued", {"job_id": job_id})
        return ChatResponse(
            session_id=session_id, job_id=job_id, status="queued",
            reply=("Your file is taking longer than usual to process. "
                   "I've queued it and will reply here shortly.")
        )

    # Reject unsafe / prompt-injection content
    if evidence.get("injection"):
        log(db, session_id, "prompt_injection_rejected",
            {"reasons": evidence["injection_reasons"]})
        # Delete file immediately
        try: os.remove(path)
        except OSError: pass
        record.deleted = True; db.commit()
        return ChatResponse(
            session_id=session_id,
            status="rejected",
            reply=("I can't act on instructions that appear inside uploaded "
                   "files. Please describe your request in the chat message.")
        )

    reply, verification, status = decide(message, evidence)
    elapsed = time.perf_counter() - started

    log(db, session_id, "processed", {
        "elapsed": round(elapsed, 2),
        "status": status,
        "matched": verification.matched_fields,
        "conflicts": verification.conflicts,
    })

    return ChatResponse(
        session_id=session_id, reply=reply, status=status,
        verification=verification
    )

@app.get("/jobs/{job_id}")
def job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {
        "job_id": job.id, "status": job.status, "result": job.result,
        "updated_at": job.updated_at.isoformat(),
    }

@app.post("/admin/cleanup")
def cleanup(db: Session = Depends(get_db)):
    n = sweep_expired(db)
    return {"deleted": n}

@app.on_event("startup")
async def _startup_sweeper():
    async def loop():
        while True:
            db = SessionLocal()
            try:
                sweep_expired(db)
            finally:
                db.close()
            await asyncio.sleep(60)
    asyncio.create_task(loop())