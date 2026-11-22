from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any, List
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
    Text,
    func,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import generate_uuid


class DutyTask(Base):
    """
    Generic task engine storing all bot-prepared and human-decided tasks across the 10 HR duties.
    Status flow: queued -> prepared -> awaiting_approval -> approved | rejected | returned
    Includes version for optimistic locking.
    """
    __tablename__ = "duty_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    duty_key = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(64), nullable=True, index=True)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=True, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="queued", index=True)
    prepared_by = Column(String(64), nullable=False, default="bot")
    prepared_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    approver_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=True, index=True)
    approver_role = Column(String(32), nullable=True)
    decision_note = Column(String(1024), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(Date, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    employee = relationship("Employee", foreign_keys=[employee_id])
    approver = relationship("Employee", foreign_keys=[approver_id])


# Duty 1: Payroll & Statutory
class PayrollConfig(Base):
    __tablename__ = "payroll_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    effective_from = Column(Date, nullable=False, default=date(2026, 1, 1))
    basic_pct = Column(Numeric(5, 2), nullable=False, default=40.0)
    hra_pct = Column(Numeric(5, 2), nullable=False, default=20.0)
    pf_rate_pct = Column(Numeric(5, 2), nullable=False, default=12.0)
    pf_wage_ceiling = Column(Numeric(10, 2), nullable=False, default=15000.00)
    esi_rate_pct = Column(Numeric(5, 2), nullable=False, default=0.75)
    esi_wage_ceiling = Column(Numeric(10, 2), nullable=False, default=21000.00)
    pt_slabs = Column(JSON, nullable=False, default=dict)
    standard_deduction = Column(Numeric(10, 2), nullable=False, default=50000.00)
    disclaimer = Column(String(255), nullable=False, default="Sample values, verify against current law before real use")
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class EmployeeSalary(Base):
    __tablename__ = "employee_salaries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), unique=True, nullable=False, index=True)
    ctc_annual = Column(Numeric(12, 2), nullable=False)
    monthly_gross = Column(Numeric(12, 2), nullable=False)
    basic_pay = Column(Numeric(12, 2), nullable=False)
    hra = Column(Numeric(12, 2), nullable=False)
    special_allowance = Column(Numeric(12, 2), nullable=False)
    state = Column(String(64), nullable=False, default="Karnataka")
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    employee = relationship("Employee", foreign_keys=[employee_id])


class PayrollRun(Base):
    __tablename__ = "payroll_runs"

    run_id = Column(String(36), primary_key=True, default=generate_uuid)
    period = Column(String(32), nullable=False, index=True)  # e.g. "2026-10"
    total_employees = Column(Integer, nullable=False, default=0)
    total_gross = Column(Numeric(12, 2), nullable=False, default=0.0)
    total_pf = Column(Numeric(12, 2), nullable=False, default=0.0)
    total_esi = Column(Numeric(12, 2), nullable=False, default=0.0)
    total_pt = Column(Numeric(12, 2), nullable=False, default=0.0)
    total_tds = Column(Numeric(12, 2), nullable=False, default=0.0)
    total_net = Column(Numeric(12, 2), nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="calculated")  # calculated, approved, challans_paid
    approved_by = Column(String(64), ForeignKey("employees.employee_id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    challan_pf_no = Column(String(64), nullable=True)
    challan_esi_no = Column(String(64), nullable=True)
    challan_pt_no = Column(String(64), nullable=True)
    challan_payment_date = Column(Date, nullable=True)
    payslips_generated = Column(Boolean, nullable=False, default=True)
    records_json = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


# Duty 2: Labour Law Compliance
class ComplianceDeadline(Base):
    __tablename__ = "compliance_deadlines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    authority = Column(String(32), nullable=False, index=True)  # TDS, PF, ESI, PT
    period = Column(String(32), nullable=False, index=True)
    due_date = Column(Date, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(512), nullable=False)
    reminder_days = Column(JSON, nullable=False, default=list)  # [7, 3, 1]
    status = Column(String(32), nullable=False, default="pending")  # pending, ready_for_signoff, completed
    challan_reference = Column(String(128), nullable=True)
    signed_off_by = Column(String(64), ForeignKey("employees.employee_id"), nullable=True)
    signed_off_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


# Duty 3: POSH
class POSHRecord(Base):
    __tablename__ = "posh_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_number = Column(String(64), unique=True, nullable=False, index=True)
    incident_date = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, default="received")  # received, inquiry_ongoing, resolved, dismissed
    encrypted_complaint = Column(Text, nullable=False)
    disposition = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)


class POSHCommitteeMember(Base):
    __tablename__ = "posh_committee_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    role = Column(String(64), nullable=False)  # Presiding Officer, External Member, Internal Member
    email = Column(String(255), nullable=False, index=True)
    contact = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class POSHAwarenessSession(Base):
    __tablename__ = "posh_awareness_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    topic = Column(String(255), nullable=False)
    session_date = Column(Date, nullable=False)
    attendees_count = Column(Integer, nullable=False, default=0)
    mode = Column(String(64), nullable=False, default="In-person & Virtual")
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class POSHAcknowledgment(Base):
    __tablename__ = "posh_acknowledgments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    policy_version = Column(String(32), nullable=False, default="POSH-2026.1")
    acknowledged_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


# Duty 4: Discipline & Grievance
class GrievanceCase(Base):
    __tablename__ = "grievance_cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_number = Column(String(64), unique=True, nullable=False, index=True)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    category = Column(String(64), nullable=False)  # grievance, misconduct, attendance_violation
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    sla_due_date = Column(Date, nullable=False)
    status = Column(String(32), nullable=False, default="open")  # open, in_review, action_taken, closed
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    employee = relationship("Employee", foreign_keys=[employee_id])


class DisciplinaryNotice(Base):
    __tablename__ = "disciplinary_notices"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("grievance_cases.id"), nullable=False, index=True)
    notice_type = Column(String(64), nullable=False)  # show_cause, warning, outcome
    recipient_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    draft_text = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="draft")  # draft, approved_issued
    approved_by = Column(String(64), ForeignKey("employees.employee_id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


# Duty 5: Recruitment
class JobOpening(Base):
    __tablename__ = "job_openings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    department = Column(String(64), nullable=False)
    min_experience = Column(Integer, nullable=False, default=1)
    required_skills = Column(JSON, nullable=False, default=list)
    template_text = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="open")  # open, closed
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class JobApplicant(Base):
    __tablename__ = "job_applicants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("job_openings.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    education = Column(String(128), nullable=False)
    years_experience = Column(Numeric(4, 1), nullable=False, default=0.0)
    skills = Column(JSON, nullable=False, default=list)
    screening_score = Column(Integer, nullable=False, default=0)
    screening_reasons = Column(JSON, nullable=False, default=list)
    status = Column(String(32), nullable=False, default="screened")  # screened, shortlisted, interview_scheduled, offered, rejected
    interview_slot = Column(DateTime(timezone=True), nullable=True)
    offered_salary = Column(Numeric(12, 2), nullable=True)
    offer_approved_by = Column(String(64), ForeignKey("employees.employee_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    job = relationship("JobOpening")


# Duty 6: Onboarding
class OnboardingChecklist(Base):
    __tablename__ = "onboarding_checklists"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), unique=True, nullable=False, index=True)
    join_date = Column(Date, nullable=False)
    probation_end_date = Column(Date, nullable=False)
    doc_status = Column(String(32), nullable=False, default="submitted")  # pending, submitted, verified
    it_status = Column(String(32), nullable=False, default="provisioned")  # requested, provisioned
    induction_status = Column(String(32), nullable=False, default="completed")  # scheduled, completed
    probation_status = Column(String(32), nullable=False, default="in_probation")  # in_probation, confirmed, extended
    confirmed_by = Column(String(64), ForeignKey("employees.employee_id"), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    employee = relationship("Employee", foreign_keys=[employee_id])


# Duty 7: Attendance & Leave (leave balances table)
class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    leave_type = Column(String(32), nullable=False)  # casual, sick, earned
    accrued = Column(Numeric(4, 1), nullable=False, default=12.0)
    taken = Column(Numeric(4, 1), nullable=False, default=0.0)
    remaining = Column(Numeric(4, 1), nullable=False, default=12.0)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    employee = relationship("Employee", foreign_keys=[employee_id])


# Duty 8: Offboarding & FNF
class OffboardingCase(Base):
    __tablename__ = "offboarding_cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    resignation_date = Column(Date, nullable=False)
    last_working_date = Column(Date, nullable=False)
    notice_required_days = Column(Integer, nullable=False, default=30)
    notice_served_days = Column(Integer, nullable=False, default=30)
    it_clearance = Column(Boolean, nullable=False, default=False)
    finance_clearance = Column(Boolean, nullable=False, default=False)
    admin_clearance = Column(Boolean, nullable=False, default=False)
    hr_clearance = Column(Boolean, nullable=False, default=False)
    pending_salary = Column(Numeric(10, 2), nullable=False, default=0.0)
    leave_encashment = Column(Numeric(10, 2), nullable=False, default=0.0)
    shortfall_recovery = Column(Numeric(10, 2), nullable=False, default=0.0)
    gratuity_eligible = Column(Boolean, nullable=False, default=False)
    gratuity_amount = Column(Numeric(10, 2), nullable=False, default=0.0)
    net_payable = Column(Numeric(10, 2), nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="initiated")  # initiated, clearance_in_progress, fnf_calculated, approved_closed
    approved_by = Column(String(64), ForeignKey("employees.employee_id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    employee = relationship("Employee", foreign_keys=[employee_id])


# Duty 9: Policies & Records
class PolicyLibraryItem(Base):
    __tablename__ = "policy_library"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False)  # leave, code_of_conduct, compensation, safety
    version = Column(String(32), nullable=False, default="v1.0")
    content_markdown = Column(Text, nullable=False)
    is_published = Column(Boolean, nullable=False, default=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String(64), ForeignKey("employees.employee_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class PolicyAckRecord(Base):
    __tablename__ = "policy_acknowledgments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    policy_id = Column(String(36), ForeignKey("policy_library.id"), nullable=False, index=True)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    version = Column(String(32), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class RetentionRecord(Base):
    __tablename__ = "retention_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    record_type = Column(String(64), nullable=False)  # tax, payroll, contract, medical
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    retention_tag = Column(String(64), nullable=False)  # e.g. "Tax: 8 years", "Personnel: 10 years"
    expires_at = Column(Date, nullable=False)
    status = Column(String(32), nullable=False, default="retained")
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


# Duty 10: Performance
class PerformanceCycle(Base):
    __tablename__ = "performance_cycles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    cycle_name = Column(String(255), nullable=False)
    period = Column(String(32), nullable=False, index=True)  # e.g. "2026-H2"
    status = Column(String(32), nullable=False, default="active")  # active, evaluating, finalized
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class PerformanceReview(Base):
    __tablename__ = "performance_reviews"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    cycle_id = Column(String(36), ForeignKey("performance_cycles.id"), nullable=False, index=True)
    employee_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    manager_id = Column(String(64), ForeignKey("employees.employee_id"), nullable=False, index=True)
    self_goals_json = Column(JSON, nullable=False, default=list)
    peer_feedback_json = Column(JSON, nullable=False, default=list)
    deterministic_summary = Column(JSON, nullable=False, default=dict)
    human_rating = Column(Numeric(3, 1), nullable=True)  # 1.0 to 5.0
    increment_pct = Column(Numeric(4, 2), nullable=True)  # e.g. 8.5%
    pip_flag = Column(Boolean, nullable=False, default=False)
    pip_notes = Column(Text, nullable=True)
    approved_by = Column(String(64), ForeignKey("employees.employee_id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    cycle = relationship("PerformanceCycle")
    employee = relationship("Employee", foreign_keys=[employee_id])
    manager = relationship("Employee", foreign_keys=[manager_id])
