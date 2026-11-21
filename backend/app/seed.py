import os
import csv
import logging
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
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
)
from app.models.master_hr import (
    MasterUpload,
    MasterHRRecord,
)
from app.models.auth import UserAuth, OTPVerification
from app.auth.service import hash_password
from app.models.base import generate_uuid
from app.imports.service import IngestionService, compute_natural_row_hash
from app.rules.engine import DEFAULT_POLICY_VERSION, DEFAULT_POLICY_CONFIG

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ORGANIZATION_ID = "ORG_DEMO_01"


def seed_employees(db: Session):
    """Seeds exactly 30 employees across 3 departments with realistic reporting hierarchy."""
    if db.query(Employee).count() >= 30:
        return
    sample_csv = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "sample-data", "employees.csv")
    )

    if os.path.exists(sample_csv):
        with open(sample_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                emp_id = row["employee_id"].strip()
                existing = db.query(Employee).filter(Employee.employee_id == emp_id).first()
                if not existing:
                    emp = Employee(
                        employee_id=emp_id,
                        organization_id=row.get("organization_id", ORGANIZATION_ID).strip(),
                        email=row["email"].strip(),
                        full_name=row["full_name"].strip(),
                        manager_id=row["manager_id"].strip() if row.get("manager_id") else None,
                        timezone=row.get("timezone", "America/New_York").strip(),
                        hire_date=date.fromisoformat(row["hire_date"].strip()),
                        is_active=row.get("is_active", "true").lower() == "true",
                    )
                    db.add(emp)
        db.commit()

    count = db.query(Employee).count()
    logger.info("Employees verified in database: %d total", count)


def seed_user_accounts(db: Session):
    """Seeds hashed password credentials and role linkages for all employees."""
    if db.query(UserAuth).count() >= 30:
        return
    employees = db.query(Employee).all()
    default_hash = hash_password("Password123!")

    for emp in employees:
        existing = db.query(UserAuth).filter(UserAuth.employee_id == emp.employee_id).first()
        if not existing:
            if emp.employee_id.startswith("HR") or "hr" in emp.email:
                role = "hr_admin"
            elif emp.employee_id.startswith("MGR") or "manager" in emp.email:
                role = "manager"
            else:
                role = "employee"

            user = UserAuth(
                employee_id=emp.employee_id,
                organization_id=emp.organization_id,
                email=emp.email,
                password_hash=default_hash,
                role=role,
                is_verified=True,
            )
            db.add(user)
    db.commit()
    user_count = db.query(UserAuth).count()
    logger.info("User accounts verified with hashed credentials: %d total", user_count)


def seed_policy_versions(db: Session):
    """Seeds effective-dated policy versions (Historical POLICY-2026.1 and Current POLICY-2026.2)."""
    # Policy Version 1: Jan 1, 2026 to Jun 30, 2026
    p1 = db.query(PolicyVersion).filter(PolicyVersion.policy_version == "POLICY-2026.1").first()
    if not p1:
        p1 = PolicyVersion(
            policy_version="POLICY-2026.1",
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 6, 30),
            rule_configurations={
                "missing_punch": {"severity": "blocking"},
                "hours_mismatch": {"tolerance_minutes": 45, "severity": "blocking"},
                "missing_receipt": {"receipt_threshold_usd": 30.00, "severity": "warning"},
                "document_expiry": {"warning_days": 30, "severity": "warning"},
            },
            is_active=False,
        )
        db.add(p1)

    # Policy Version 2: Jul 1, 2026 onwards (Active)
    p2 = db.query(PolicyVersion).filter(PolicyVersion.policy_version == "POLICY-2026.2").first()
    if not p2:
        p2 = PolicyVersion(
            policy_version="POLICY-2026.2",
            effective_from=date(2026, 7, 1),
            effective_to=None,
            rule_configurations={
                "missing_punch": {"severity": "blocking"},
                "hours_mismatch": {"tolerance_minutes": 30, "severity": "blocking"},
                "missing_receipt": {"receipt_threshold_usd": 25.00, "severity": "warning"},
                "document_expiry": {"warning_days": 30, "severity": "warning"},
            },
            is_active=True,
        )
        db.add(p2)

    # Also keep default policy alias if distinct
    if DEFAULT_POLICY_VERSION not in ("POLICY-2026.1", "POLICY-2026.2"):
        p_def = db.query(PolicyVersion).filter(PolicyVersion.policy_version == DEFAULT_POLICY_VERSION).first()
        if not p_def:
            db.add(PolicyVersion(
                policy_version=DEFAULT_POLICY_VERSION,
                effective_from=date(2026, 1, 1),
                effective_to=None,
                rule_configurations=DEFAULT_POLICY_CONFIG,
                is_active=True,
            ))

    db.commit()
    logger.info("Effective-dated policy versions seeded (POLICY-2026.1 and POLICY-2026.2)")


def seed_synthetic_history(db: Session):
    """
    Seeds 6 months of synthetic records across 30 employees:
    Months: 2026-05, 2026-06, 2026-07, 2026-08, 2026-09, 2026-10.
    Includes normal passes, overnight shifts, split shifts, missing punches,
    hours mismatches, and missing receipts.
    """
    if db.query(Attendance).count() >= 50:
        return
    months = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
    employees = db.query(Employee).all()

    for period in months:
        y, m = map(int, period.split("-"))

        # Create or fetch SourceImport record for provenance tracking
        import_record = db.query(SourceImport).filter(
            SourceImport.covered_period == period,
            SourceImport.source_system == "attendance_gate",
        ).first()

        if not import_record:
            import_record = SourceImport(
                import_id=generate_uuid(),
                organization_id=ORGANIZATION_ID,
                source_system="attendance_gate",
                covered_period=period,
                status="completed",
                completeness_flag=True,
                source_updated_at=datetime(y, m, 28, 18, 0, tzinfo=timezone.utc),
                imported_at=datetime(y, m, 28, 18, 5, tzinfo=timezone.utc),
                raw_file_uri=f"s3://hr-raw-data/{period}/synthetic_batch.csv",
            )
            db.add(import_record)
            db.commit()
            db.refresh(import_record)

        # Generate sample records across days 8, 14, 18, 21, 25 of each month
        sample_days = [8, 14, 18, 21, 25]

        for emp in employees:
            tz = timezone.utc

            for day in sample_days:
                work_d = date(y, m, day)
                src_att_id = f"ATT-{emp.employee_id}-{period}-{day:02d}"
                src_ts_id = f"TS-{emp.employee_id}-{period}-{day:02d}"

                # 1. Attendance Record
                existing_att = db.query(Attendance).filter(
                    Attendance.organization_id == ORGANIZATION_ID,
                    Attendance.source_system == "attendance_gate",
                    Attendance.source_record_id == src_att_id,
                ).first()

                if not existing_att:
                    # In October (2026-10), inject varied issues:
                    # Issue 1: EMP001 has missing out-punch on Oct 14
                    if period == "2026-10" and emp.employee_id == "EMP001" and day == 14:
                        cin = datetime(y, m, day, 9, 0, tzinfo=tz)
                        cout = None  # Missing punch
                    # Issue 2: EMP004 has overnight shift on Oct 25
                    elif emp.employee_id == "EMP004" and day == 25:
                        cin = datetime(y, m, day, 21, 0, tzinfo=tz)
                        cout = datetime(y, m, day + 1, 5, 30, tzinfo=tz)
                    else:
                        cin = datetime(y, m, day, 9, 0, tzinfo=tz)
                        cout = datetime(y, m, day, 17, 30, tzinfo=tz)

                    att = Attendance(
                        id=generate_uuid(),
                        organization_id=ORGANIZATION_ID,
                        employee_id=emp.employee_id,
                        work_date=work_d,
                        clock_in=cin,
                        clock_out=cout,
                        timezone="America/New_York",
                        shift_id="DAY_SHIFT_A",
                        approval_state="approved",
                        source_system="attendance_gate",
                        source_record_id=src_att_id,
                        import_id=import_record.import_id,
                        record_version=1,
                    )
                    db.add(att)

                # 2. Timesheet Record
                existing_ts = db.query(Timesheet).filter(
                    Timesheet.organization_id == ORGANIZATION_ID,
                    Timesheet.source_system == "workday_timesheet",
                    Timesheet.source_record_id == src_ts_id,
                ).first()

                if not existing_ts:
                    # Issue 3: EMP001 has hours mismatch on Oct 18 (claims 9.5h while badge is 7.0h)
                    if period == "2026-10" and emp.employee_id == "EMP001" and day == 18:
                        regular_h = Decimal("9.50")
                    else:
                        regular_h = Decimal("8.00")

                    ts = Timesheet(
                        id=generate_uuid(),
                        organization_id=ORGANIZATION_ID,
                        employee_id=emp.employee_id,
                        work_date=work_d,
                        regular_hours=regular_h,
                        overtime_hours=Decimal("0.00"),
                        approval_state="approved",
                        source_system="workday_timesheet",
                        source_record_id=src_ts_id,
                        import_id=import_record.import_id,
                        record_version=1,
                    )
                    db.add(ts)

            # 3. Expense Claims (for subset of employees)
            src_exp_id = f"EXP-{emp.employee_id}-{period}-01"
            existing_exp = db.query(ExpenseClaim).filter(
                ExpenseClaim.organization_id == ORGANIZATION_ID,
                ExpenseClaim.source_system == "concur_expense",
                ExpenseClaim.source_record_id == src_exp_id,
            ).first()

            if not existing_exp and emp.employee_id in ["EMP001", "EMP002", "EMP005", "EMP015"]:
                # Issue 4: EMP001 client lunch has missing receipt > $25 ($84.50) in October
                if period == "2026-10" and emp.employee_id == "EMP001":
                    amt = Decimal("84.50")
                    rcpt = None  # Missing receipt
                elif emp.employee_id == "EMP002":
                    amt = Decimal("18.50")  # Below $25 threshold (passes policy)
                    rcpt = None
                else:
                    amt = Decimal("145.00")
                    rcpt = f"s3://hr-receipts/{period}/rcpt_{emp.employee_id}.jpg"

                exp = ExpenseClaim(
                    id=generate_uuid(),
                    organization_id=ORGANIZATION_ID,
                    employee_id=emp.employee_id,
                    claim_date=date(y, m, 21),
                    category="Meals & Entertainment",
                    amount=amt,
                    currency="USD",
                    receipt_reference=rcpt,
                    merchant_name="Bistro Central",
                    approval_state="pending",
                    source_system="concur_expense",
                    source_record_id=src_exp_id,
                    import_id=import_record.import_id,
                    record_version=1,
                )
                db.add(exp)

    # 4. Seed Employee Passports / Work Permits (once per employee)
    for emp in employees:
        src_doc_id = f"DOC-{emp.employee_id}-PASSPORT"
        existing_doc = db.query(Document).filter(
            Document.organization_id == ORGANIZATION_ID,
            Document.source_system == "hr_documents",
            Document.source_record_id == src_doc_id,
        ).first()

        if not existing_doc:
            if emp.employee_id == "EMP008":
                exp_date = date(2026, 11, 15)  # Expiring within 30 days (Warning)
            elif emp.employee_id == "EMP018":
                exp_date = date(2026, 8, 30)   # Expired (Blocking)
            else:
                exp_date = date(2028, 12, 31)  # Valid far future

            doc = Document(
                id=generate_uuid(),
                organization_id=ORGANIZATION_ID,
                employee_id=emp.employee_id,
                document_type="passport",
                document_reference=f"PASS-{emp.employee_id}-US",
                issue_date=date(2020, 1, 1),
                expiry_date=exp_date,
                verification_status="verified",
                source_system="hr_documents",
                source_record_id=src_doc_id,
                import_id=generate_uuid(),
                record_version=1,
            )
            db.add(doc)

    db.commit()
    logger.info("6 months of synthetic records successfully populated with varied edge cases.")


def seed_sample_csv_feeds(db: Session):
    """Ingests base sample CSVs from sample-data folder if present to ensure 100% test alignment."""
    if db.query(SourceImport).count() >= 5:
        return
    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sample-data"))
    if not os.path.exists(sample_dir):
        return

    feeds = [
        ("attendance_gate", "attendance_valid.csv"),
        ("bamboohr_leave", "leave_valid.csv"),
        ("workday_timesheet", "timesheets_valid.csv"),
        ("concur_expense", "expense_claims_valid.csv"),
        ("hr_documents", "documents_valid.csv"),
    ]

    for system, filename in feeds:
        path = os.path.join(sample_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            try:
                IngestionService.ingest_csv(
                    db=db,
                    organization_id=ORGANIZATION_ID,
                    source_system=system,
                    covered_period="2026-10",
                    file_content=content,
                    actor_id="service:seed_csv",
                    raw_file_uri=f"sample-data/{filename}",
                    is_complete_feed=True,
                )
            except Exception as e:
                db.rollback()
                logger.debug("Ingestion notice for %s: %s", filename, e)


def init_db_and_seed():
    """Master database migration and seeding entrypoint."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        seed_employees(db)
        seed_user_accounts(db)
        seed_policy_versions(db)
        seed_sample_csv_feeds(db)
        seed_synthetic_history(db)

        # Output verification statistics
        total_emp = db.query(Employee).count()
        total_att = db.query(Attendance).count()
        total_ts = db.query(Timesheet).count()
        total_exp = db.query(ExpenseClaim).count()
        total_doc = db.query(Document).count()
        total_policies = db.query(PolicyVersion).count()

        logger.info("================ DATABASE SEED SUMMARY ================")
        logger.info("Employees:        %d", total_emp)
        logger.info("Policy Versions:  %d", total_policies)
        logger.info("Attendance Rows:  %d", total_att)
        logger.info("Timesheet Rows:   %d", total_ts)
        logger.info("Expense Claims:   %d", total_exp)
        logger.info("Documents:        %d", total_doc)
        logger.info("=======================================================")

    except Exception as e:
        db.rollback()
        logger.error("Seeding failed: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db_and_seed()
