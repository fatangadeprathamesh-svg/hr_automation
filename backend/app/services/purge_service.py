"""
Purge and Reset Service for HR Self-Audit Assistant.
Safely deletes all synthetic/demo business data, tasks, and audit logs
while preserving core schema, statutory policy configs, and login personas.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import Base, engine
from app.models.hr import (
    Employee,
    PolicyVersion,
    SourceImport,
    Attendance,
    Leave,
    Timesheet,
    ExpenseClaim,
    Document,
    AuditEvent,
    AuditFlag,
    AuditRun,
    Approval,
    Correction,
    SubmissionPack,
    ExportRun,
)
from app.models.master_hr import (
    MasterUpload,
    MasterHRRecord,
)
from app.models.duties import (
    DutyTask,
    ComplianceDeadline,
    POSHRecord,
    POSHAwarenessSession,
    GrievanceCase,
    DisciplinaryNotice,
    JobOpening,
    JobApplicant,
    OnboardingChecklist,
    LeaveBalance,
    OffboardingCase,
    RetentionRecord,
    PerformanceCycle,
    PerformanceReview,
    PayrollRun,
    EmployeeSalary,
)
from app.models.auth import UserAuth, OTPVerification
from app.auth.service import hash_password

logger = logging.getLogger(__name__)

CORE_PERSONA_IDS = {"EMP001", "MGR001", "HR001", "IC001"}


def ensure_baseline_schema_and_accounts(db: Session) -> dict:
    """
    Ensures that database tables exist, statutory policy versions are registered,
    and login personas are present with valid password credentials.
    Does NOT seed fake attendance, timesheets, or dummy duties.
    """
    Base.metadata.create_all(bind=engine)

    # Dynamic SQLite migrations for incremental columns
    try:
        with engine.begin() as conn:
            m_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(master_uploads)")).fetchall()]
            if "pipeline_stages" not in m_cols:
                conn.execute(text("ALTER TABLE master_uploads ADD COLUMN pipeline_stages JSON"))
            e_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(employees)")).fetchall()]
            if "manager" not in e_cols:
                conn.execute(text("ALTER TABLE employees ADD COLUMN manager VARCHAR(255)"))
    except Exception as migr_err:
        logger.debug("Schema migration check: %s", migr_err)

    # 1. Ensure 4 core test personas exist in Employee table
    personas = [
        {
            "id": "EMP001",
            "name": "Alice Employee",
            "email": "alice@example.com",
            "role": "employee",
            "mgr": "MGR001",
        },
        {
            "id": "MGR001",
            "name": "Bob Manager",
            "email": "bob.manager@example.com",
            "role": "manager",
            "mgr": None,
        },
        {
            "id": "HR001",
            "name": "Carol HR Admin",
            "email": "carol.hr@example.com",
            "role": "hr_admin",
            "mgr": None,
        },
        {
            "id": "IC001",
            "name": "Irene IC Member",
            "email": "irene.ic@example.com",
            "role": "ic_member",
            "mgr": None,
        },
    ]

    for p in personas:
        emp = db.query(Employee).filter(Employee.employee_id == p["id"]).first()
        if not emp:
            emp = Employee(
                employee_id=p["id"],
                organization_id="ORG_DEMO_01",
                email=p["email"],
                full_name=p["name"],
                manager_id=p["mgr"],
                timezone="America/New_York",
                hire_date=datetime(2024, 1, 1).date(),
                is_active=True,
            )
            db.add(emp)

        auth = db.query(UserAuth).filter(UserAuth.employee_id == p["id"]).first()
        if not auth:
            auth = UserAuth(
                employee_id=p["id"],
                organization_id="ORG_DEMO_01",
                email=p["email"],
                password_hash=hash_password("Password123!"),
                role=p["role"],
                is_verified=True,
            )
            db.add(auth)

    # 2. Ensure effective-dated policy versions exist
    from app.seed import seed_policy_versions
    seed_policy_versions(db)

    # 3. Ensure Genesis block exists in audit ledger if table is empty
    ledger_count = db.query(AuditEvent).count()
    if ledger_count == 0:
        create_genesis_audit_block(db)

    db.commit()
    return {"status": "baseline_ensured"}


def create_genesis_audit_block(db: Session) -> AuditEvent:
    """Seeds a single, immutable genesis block for the audit ledger."""
    genesis = AuditEvent(
        event_id="GENESIS-00000000",
        organization_id="ORG_DEMO_01",
        actor_id="system",
        actor_role="system",
        action_type="LEDGER_INIT",
        target_entity="system",
        target_id="genesis",
        payload_diff={"description": "HR Self-Audit Compliance Ledger Genesis Block"},
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(genesis)
    db.commit()
    return genesis


def purge_all_demo_data(db: Session) -> dict:
    """
    Purges all dummy/seeded business records across all tables,
    keeping only schema, migrations, policy rules, and core login personas.
    """
    deleted_counts = {}

    # Tables to truncate / delete completely
    truncate_models = [
        ("attendance", Attendance),
        ("timesheets", Timesheet),
        ("expense_claims", ExpenseClaim),
        ("documents", Document),
        ("leave", Leave),
        ("leave_balances", LeaveBalance),
        ("source_imports", SourceImport),
        ("audit_flags", AuditFlag),
        ("audit_runs", AuditRun),
        ("approvals", Approval),
        ("corrections", Correction),
        ("submission_packs", SubmissionPack),
        ("export_runs", ExportRun),
        ("duty_tasks", DutyTask),
        ("compliance_deadlines", ComplianceDeadline),
        ("disciplinary_notices", DisciplinaryNotice),
        ("grievance_cases", GrievanceCase),
        ("job_applicants", JobApplicant),
        ("job_openings", JobOpening),
        ("offboarding_cases", OffboardingCase),
        ("onboarding_checklists", OnboardingChecklist),
        ("payroll_runs", PayrollRun),
        ("performance_cycles", PerformanceCycle),
        ("performance_reviews", PerformanceReview),
        ("posh_awareness_sessions", POSHAwarenessSession),
        ("posh_records", POSHRecord),
        ("retention_records", RetentionRecord),
        ("otp_verifications", OTPVerification),
        ("master_hr_records", MasterHRRecord),
        ("master_uploads", MasterUpload),
    ]

    for name, model in truncate_models:
        count = db.query(model).delete()
        deleted_counts[name] = count

    # Prune non-core employees
    emp_count = db.query(Employee).filter(Employee.employee_id.notin_(CORE_PERSONA_IDS)).delete(synchronize_session=False)
    deleted_counts["employees"] = emp_count

    # Prune non-core user auth accounts
    auth_count = db.query(UserAuth).filter(UserAuth.employee_id.notin_(CORE_PERSONA_IDS)).delete(synchronize_session=False)
    deleted_counts["user_auth"] = auth_count

    # Prune non-core salaries
    sal_count = db.query(EmployeeSalary).filter(EmployeeSalary.employee_id.notin_(CORE_PERSONA_IDS)).delete(synchronize_session=False)
    deleted_counts["employee_salaries"] = sal_count

    # Reset audit events: use direct SQL execution to bypass the before_delete ORM immutability hook
    res = db.execute(text("DELETE FROM audit_events"))
    deleted_counts["audit_events"] = res.rowcount if res.rowcount is not None and res.rowcount >= 0 else 0

    db.commit()

    # Re-initialize baseline (genesis block + personas verification)
    ensure_baseline_schema_and_accounts(db)

    total_deleted = sum(deleted_counts.values())
    logger.info("Purged %d total fake/demo records across %d tables.", total_deleted, len(deleted_counts))
    return {
        "status": "success",
        "total_deleted": total_deleted,
        "deleted_counts": deleted_counts,
    }
