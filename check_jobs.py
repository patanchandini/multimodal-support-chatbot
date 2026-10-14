from app.db import SessionLocal
from app.models import Job

db = SessionLocal()
rows = db.query(Job).order_by(Job.created_at.desc()).limit(5).all()
print(f"total jobs: {len(rows)}")
for r in rows:
    print(f"  id={r.id}  session={r.session_id}  status={r.status}  updated={r.updated_at}")