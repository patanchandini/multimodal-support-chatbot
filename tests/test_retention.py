import os
from datetime import datetime, timedelta

from app.db import SessionLocal, engine
from app.models import UploadedFile, Base
from app.storage import save_bytes
from app.cleanup import sweep_expired


Base.metadata.create_all(engine)


def _create_tracked_file(db, data: bytes, session: str, name: str,
                         retention_seconds: int = 3600):
    """
    Mirrors what app/main.py does: writes the file AND inserts the DB row.
    Returns (info_dict, row).
    """
    info = save_bytes(data, session, name)

    row = UploadedFile(
        id=info["id"],
        session_id=session,
        path=info["path"],
        mime="text/plain",
        size=len(data),
        sha256="0" * 64,
        expires_at=datetime.utcnow() + timedelta(seconds=retention_seconds),
    )
    db.add(row)
    db.commit()
    return info, row


def test_save_writes_file_to_disk():
    """save_bytes alone writes to disk (does not touch DB)."""
    info = save_bytes(b"data", "test-disk", "disk.txt")
    assert os.path.exists(info["path"])
    os.remove(info["path"])


def test_tracked_file_row_is_queryable():
    """When main.py-style insert runs, the row is retrievable."""
    db = SessionLocal()
    info, _ = _create_tracked_file(db, b"payload", "test-row", "row.txt")
    fetched = db.query(UploadedFile).filter(UploadedFile.id == info["id"]).first()
    assert fetched is not None
    assert fetched.deleted is False
    db.close()


def test_sweep_deletes_expired_rows():
    db = SessionLocal()
    info, _ = _create_tracked_file(
        db, b"expired", "test-sweep", "old.txt", retention_seconds=-10
    )
    deleted = sweep_expired(db)
    assert deleted >= 1

    refreshed = db.query(UploadedFile).filter(UploadedFile.id == info["id"]).first()
    assert refreshed.deleted is True
    assert not os.path.exists(info["path"])
    db.close()


def test_sweep_skips_non_expired_rows():
    db = SessionLocal()
    info, _ = _create_tracked_file(
        db, b"fresh", "test-sweep-2", "fresh.txt", retention_seconds=3600
    )
    sweep_expired(db)
    refreshed = db.query(UploadedFile).filter(UploadedFile.id == info["id"]).first()
    assert refreshed.deleted is False
    db.close()