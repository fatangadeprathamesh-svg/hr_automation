from datetime import datetime, date
from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import ProvenanceMixin, generate_uuid


class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(String(64), primary_key=True)
    organization_id = Column(String(64), nullable=False, default="ORG_DEMO_01", index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    manager_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=True)
    manager = Column(String(255), nullable=True)  # Manager name string from master profile
    timezone = Column(String(64), nullable=False, default="America/New_York")
    hire_date = Column(Date, nullable=False, default=date(2025, 1, 1))
    termination_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    manager_rel = relationship("Employee", remote_side=[employee_id], foreign_keys=[manager_id], backref="direct_reports")


class SourceImport(Base):
    __tablename__ = "source_imports"

    import_id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(64), nullable=False, default="ORG_DEMO_01", index=True)
    source_system = Column(String(64), nullable=False, index=True)
    covered_period = Column(String(32), nullable=False, index=True)  # e.g. "2026-10"
    status = Column(String(32), nullable=False, default="completed")  # completed, failed, partial
    completeness_flag = Column(Boolean, nullable=False, default=True)
    source_updated_at = Column(DateTime(timezone=True), nullable=True)
    imported_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    validation_errors = Column(JSON, nullable=True, default=list)
    raw_file_uri = Column(String(512), nullable=True)


class Attendance(Base, ProvenanceMixin):
    __tablename__ = "attendance"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    work_date = Column(Date, nullable=False, index=True)
    clock_in = Column(DateTime(timezone=True), nullable=True)
    clock_out = Column(DateTime(timezone=True), nullable=True)
    timezone = Column(String(64), nullable=False, default="America/New_York")
    shift_id = Column(String(64), nullable=True)
    approval_state = Column(String(32), nullable=False, default="approved")
    hours_total = Column(Numeric(5, 2), nullable=True)
    status = Column(String(64), nullable=True)  # Present, Late, etc.
    overtime_approved = Column(String(8), nullable=True)  # Y / N

    __table_args__ = (
        UniqueConstraint("organization_id", "source_system", "source_record_id", name="uq_attendance_source"),
    )


class Leave(Base, ProvenanceMixin):
    __tablename__ = "leave"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    leave_type = Column(String(64), nullable=False)  # annual, sick, unpaid
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    days_taken = Column(Numeric(4, 2), nullable=False, default=1.0)
    approval_state = Column(String(32), nullable=False, default="approved")

    __table_args__ = (
        UniqueConstraint("organization_id", "source_system", "source_record_id", name="uq_leave_source"),
    )


class Timesheet(Base, ProvenanceMixin):
    __tablename__ = "timesheets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    work_date = Column(Date, nullable=False, index=True)
    regular_hours = Column(Numeric(5, 2), nullable=False, default=8.0)
    overtime_hours = Column(Numeric(5, 2), nullable=False, default=0.0)
    approval_state = Column(String(32), nullable=False, default="approved")
    hours_total = Column(Numeric(5, 2), nullable=True)
    status = Column(String(64), nullable=True)  # Approved, Unapproved, etc.

    __table_args__ = (
        UniqueConstraint("organization_id", "source_system", "source_record_id", name="uq_timesheet_source"),
    )


class ExpenseClaim(Base, ProvenanceMixin):
    __tablename__ = "expense_claims"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    claim_date = Column(Date, nullable=False, index=True)
    category = Column(String(64), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(8), nullable=False, default="USD")
    receipt_reference = Column(String(512), nullable=True)
    merchant_name = Column(String(255), nullable=True)
    approval_state = Column(String(32), nullable=False, default="pending")
    receipt_attached = Column(String(8), nullable=True)  # Y / N

    __table_args__ = (
        UniqueConstraint("organization_id", "source_system", "source_record_id", name="uq_expense_source"),
    )


class Document(Base, ProvenanceMixin):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    document_type = Column(String(64), nullable=False)  # passport, work_permit, driver_license
    document_reference = Column(String(512), nullable=False)
    issue_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True, index=True)
    verification_status = Column(String(32), nullable=False, default="verified")

    __table_args__ = (
        UniqueConstraint("organization_id", "source_system", "source_record_id", name="uq_document_source"),
    )


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    policy_version = Column(String(64), primary_key=True)  # e.g. "POLICY-2026.1"
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    rule_configurations = Column(JSON, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class AuditRun(Base):
    __tablename__ = "audit_runs"

    audit_run_id = Column(String(36), primary_key=True, default=generate_uuid)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    period = Column(String(32), nullable=False, index=True)
    policy_version = Column(String(64), ForeignKey("policy_versions.policy_version"), nullable=False)
    trigger_source = Column(String(64), nullable=False, default="manual")  # import_completed, manual, correction
    blocking_count = Column(Integer, nullable=False, default=0)
    warning_count = Column(Integer, nullable=False, default=0)
    data_health = Column(String(32), nullable=False, default="complete")  # complete, incomplete
    submission_allowed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    flags = relationship("AuditFlag", backref="audit_run", cascade="all, delete-orphan")


class AuditFlag(Base):
    __tablename__ = "audit_flags"

    flag_id = Column(String(36), primary_key=True, default=generate_uuid)
    audit_run_id = Column(String(36), ForeignKey("audit_runs.audit_run_id"), nullable=False, index=True)
    rule_id = Column(String(64), nullable=False, index=True)
    record_id = Column(String(128), nullable=True, index=True)
    rule_version = Column(String(16), nullable=False, default="1.0")
    outcome = Column(String(32), nullable=False)  # pass, fail, unknown, not_applicable
    severity = Column(String(32), nullable=False)  # blocking, warning, info
    evidence = Column(JSON, nullable=False, default=dict)
    policy_version = Column(String(64), nullable=False)
    suggested_action = Column(String(255), nullable=True)
    resolution_status = Column(String(32), nullable=False, default="unresolved")  # unresolved, corrected, waived
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class Correction(Base):
    __tablename__ = "corrections"

    correction_id = Column(String(36), primary_key=True, default=generate_uuid)
    flag_id = Column(String(36), ForeignKey("audit_flags.flag_id"), nullable=True, index=True)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    entity_name = Column(String(64), nullable=False)  # attendance, timesheet, expense_claim
    entity_id = Column(String(36), nullable=False, index=True)
    original_record_version = Column(Integer, nullable=False)
    original_data = Column(JSON, nullable=False)
    proposed_data = Column(JSON, nullable=False)
    employee_reason = Column(String(512), nullable=False)
    status = Column(String(32), nullable=False, default="pending_review")  # pending_review, approved, rejected
    requested_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    approvals = relationship("Approval", backref="correction", cascade="all, delete-orphan")


class Approval(Base):
    __tablename__ = "approvals"

    approval_id = Column(String(36), primary_key=True, default=generate_uuid)
    correction_id = Column(String(36), ForeignKey("corrections.correction_id"), nullable=False, index=True)
    reviewer_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    bound_record_version = Column(Integer, nullable=False)
    bound_policy_version = Column(String(64), nullable=False)
    decision = Column(String(32), nullable=False)  # approved, rejected
    manager_reason = Column(String(512), nullable=False)
    decided_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class SubmissionPack(Base):
    __tablename__ = "submission_packs"

    snapshot_id = Column(String(36), primary_key=True, default=generate_uuid)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    period = Column(String(32), nullable=False, index=True)
    policy_version = Column(String(64), nullable=False)
    frozen_data = Column(JSON, nullable=False)
    status = Column(String(32), nullable=False, default="submitted")  # submitted, approved, returned
    submitted_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    hr_reviewer_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=True)
    hr_decision = Column(String(32), nullable=True)  # approved, returned
    hr_return_reason = Column(String(512), nullable=True)


class ExportRun(Base):
    __tablename__ = "export_runs"

    export_run_id = Column(String(36), primary_key=True, default=generate_uuid)
    snapshot_id = Column(String(36), ForeignKey("submission_packs.snapshot_id"), nullable=False, index=True)
    export_type = Column(String(32), nullable=False, default="PDF_JSON_PACK")
    pack_pdf_uri = Column(String(512), nullable=True)
    pack_json_uri = Column(String(512), nullable=True)
    status = Column(String(32), nullable=False, default="pending")  # pending, delivered, failed
    destination_system = Column(String(64), nullable=False, default="payroll_staging")
    delivery_acknowledgement = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(64), nullable=False, default="ORG_DEMO_01", index=True)
    actor_id = Column(String(64), nullable=False, index=True)
    actor_role = Column(String(32), nullable=False)  # employee, manager, hr_admin, system
    action_type = Column(String(64), nullable=False, index=True)
    target_entity = Column(String(64), nullable=False)
    target_id = Column(String(128), nullable=False)
    payload_diff = Column(JSON, nullable=True)
    occurred_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


# Protect audit_events from ordinary edits and deletes (Non-negotiable immutability rule)
@event.listens_for(AuditEvent, "before_update")
def block_audit_event_update(mapper, connection, target):
    raise PermissionError("AuditEvent records are immutable and cannot be updated.")


@event.listens_for(AuditEvent, "before_delete")
def block_audit_event_delete(mapper, connection, target):
    raise PermissionError("AuditEvent records are immutable and cannot be deleted.")


class ExternalEnrichment(Base):
    __tablename__ = "external_enrichments"

    enrichment_id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(64), nullable=False)  # vendor, company, profile
    entity_id = Column(String(128), nullable=False, index=True)
    provider = Column(String(64), nullable=False, default="crustdata")
    query_key = Column(String(255), nullable=False)
    provider_response = Column(JSON, nullable=False)
    review_status = Column(String(32), nullable=False, default="unreviewed")
    retrieved_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
