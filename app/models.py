from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Float, JSON, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    path = Column(String)
    mime = Column(String)
    size = Column(Integer)
    sha256 = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    deleted = Column(Boolean, default=False)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    status = Column(String, default="queued")   # queued|running|done|failed
    payload = Column(JSON)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True)
    event = Column(String)
    details = Column(JSON)            # already masked
    created_at = Column(DateTime, default=datetime.utcnow)