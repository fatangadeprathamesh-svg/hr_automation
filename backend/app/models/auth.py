from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import generate_uuid


class UserAuth(Base):
    """
    User credential and identity linkage for password, OTP, and Google SSO.
    """
    __tablename__ = "user_auth"

    employee_id = Column(String(64), ForeignKey("employees.employee_id"), primary_key=True)
    organization_id = Column(String(64), nullable=False, default="ORG_DEMO_01", index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(32), nullable=False, default="employee")  # employee, manager, hr_admin
    google_sub = Column(String(255), nullable=True, unique=True, index=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    employee = relationship("Employee", backref="auth_profile")


class OTPVerification(Base):
    """
    Time-limited, attempt-capped email verification and OTP store.
    10-minute expiry, max 5 attempts, 60-second resend cooldown.
    """
    __tablename__ = "otp_verifications"

    verification_id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), nullable=False, index=True)
    code_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    resend_available_at = Column(DateTime(timezone=True), nullable=False)
    is_consumed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
