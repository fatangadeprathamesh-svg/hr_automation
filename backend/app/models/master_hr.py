import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Date,
    DateTime,
    Text,
    Boolean,
    JSON,
    Index,
    func,
)
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class MasterUpload(Base):
    __tablename__ = "master_uploads"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    uploaded_by = Column(String(64), nullable=False, default="unknown")
    uploaded_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    status = Column(String(32), nullable=False, default="queued")  # queued, processing, done, failed
    total_rows = Column(Integer, nullable=False, default=0)
    accepted_rows = Column(Integer, nullable=False, default=0)
    rejected_rows = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Float, nullable=False, default=0.0)
    error_message = Column(Text, nullable=True)
    duplicate_warning = Column(Boolean, nullable=False, default=False)
    rejected_details = Column(JSON, nullable=True, default=list)


class MasterHRRecord(Base):
    __tablename__ = "master_hr_records"

    record_id = Column(String(128), primary_key=True)
    upload_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 55 Core Master CSV Columns
    record_type = Column(String(64), nullable=False, index=True)
    source_file = Column(String(255), nullable=True)
    employee_id = Column(String(64), nullable=True, index=True)
    applicant_id = Column(String(64), nullable=True)
    employee_name = Column(String(255), nullable=True, index=True)
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)
    department = Column(String(128), nullable=True, index=True)
    position = Column(String(128), nullable=True)
    division = Column(String(128), nullable=True)
    business_unit = Column(String(128), nullable=True)
    branch_location = Column(String(128), nullable=True)
    manager = Column(String(255), nullable=True)
    employment_type = Column(String(64), nullable=True)
    gender = Column(String(32), nullable=True)
    age = Column(Integer, nullable=True)
    dob = Column(Date, nullable=True)
    marital_status = Column(String(32), nullable=True)
    state = Column(String(64), nullable=True)
    education = Column(String(128), nullable=True)
    hire_date = Column(Date, nullable=True)
    exit_date = Column(Date, nullable=True)
    employee_status = Column(String(64), nullable=True)
    performance_score = Column(String(64), nullable=True)
    performance_rating = Column(String(64), nullable=True)
    monthly_income = Column(Float, nullable=True)
    years_experience = Column(Float, nullable=True)
    salary_hike_pct = Column(Float, nullable=True)
    event_date = Column(Date, nullable=True, index=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    applied_date = Column(Date, nullable=True)
    status = Column(String(64), nullable=True, index=True)
    category = Column(String(128), nullable=True)
    reason = Column(Text, nullable=True)
    days = Column(Float, nullable=True)
    clock_in = Column(String(64), nullable=True)
    clock_out = Column(String(64), nullable=True)
    hours_total = Column(Float, nullable=True)
    hours_scheduled = Column(Float, nullable=True)
    break_minutes = Column(Float, nullable=True)
    leave_entitlement = Column(Float, nullable=True)
    leave_taken_so_far = Column(Float, nullable=True)
    leave_remaining = Column(Float, nullable=True)
    engagement_score = Column(Float, nullable=True)
    satisfaction_score = Column(Float, nullable=True)
    work_life_balance_score = Column(Float, nullable=True)
    training_program = Column(String(255), nullable=True)
    training_outcome = Column(String(128), nullable=True)
    trainer = Column(String(255), nullable=True)
    training_location = Column(String(255), nullable=True)
    training_cost = Column(Float, nullable=True)
    desired_salary = Column(Float, nullable=True)
    country = Column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_master_hr_rec_type_dept", "record_type", "department"),
        Index("ix_master_hr_emp_event", "employee_id", "event_date"),
    )
