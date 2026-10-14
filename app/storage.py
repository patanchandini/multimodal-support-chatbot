import os, uuid, aiofiles
from datetime import datetime, timedelta
from app.config import settings

os.makedirs(settings.upload_dir, exist_ok=True)

def save_bytes(data: bytes, session_id: str, filename: str) -> dict:
    fid = uuid.uuid4().hex
    safe_name = f"{fid}_{os.path.basename(filename)}"
    path = os.path.join(settings.upload_dir, safe_name)
    with open(path, "wb") as f:
        f.write(data)
    expires = datetime.utcnow() + timedelta(seconds=settings.retention_seconds)
    return {"id": fid, "path": path, "expires_at": expires}