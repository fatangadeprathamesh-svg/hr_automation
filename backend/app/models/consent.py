from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, func
from app.database import Base
from app.models.base import generate_uuid


class ConsentLog(Base):
    """
    Audit log of user cookie and data processing consent decisions.
    Demonstrates compliance with India's Digital Personal Data Protection Act 2023 (DPDP Act)
    and international transparency standards.
    """
    __tablename__ = "consent_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    anonymous_id = Column(String(100), nullable=False, index=True)
    policy_version = Column(String(32), nullable=False, default="2026.1")
    necessary = Column(Boolean, nullable=False, default=True)
    preferences = Column(Boolean, nullable=False, default=False)
    analytics = Column(Boolean, nullable=False, default=False)
    user_agent = Column(String(255), nullable=True)
    ip_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
