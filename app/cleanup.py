import os
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import UploadedFile

def sweep_expired(db: Session) -> int:
    now = datetime.utcnow()
    rows = db.query(UploadedFile).filter(
        UploadedFile.deleted == False,
        UploadedFile.expires_at <= now
    ).all()
    n = 0
    for r in rows:
        try:
            if r.path and os.path.exists(r.path):
                os.remove(r.path)
        except OSError:
            pass
        r.deleted = True
        n += 1
    db.commit()
    return n