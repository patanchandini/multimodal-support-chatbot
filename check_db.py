from datetime import datetime
from app.db import SessionLocal
from app.models import UploadedFile

db = SessionLocal()
now = datetime.utcnow()
print(f"now (UTC): {now}")
print()

rows = db.query(UploadedFile).order_by(UploadedFile.created_at.desc()).all()
print(f"total rows: {len(rows)}")
for r in rows:
    expires = r.expires_at
    delta = (expires - now).total_seconds() if expires else None
    print(f"  id={r.id[:8]}  deleted={r.deleted}  created={r.created_at}  expires={expires}  in {delta:.0f}s")