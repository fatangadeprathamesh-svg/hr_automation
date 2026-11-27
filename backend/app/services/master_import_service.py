import os
import csv
import time
import logging
import re
from datetime import datetime, date, timezone, time as dtime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set
from sqlalchemy import text, or_, func
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.master_hr import MasterUpload, MasterHRRecord
from app.models.hr import Employee, AuditEvent
from app.models.auth import UserAuth
from app.rules.engine import AuditEngine

logger = logging.getLogger(__name__)

# Master 61 columns (55 standard + 6 optional backward-compatible extensions)
COLUMNS = [
    "record_id", "record_type", "source_file", "employee_id", "applicant_id",
    "employee_name", "first_name", "last_name", "department", "position",
    "division", "business_unit", "branch_location", "manager", "employment_type",
    "gender", "age", "dob", "marital_status", "state", "education",
    "hire_date", "exit_date", "employee_status", "performance_score",
    "performance_rating", "monthly_income", "years_experience", "salary_hike_pct",
    "event_date", "start_date", "end_date", "applied_date", "status",
    "category", "reason", "days", "clock_in", "clock_out", "hours_total",
    "hours_scheduled", "break_minutes", "leave_entitlement", "leave_taken_so_far",
    "leave_remaining", "engagement_score", "satisfaction_score",
    "work_life_balance_score", "training_program", "training_outcome",
    "trainer", "training_location", "training_cost", "desired_salary", "country",
    # 6 optional columns
    "email", "project_code", "amount", "expense_category", "receipt_attached", "overtime_approved"
]

DATE_FIELDS = {
    "dob", "hire_date", "exit_date", "event_date", "start_date", "end_date", "applied_date"
}

NUMERIC_FLOAT_FIELDS = {
    "monthly_income", "years_experience", "salary_hike_pct", "days",
    "hours_total", "hours_scheduled", "break_minutes", "leave_entitlement",
    "leave_taken_so_far", "leave_remaining", "engagement_score",
    "satisfaction_score", "work_life_balance_score", "training_cost", "desired_salary",
    "amount"
}

NUMERIC_INT_FIELDS = {"age"}

VALID_RECORD_TYPES = {
    "employee_profile",
    "leave_request",
    "leave_balance",
    "timesheet",
    "training",
    "engagement_survey",
    "applicant",
    "attendance",
    "expense",
}

UPSERT_SQL = f"""
INSERT INTO master_hr_records (
    record_id, upload_id, record_type, source_file, employee_id, applicant_id,
    employee_name, first_name, last_name, department, position, division,
    business_unit, branch_location, manager, employment_type, gender, age, dob,
    marital_status, state, education, hire_date, exit_date, employee_status,
    performance_score, performance_rating, monthly_income, years_experience,
    salary_hike_pct, event_date, start_date, end_date, applied_date, status,
    category, reason, days, clock_in, clock_out, hours_total, hours_scheduled,
    break_minutes, leave_entitlement, leave_taken_so_far, leave_remaining,
    engagement_score, satisfaction_score, work_life_balance_score,
    training_program, training_outcome, trainer, training_location, training_cost,
    desired_salary, country, email, project_code, amount, expense_category,
    receipt_attached, overtime_approved, created_at, updated_at
) VALUES (
    :record_id, :upload_id, :record_type, :source_file, :employee_id, :applicant_id,
    :employee_name, :first_name, :last_name, :department, :position, :division,
    :business_unit, :branch_location, :manager, :employment_type, :gender, :age, :dob,
    :marital_status, :state, :education, :hire_date, :exit_date, :employee_status,
    :performance_score, :performance_rating, :monthly_income, :years_experience,
    :salary_hike_pct, :event_date, :start_date, :end_date, :applied_date, :status,
    :category, :reason, :days, :clock_in, :clock_out, :hours_total, :hours_scheduled,
    :break_minutes, :leave_entitlement, :leave_taken_so_far, :leave_remaining,
    :engagement_score, :satisfaction_score, :work_life_balance_score,
    :training_program, :training_outcome, :trainer, :training_location, :training_cost,
    :desired_salary, :country, :email, :project_code, :amount, :expense_category,
    :receipt_attached, :overtime_approved, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT(record_id) DO UPDATE SET
    upload_id = excluded.upload_id,
    record_type = excluded.record_type,
    source_file = excluded.source_file,
    employee_id = excluded.employee_id,
    applicant_id = excluded.applicant_id,
    employee_name = excluded.employee_name,
    first_name = excluded.first_name,
    last_name = excluded.last_name,
    department = excluded.department,
    position = excluded.position,
    division = excluded.division,
    business_unit = excluded.business_unit,
    branch_location = excluded.branch_location,
    manager = excluded.manager,
    employment_type = excluded.employment_type,
    gender = excluded.gender,
    age = excluded.age,
    dob = excluded.dob,
    marital_status = excluded.marital_status,
    state = excluded.state,
    education = excluded.education,
    hire_date = excluded.hire_date,
    exit_date = excluded.exit_date,
    employee_status = excluded.employee_status,
    performance_score = excluded.performance_score,
    performance_rating = excluded.performance_rating,
    monthly_income = excluded.monthly_income,
    years_experience = excluded.years_experience,
    salary_hike_pct = excluded.salary_hike_pct,
    event_date = excluded.event_date,
    start_date = excluded.start_date,
    end_date = excluded.end_date,
    applied_date = excluded.applied_date,
    status = excluded.status,
    category = excluded.category,
    reason = excluded.reason,
    days = excluded.days,
    clock_in = excluded.clock_in,
    clock_out = excluded.clock_out,
    hours_total = excluded.hours_total,
    hours_scheduled = excluded.hours_scheduled,
    break_minutes = excluded.break_minutes,
    leave_entitlement = excluded.leave_entitlement,
    leave_taken_so_far = excluded.leave_taken_so_far,
    leave_remaining = excluded.leave_remaining,
    engagement_score = excluded.engagement_score,
    satisfaction_score = excluded.satisfaction_score,
    work_life_balance_score = excluded.work_life_balance_score,
    training_program = excluded.training_program,
    training_outcome = excluded.training_outcome,
    trainer = excluded.trainer,
    training_location = excluded.training_location,
    training_cost = excluded.training_cost,
    desired_salary = excluded.desired_salary,
    country = excluded.country,
    email = excluded.email,
    project_code = excluded.project_code,
    amount = excluded.amount,
    expense_category = excluded.expense_category,
    receipt_attached = excluded.receipt_attached,
    overtime_approved = excluded.overtime_approved,
    updated_at = CURRENT_TIMESTAMP
"""

UPSERT_EMPLOYEE_SQL = """
INSERT INTO employees (employee_id, organization_id, email, full_name, manager, timezone, hire_date, termination_date, is_active, created_at)
VALUES (:employee_id, :organization_id, :email, :full_name, :manager, 'America/New_York', :hire_date, :termination_date, :is_active, CURRENT_TIMESTAMP)
ON CONFLICT(employee_id) DO UPDATE SET
    email = excluded.email,
    full_name = excluded.full_name,
    manager = excluded.manager,
    hire_date = excluded.hire_date,
    termination_date = excluded.termination_date,
    is_active = excluded.is_active
"""

UPSERT_ATTENDANCE_SQL = """
INSERT INTO attendance (id, organization_id, source_system, source_record_id, employee_id, work_date, clock_in, clock_out, timezone, shift_id, approval_state, hours_total, status, overtime_approved, import_id, imported_at, record_version)
VALUES (:id, :organization_id, 'master_csv', :record_id, :employee_id, :work_date, :clock_in, :clock_out, 'America/New_York', NULL, 'approved', :hours_total, :status, :overtime_approved, :upload_id, CURRENT_TIMESTAMP, 1)
ON CONFLICT(organization_id, source_system, source_record_id) DO UPDATE SET
    employee_id = excluded.employee_id,
    work_date = excluded.work_date,
    clock_in = excluded.clock_in,
    clock_out = excluded.clock_out,
    hours_total = excluded.hours_total,
    status = excluded.status,
    overtime_approved = excluded.overtime_approved,
    imported_at = CURRENT_TIMESTAMP
"""

UPSERT_TIMESHEET_SQL = """
INSERT INTO timesheets (id, organization_id, source_system, source_record_id, employee_id, work_date, regular_hours, overtime_hours, approval_state, hours_total, status, import_id, imported_at, record_version)
VALUES (:id, :organization_id, 'master_csv', :record_id, :employee_id, :work_date, :hours_total, 0.0, :approval_state, :hours_total, :status, :upload_id, CURRENT_TIMESTAMP, 1)
ON CONFLICT(organization_id, source_system, source_record_id) DO UPDATE SET
    employee_id = excluded.employee_id,
    work_date = excluded.work_date,
    regular_hours = excluded.regular_hours,
    approval_state = excluded.approval_state,
    hours_total = excluded.hours_total,
    status = excluded.status,
    imported_at = CURRENT_TIMESTAMP
"""

UPSERT_EXPENSE_SQL = """
INSERT INTO expense_claims (id, organization_id, source_system, source_record_id, employee_id, claim_date, category, amount, currency, receipt_reference, receipt_attached, approval_state, import_id, imported_at, record_version)
VALUES (:id, :organization_id, 'master_csv', :record_id, :employee_id, :claim_date, :category, :amount, 'USD', :receipt_reference, :receipt_attached, 'approved', :upload_id, CURRENT_TIMESTAMP, 1)
ON CONFLICT(organization_id, source_system, source_record_id) DO UPDATE SET
    employee_id = excluded.employee_id,
    claim_date = excluded.claim_date,
    category = excluded.category,
    amount = excluded.amount,
    receipt_reference = excluded.receipt_reference,
    receipt_attached = excluded.receipt_attached,
    imported_at = CURRENT_TIMESTAMP
"""

UPSERT_LEAVE_SQL = """
INSERT INTO leave (id, organization_id, source_system, source_record_id, employee_id, leave_type, start_date, end_date, days_taken, approval_state, import_id, imported_at, record_version)
VALUES (:id, :organization_id, 'master_csv', :record_id, :employee_id, :leave_type, :start_date, :end_date, :days_taken, :approval_state, :upload_id, CURRENT_TIMESTAMP, 1)
ON CONFLICT(organization_id, source_system, source_record_id) DO UPDATE SET
    employee_id = excluded.employee_id,
    leave_type = excluded.leave_type,
    start_date = excluded.start_date,
    end_date = excluded.end_date,
    days_taken = excluded.days_taken,
    approval_state = excluded.approval_state,
    imported_at = CURRENT_TIMESTAMP
"""

UPSERT_LEAVE_BALANCE_SQL = """
INSERT INTO leave_balances (id, employee_id, leave_type, accrued, taken, remaining, updated_at)
VALUES (:id, :employee_id, :leave_type, :accrued, :taken, :remaining, CURRENT_TIMESTAMP)
ON CONFLICT(id) DO UPDATE SET
    accrued = excluded.accrued,
    taken = excluded.taken,
    remaining = excluded.remaining,
    updated_at = CURRENT_TIMESTAMP
"""

TIME_PATTERN = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")


class MasterImportService:

    @staticmethod
    def validate_and_parse_row(
        row_dict: Dict[str, str],
        row_num: int,
        known_emp_ids: Optional[Set[str]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Validates one row based on the business rules.
        Returns (parsed_dict, None) if valid, or (None, rejection_dict) if invalid.
        """
        record_id = (row_dict.get("record_id") or "").strip()
        if not record_id:
            return None, {
                "row_num": row_num,
                "record_id": "MISSING",
                "reason": "Missing required field: record_id",
                "raw_preview": str(row_dict)[:120],
            }

        record_type = (row_dict.get("record_type") or "").strip().lower()
        if not record_type or record_type not in VALID_RECORD_TYPES:
            return None, {
                "row_num": row_num,
                "record_id": record_id,
                "reason": f"Invalid record_type '{record_type}'. Must be one of: {sorted(list(VALID_RECORD_TYPES))}",
                "raw_preview": str(row_dict)[:120],
            }

        emp_id = (row_dict.get("employee_id") or "").strip()
        emp_name = (row_dict.get("employee_name") or "").strip()
        app_id = (row_dict.get("applicant_id") or "").strip()
        start_d_str = (row_dict.get("start_date") or "").strip()
        end_d_str = (row_dict.get("end_date") or "").strip()
        event_d_str = (row_dict.get("event_date") or "").strip()
        status_str = (row_dict.get("status") or "").strip()
        clock_in_str = (row_dict.get("clock_in") or "").strip()
        clock_out_str = (row_dict.get("clock_out") or "").strip()
        exp_cat = (row_dict.get("expense_category") or row_dict.get("category") or "").strip()
        receipt_att = (row_dict.get("receipt_attached") or "").strip().upper()
        train_prog = (row_dict.get("training_program") or "").strip()

        # Check unknown employee_id for record types referencing employees
        if record_type in ("attendance", "timesheet", "expense", "leave_request", "leave_balance"):
            if not emp_id:
                return None, {
                    "row_num": row_num,
                    "record_id": record_id,
                    "reason": f"{record_type} requires employee_id",
                    "raw_preview": str(row_dict)[:120],
                }
            if known_emp_ids is not None and emp_id not in known_emp_ids:
                return None, {
                    "row_num": row_num,
                    "record_id": record_id,
                    "reason": f"Unknown employee_id '{emp_id}'. No matching employee profile exists.",
                    "raw_preview": str(row_dict)[:120],
                }

        # Per-type validation
        if record_type == "employee_profile":
            if not emp_id:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "employee_profile requires employee_id", "raw_preview": str(row_dict)[:120]}
            if not emp_name:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "employee_profile requires employee_name", "raw_preview": str(row_dict)[:120]}

        elif record_type == "attendance":
            if not event_d_str:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "attendance requires event_date", "raw_preview": str(row_dict)[:120]}
            if clock_in_str and not TIME_PATTERN.match(clock_in_str):
                return None, {"row_num": row_num, "record_id": record_id, "reason": f"clock_in must be HH:MM format, got '{clock_in_str}'", "raw_preview": str(row_dict)[:120]}
            # clock_out: blank is completely valid (missing punch case). If present, validate format
            if clock_out_str and not TIME_PATTERN.match(clock_out_str):
                return None, {"row_num": row_num, "record_id": record_id, "reason": f"clock_out must be HH:MM format, got '{clock_out_str}'", "raw_preview": str(row_dict)[:120]}

        elif record_type == "timesheet":
            if not event_d_str:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "timesheet requires event_date", "raw_preview": str(row_dict)[:120]}
            if not status_str:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "timesheet requires status", "raw_preview": str(row_dict)[:120]}

        elif record_type == "expense":
            if not event_d_str:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "expense requires event_date", "raw_preview": str(row_dict)[:120]}
            if not exp_cat:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "expense requires expense_category", "raw_preview": str(row_dict)[:120]}
            # amount required and numeric
            raw_amt = (row_dict.get("amount") or "").strip()
            if not raw_amt:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "expense requires amount", "raw_preview": str(row_dict)[:120]}
            try:
                amt_val = float(raw_amt)
                if amt_val < 0:
                    return None, {"row_num": row_num, "record_id": record_id, "reason": f"expense amount cannot be negative, got {amt_val}", "raw_preview": str(row_dict)[:120]}
            except ValueError:
                return None, {"row_num": row_num, "record_id": record_id, "reason": f"Invalid numeric amount '{raw_amt}'", "raw_preview": str(row_dict)[:120]}
            if not receipt_att:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "expense requires receipt_attached (Y/N)", "raw_preview": str(row_dict)[:120]}

        elif record_type == "leave_request":
            if not start_d_str or not end_d_str:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "leave_request requires start_date and end_date", "raw_preview": str(row_dict)[:120]}
            if not status_str:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "leave_request requires status", "raw_preview": str(row_dict)[:120]}

        elif record_type == "leave_balance":
            pass

        elif record_type == "training":
            if not emp_id and not emp_name:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "training requires employee_id or employee_name", "raw_preview": str(row_dict)[:120]}
            if not train_prog:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "training requires training_program", "raw_preview": str(row_dict)[:120]}

        elif record_type == "engagement_survey":
            if not emp_id and not emp_name:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "engagement_survey requires employee_id or employee_name", "raw_preview": str(row_dict)[:120]}

        elif record_type == "applicant":
            if not app_id and not emp_name:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "applicant requires applicant_id or employee_name", "raw_preview": str(row_dict)[:120]}

        # Parse and validate dates
        parsed_dates: Dict[str, Optional[date]] = {}
        for f in DATE_FIELDS:
            raw_val = (row_dict.get(f) or "").strip()
            if not raw_val:
                parsed_dates[f] = None
            else:
                try:
                    parsed_dates[f] = datetime.strptime(raw_val, "%Y-%m-%d").date()
                except ValueError:
                    return None, {
                        "row_num": row_num,
                        "record_id": record_id,
                        "reason": f"Invalid date format in '{f}': '{raw_val}' (expected YYYY-MM-DD)",
                        "raw_preview": str(row_dict)[:120],
                    }

        # Check start_date <= end_date
        if parsed_dates.get("start_date") and parsed_dates.get("end_date"):
            if parsed_dates["end_date"] < parsed_dates["start_date"]:
                return None, {
                    "row_num": row_num,
                    "record_id": record_id,
                    "reason": f"end_date ({parsed_dates['end_date']}) cannot be before start_date ({parsed_dates['start_date']})",
                    "raw_preview": str(row_dict)[:120],
                }

        # Parse numeric float fields
        parsed_nums: Dict[str, Optional[float]] = {}
        for f in NUMERIC_FLOAT_FIELDS:
            raw_val = (row_dict.get(f) or "").strip()
            if not raw_val:
                parsed_nums[f] = None
            else:
                try:
                    val = float(raw_val)
                    if f == "hours_total" and (val < 0.0 or val > 24.0):
                        return None, {
                            "row_num": row_num,
                            "record_id": record_id,
                            "reason": f"hours_total must be between 0 and 24, got {val}",
                            "raw_preview": str(row_dict)[:120],
                        }
                    parsed_nums[f] = val
                except ValueError:
                    return None, {
                        "row_num": row_num,
                        "record_id": record_id,
                        "reason": f"Invalid numeric value in '{f}': '{raw_val}'",
                        "raw_preview": str(row_dict)[:120],
                    }

        parsed_ints: Dict[str, Optional[int]] = {}
        for f in NUMERIC_INT_FIELDS:
            raw_val = (row_dict.get(f) or "").strip()
            if not raw_val:
                parsed_ints[f] = None
            else:
                try:
                    parsed_ints[f] = int(float(raw_val))
                except ValueError:
                    return None, {
                        "row_num": row_num,
                        "record_id": record_id,
                        "reason": f"Invalid integer value in '{f}': '{raw_val}'",
                        "raw_preview": str(row_dict)[:120],
                    }

        email_val = (row_dict.get("email") or "").strip() or None
        proj_code = (row_dict.get("project_code") or "").strip() or None
        ot_appr = (row_dict.get("overtime_approved") or "").strip() or None

        record_params = {
            "record_id": record_id,
            "upload_id": None,
            "record_type": record_type,
            "source_file": (row_dict.get("source_file") or "").strip() or None,
            "employee_id": emp_id or None,
            "applicant_id": app_id or None,
            "employee_name": emp_name or None,
            "first_name": (row_dict.get("first_name") or "").strip() or None,
            "last_name": (row_dict.get("last_name") or "").strip() or None,
            "department": (row_dict.get("department") or "").strip() or None,
            "position": (row_dict.get("position") or "").strip() or None,
            "division": (row_dict.get("division") or "").strip() or None,
            "business_unit": (row_dict.get("business_unit") or "").strip() or None,
            "branch_location": (row_dict.get("branch_location") or "").strip() or None,
            "manager": (row_dict.get("manager") or "").strip() or None,
            "employment_type": (row_dict.get("employment_type") or "").strip() or None,
            "gender": (row_dict.get("gender") or "").strip() or None,
            "age": parsed_ints.get("age"),
            "dob": parsed_dates.get("dob"),
            "marital_status": (row_dict.get("marital_status") or "").strip() or None,
            "state": (row_dict.get("state") or "").strip() or None,
            "education": (row_dict.get("education") or "").strip() or None,
            "hire_date": parsed_dates.get("hire_date"),
            "exit_date": parsed_dates.get("exit_date"),
            "employee_status": (row_dict.get("employee_status") or "").strip() or None,
            "performance_score": (row_dict.get("performance_score") or "").strip() or None,
            "performance_rating": (row_dict.get("performance_rating") or "").strip() or None,
            "monthly_income": parsed_nums.get("monthly_income"),
            "years_experience": parsed_nums.get("years_experience"),
            "salary_hike_pct": parsed_nums.get("salary_hike_pct"),
            "event_date": parsed_dates.get("event_date"),
            "start_date": parsed_dates.get("start_date"),
            "end_date": parsed_dates.get("end_date"),
            "applied_date": parsed_dates.get("applied_date"),
            "status": status_str or None,
            "category": (row_dict.get("category") or "").strip() or None,
            "reason": (row_dict.get("reason") or "").strip() or None,
            "days": parsed_nums.get("days"),
            "clock_in": clock_in_str or None,
            "clock_out": clock_out_str or None,
            "hours_total": parsed_nums.get("hours_total"),
            "hours_scheduled": parsed_nums.get("hours_scheduled"),
            "break_minutes": parsed_nums.get("break_minutes"),
            "leave_entitlement": parsed_nums.get("leave_entitlement"),
            "leave_taken_so_far": parsed_nums.get("leave_taken_so_far"),
            "leave_remaining": parsed_nums.get("leave_remaining"),
            "engagement_score": parsed_nums.get("engagement_score"),
            "satisfaction_score": parsed_nums.get("satisfaction_score"),
            "work_life_balance_score": parsed_nums.get("work_life_balance_score"),
            "training_program": train_prog or None,
            "training_outcome": (row_dict.get("training_outcome") or "").strip() or None,
            "trainer": (row_dict.get("trainer") or "").strip() or None,
            "training_location": (row_dict.get("training_location") or "").strip() or None,
            "training_cost": parsed_nums.get("training_cost"),
            "desired_salary": parsed_nums.get("desired_salary"),
            "country": (row_dict.get("country") or "").strip() or None,
            "email": email_val,
            "project_code": proj_code,
            "amount": parsed_nums.get("amount"),
            "expense_category": exp_cat or None,
            "receipt_attached": receipt_att or None,
            "overtime_approved": ot_appr,
        }

        return record_params, None

    @classmethod
    def process_upload_task(
        cls,
        upload_id: str,
        file_path: str,
        actor_id: str,
        actor_org: str,
        actor_role: str,
        db: Optional[Session] = None,
    ):
        """
        Background task:
        1. Pre-scans employee profiles to discover valid employee IDs.
        2. Streams CSV in chunks, validates every row, performs bulk UPSERT into master_hr_records.
        3. Maps validated rows into operational audit tables (employees, attendance, timesheets,
           expense_claims, leave, leave_balances).
        4. Reconciles user accounts with employees (e.g. alice@company.com -> EMP0001).
        5. Triggers background evaluation of the rules engine across all employees.
        """
        start_time = time.time()
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        rejected_file_path = Path(file_path).parent / f"rejected_{upload_id}.csv"

        try:
            upload = db.query(MasterUpload).filter(MasterUpload.id == upload_id).first()
            if not upload:
                logger.error("MasterUpload %s not found in DB", upload_id)
                return

            upload.status = "processing"
            db.commit()

            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                upload.status = "failed"
                upload.error_message = "Uploaded file is empty (0 bytes)."
                db.commit()
                return

            # Open file to detect delimiter and headers
            with open(file_path, "r", encoding="utf-8-sig", newline="", errors="replace") as f:
                sample = f.read(4096)
                f.seek(0)
                delimiter = ","
                if "\t" in sample and sample.count("\t") > sample.count(","):
                    delimiter = "\t"

                reader = csv.reader(f, delimiter=delimiter)
                try:
                    raw_header = next(reader)
                except StopIteration:
                    upload.status = "failed"
                    upload.error_message = "CSV file has no header row."
                    db.commit()
                    return

                header_map = {}
                for idx, col in enumerate(raw_header):
                    norm_col = col.strip().lower().replace(" ", "_")
                    header_map[norm_col] = idx

                # Check essential header columns
                missing_essential = []
                for essential in ["record_id", "record_type"]:
                    if essential not in header_map:
                        missing_essential.append(essential)

                if missing_essential:
                    upload.status = "failed"
                    upload.error_message = f"Missing required column(s): {', '.join(missing_essential)}."
                    db.commit()
                    return

                stages = {
                    "uploaded": {
                        "status": "done",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "filename": upload.filename,
                    },
                    "validated": {
                        "status": "in_progress",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "mapped": {"status": "pending"},
                    "evaluated": {"status": "pending"},
                    "dashboards_updated": {"status": "pending"},
                }
                upload.pipeline_stages = stages
                db.commit()

                # Ensure source_imports record exists for foreign key constraints
                db.execute(text("""
                    INSERT OR IGNORE INTO source_imports (import_id, organization_id, source_system, covered_period, status, completeness_flag, imported_at)
                    VALUES (:import_id, :organization_id, 'master_csv', 'ALL', 'completed', 1, CURRENT_TIMESTAMP)
                """), {"import_id": upload_id, "organization_id": actor_org})
                db.commit()

                # Pre-scan file to collect employee_ids defined in employee_profile rows
                known_emp_ids = set(r[0] for r in db.query(Employee.employee_id).all())
                f.seek(0)
                scan_reader = csv.reader(f, delimiter=delimiter)
                next(scan_reader, None)  # skip header
                rec_type_idx = header_map.get("record_type")
                emp_id_idx = header_map.get("employee_id")
                for scan_row in scan_reader:
                    if rec_type_idx is not None and rec_type_idx < len(scan_row):
                        if scan_row[rec_type_idx].strip().lower() == "employee_profile":
                            if emp_id_idx is not None and emp_id_idx < len(scan_row):
                                eid = scan_row[emp_id_idx].strip()
                                if eid:
                                    known_emp_ids.add(eid)

                # Reset reader to row 2 for ingestion
                f.seek(0)
                reader = csv.reader(f, delimiter=delimiter)
                next(reader)

                total_rows = 0
                accepted_rows = 0
                rejected_rows = 0
                mapped_counts = {
                    "employees": 0,
                    "attendance": 0,
                    "timesheets": 0,
                    "expenses": 0,
                    "leave": 0,
                    "leave_balances": 0,
                }

                batch_params: List[Dict[str, Any]] = []
                batch_employees: List[Dict[str, Any]] = []
                batch_attendance: List[Dict[str, Any]] = []
                batch_timesheets: List[Dict[str, Any]] = []
                batch_expenses: List[Dict[str, Any]] = []
                batch_leaves: List[Dict[str, Any]] = []
                batch_leave_balances: List[Dict[str, Any]] = []
                rejected_details: List[Dict[str, Any]] = []
                BATCH_SIZE = 5000

                with open(rejected_file_path, "w", encoding="utf-8", newline="") as rej_f:
                    rej_writer = csv.writer(rej_f)
                    rej_writer.writerow(["row_num", "record_id", "reason", "raw_preview"])

                    for row_idx, row in enumerate(reader, start=2):
                        total_rows += 1

                        row_dict = {}
                        for col_name, col_idx in header_map.items():
                            if col_idx < len(row):
                                row_dict[col_name] = row[col_idx]
                            else:
                                row_dict[col_name] = ""

                        parsed, rejection = cls.validate_and_parse_row(row_dict, row_idx, known_emp_ids)

                        if rejection:
                            rejected_rows += 1
                            rej_writer.writerow([
                                rejection["row_num"],
                                rejection["record_id"],
                                rejection["reason"],
                                rejection["raw_preview"]
                            ])
                            if len(rejected_details) < 5000:
                                rejected_details.append(rejection)
                        else:
                            parsed["upload_id"] = upload_id
                            batch_params.append(parsed)
                            accepted_rows += 1

                            # Prepare operational table mappings
                            rec_type = parsed["record_type"]
                            rec_id = parsed["record_id"]
                            e_id = parsed["employee_id"]

                            if rec_type == "employee_profile":
                                email_val = parsed["email"]
                                if not email_val:
                                    fn = parsed["first_name"] or "emp"
                                    ln = parsed["last_name"] or e_id
                                    email_val = f"{fn.lower().strip()}.{ln.lower().strip()}@company.com"
                                is_act = (parsed["employee_status"] != "Terminated")
                                batch_employees.append({
                                    "employee_id": e_id,
                                    "organization_id": actor_org,
                                    "email": email_val.strip().lower(),
                                    "full_name": parsed["employee_name"] or f"Employee {e_id}",
                                    "manager": parsed["manager"],
                                    "hire_date": parsed["hire_date"] or date(2025, 1, 1),
                                    "termination_date": parsed["exit_date"],
                                    "is_active": is_act,
                                })

                            elif rec_type == "attendance":
                                ev_date = parsed["event_date"]
                                cin_dt = None
                                cout_dt = None
                                if parsed["clock_in"] and ev_date:
                                    try:
                                        p = parsed["clock_in"].split(":")
                                        cin_dt = datetime.combine(ev_date, dtime(int(p[0]), int(p[1]))).isoformat()
                                    except Exception:
                                        pass
                                if parsed["clock_out"] and ev_date:
                                    try:
                                        p = parsed["clock_out"].split(":")
                                        cout_dt = datetime.combine(ev_date, dtime(int(p[0]), int(p[1]))).isoformat()
                                    except Exception:
                                        pass

                                batch_attendance.append({
                                    "id": f"ATT_{rec_id}",
                                    "organization_id": actor_org,
                                    "record_id": rec_id,
                                    "employee_id": e_id,
                                    "work_date": ev_date,
                                    "clock_in": cin_dt,
                                    "clock_out": cout_dt,
                                    "hours_total": parsed["hours_total"],
                                    "status": parsed["status"] or "Present",
                                    "overtime_approved": parsed["overtime_approved"] or "N",
                                    "upload_id": upload_id,
                                })

                            elif rec_type == "timesheet":
                                st_raw = parsed["status"] or "Approved"
                                appr_state = "pending" if st_raw.lower() in ("unapproved", "pending") else "approved"
                                batch_timesheets.append({
                                    "id": f"TS_{rec_id}",
                                    "organization_id": actor_org,
                                    "record_id": rec_id,
                                    "employee_id": e_id,
                                    "work_date": parsed["event_date"],
                                    "hours_total": parsed["hours_total"] or 8.0,
                                    "status": st_raw,
                                    "approval_state": appr_state,
                                    "upload_id": upload_id,
                                })

                            elif rec_type == "expense":
                                rec_att = parsed["receipt_attached"] or "N"
                                rec_ref = None
                                batch_expenses.append({
                                    "id": f"EXP_{rec_id}",
                                    "organization_id": actor_org,
                                    "record_id": rec_id,
                                    "employee_id": e_id,
                                    "claim_date": parsed["event_date"],
                                    "category": parsed["expense_category"] or parsed["category"] or "General",
                                    "amount": parsed["amount"] or 0.0,
                                    "receipt_reference": rec_ref,
                                    "receipt_attached": rec_att,
                                    "upload_id": upload_id,
                                })

                            elif rec_type == "leave_request":
                                batch_leaves.append({
                                    "id": f"LV_{rec_id}",
                                    "organization_id": actor_org,
                                    "record_id": rec_id,
                                    "employee_id": e_id,
                                    "leave_type": parsed["category"] or "Annual",
                                    "start_date": parsed["start_date"],
                                    "end_date": parsed["end_date"],
                                    "days_taken": parsed["days"] or 1.0,
                                    "approval_state": parsed["status"] or "Approved",
                                    "upload_id": upload_id,
                                })

                            elif rec_type == "leave_balance":
                                ltype = parsed["category"] or "Annual"
                                batch_leave_balances.append({
                                    "id": f"LB_{e_id}_{ltype.lower().replace(' ', '_')}",
                                    "employee_id": e_id,
                                    "leave_type": ltype,
                                    "accrued": parsed["leave_entitlement"] or 12.0,
                                    "taken": parsed["leave_taken_so_far"] or 0.0,
                                    "remaining": parsed["leave_remaining"] or 12.0,
                                })

                        # Execute batch insert every BATCH_SIZE rows
                        if len(batch_params) >= BATCH_SIZE:
                            db.execute(text(UPSERT_SQL), batch_params)
                            if batch_employees:
                                mapped_counts["employees"] += len(batch_employees)
                                db.execute(text(UPSERT_EMPLOYEE_SQL), batch_employees)
                                batch_employees.clear()
                            if batch_attendance:
                                mapped_counts["attendance"] += len(batch_attendance)
                                db.execute(text(UPSERT_ATTENDANCE_SQL), batch_attendance)
                                batch_attendance.clear()
                            if batch_timesheets:
                                mapped_counts["timesheets"] += len(batch_timesheets)
                                db.execute(text(UPSERT_TIMESHEET_SQL), batch_timesheets)
                                batch_timesheets.clear()
                            if batch_expenses:
                                mapped_counts["expenses"] += len(batch_expenses)
                                db.execute(text(UPSERT_EXPENSE_SQL), batch_expenses)
                                batch_expenses.clear()
                            if batch_leaves:
                                mapped_counts["leave"] += len(batch_leaves)
                                db.execute(text(UPSERT_LEAVE_SQL), batch_leaves)
                                batch_leaves.clear()
                            if batch_leave_balances:
                                mapped_counts["leave_balances"] += len(batch_leave_balances)
                                db.execute(text(UPSERT_LEAVE_BALANCE_SQL), batch_leave_balances)
                                batch_leave_balances.clear()

                            db.commit()
                            batch_params.clear()

                            upload.total_rows = total_rows
                            upload.accepted_rows = accepted_rows
                            upload.rejected_rows = rejected_rows
                            upload.duration_seconds = round(time.time() - start_time, 2)
                            db.commit()

                    # Flush remaining rows
                    if batch_params:
                        db.execute(text(UPSERT_SQL), batch_params)
                        batch_params.clear()
                    if batch_employees:
                        mapped_counts["employees"] += len(batch_employees)
                        db.execute(text(UPSERT_EMPLOYEE_SQL), batch_employees)
                        batch_employees.clear()
                    if batch_attendance:
                        mapped_counts["attendance"] += len(batch_attendance)
                        db.execute(text(UPSERT_ATTENDANCE_SQL), batch_attendance)
                        batch_attendance.clear()
                    if batch_timesheets:
                        mapped_counts["timesheets"] += len(batch_timesheets)
                        db.execute(text(UPSERT_TIMESHEET_SQL), batch_timesheets)
                        batch_timesheets.clear()
                    if batch_expenses:
                        mapped_counts["expenses"] += len(batch_expenses)
                        db.execute(text(UPSERT_EXPENSE_SQL), batch_expenses)
                        batch_expenses.clear()
                    if batch_leaves:
                        mapped_counts["leave"] += len(batch_leaves)
                        db.execute(text(UPSERT_LEAVE_SQL), batch_leaves)
                        batch_leaves.clear()
                    if batch_leave_balances:
                        mapped_counts["leave_balances"] += len(batch_leave_balances)
                        db.execute(text(UPSERT_LEAVE_BALANCE_SQL), batch_leave_balances)
                        batch_leave_balances.clear()

                    db.commit()

                # Pipeline Stage 2 & 3 complete
                stages["validated"] = {
                    "status": "done",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "total_rows": total_rows,
                    "accepted_rows": accepted_rows,
                    "rejected_rows": rejected_rows,
                }
                stages["mapped"] = {
                    "status": "done",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tables": mapped_counts,
                }
                stages["evaluated"] = {
                    "status": "in_progress",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                upload.pipeline_stages = stages
                db.commit()

                # Ensure source_imports record exists for foreign key constraints
                db.execute(text("""
                    INSERT OR IGNORE INTO source_imports (import_id, organization_id, source_system, covered_period, status, completeness_flag, imported_at)
                    VALUES (:import_id, :organization_id, 'master_csv', 'ALL', 'completed', 1, CURRENT_TIMESTAMP)
                """), {"import_id": upload_id, "organization_id": actor_org})
                db.commit()

            # Link user accounts to employees
            try:
                cls.reconcile_users_with_employees(db)
            except Exception as link_err:
                logger.warning("Error reconciling user accounts with employees: %s", link_err)
                db.rollback()

            duration = time.time() - start_time
            upload.status = "done"
            upload.total_rows = total_rows
            upload.accepted_rows = accepted_rows
            upload.rejected_rows = rejected_rows
            upload.duration_seconds = round(duration, 2)
            upload.rejected_details = rejected_details
            db.commit()

            # Append to Audit Ledger
            try:
                db.add(AuditEvent(
                    organization_id=actor_org,
                    actor_id=actor_id,
                    actor_role=actor_role,
                    action_type="MASTER_CSV_UPLOAD",
                    target_entity="master_uploads",
                    target_id=upload_id,
                    payload_diff={
                        "filename": upload.filename,
                        "sha256": upload.sha256,
                        "total_rows": total_rows,
                        "accepted_rows": accepted_rows,
                        "rejected_rows": rejected_rows,
                        "duration_seconds": round(duration, 2),
                    }
                ))
                db.commit()
            except Exception as audit_err:
                logger.warning("Audit event recording failed for upload %s: %s", upload_id, audit_err)

            # Trigger background evaluation of rules engine
            eval_res = {}
            try:
                engine = AuditEngine()
                eval_res = engine.evaluate_all_employees(db, trigger_source="import_completed")
                logger.info("Evaluation completed after import: %s", eval_res)
            except Exception as eval_err:
                logger.warning("Rules evaluation failed after import: %s", eval_err)

            # Complete stages 4 and 5
            stages["evaluated"] = {
                "status": "done",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "eval_run_id": eval_res.get("run_batch_id"),
                "periods": eval_res.get("periods", []),
                "total_runs": eval_res.get("total_runs", 0),
                "total_blocking": eval_res.get("total_blocking", 0),
                "total_warning": eval_res.get("total_warning", 0),
            }
            stages["dashboards_updated"] = {
                "status": "done",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            upload.pipeline_stages = stages
            db.commit()

            try:
                from app.api.audit import invalidate_audit_cache
                invalidate_audit_cache()
            except Exception:
                pass

        except Exception as e:
            logger.exception("Error processing master upload %s: %s", upload_id, e)
            try:
                upload = db.query(MasterUpload).filter(MasterUpload.id == upload_id).first()
                if upload:
                    upload.status = "failed"
                    upload.error_message = str(e)
                    if upload.pipeline_stages:
                        st = dict(upload.pipeline_stages)
                        for s_name in ["validated", "mapped", "evaluated", "dashboards_updated"]:
                            if st.get(s_name, {}).get("status") == "in_progress":
                                st[s_name]["status"] = "failed"
                                st[s_name]["error"] = str(e)
                                break
                        upload.pipeline_stages = st
                    db.commit()
            except Exception:
                pass
        finally:
            if close_db:
                db.close()
            if "temp_uploads" in str(file_path) and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    @classmethod
    def reconcile_users_with_employees(cls, db: Session):
        """
        Matches user accounts (UserAuth) to employee profiles by email.
        Supports company.com and example.com alias variations.
        (alice@company.com -> EMP0001, bob@company.com -> EMP0002,
         carol@company.com -> EMP0003, irene@company.com -> EMP0004).
        """
        users = db.query(UserAuth).all()
        for u in users:
            clean_email = u.email.strip().lower()
            candidate_emails = [clean_email]

            if "@company.com" in clean_email:
                pfx = clean_email.split("@")[0]
                candidate_emails.append(f"{pfx}@example.com")
                if pfx == "bob":
                    candidate_emails.append("bob.manager@example.com")
                elif pfx == "carol":
                    candidate_emails.append("carol.hr@example.com")
                elif pfx == "irene":
                    candidate_emails.append("irene.ic@example.com")
            elif "@example.com" in clean_email:
                pfx = clean_email.split("@")[0].replace(".manager", "").replace(".hr", "").replace(".ic", "")
                candidate_emails.append(f"{pfx}@company.com")

            # Check if any employee matches
            emp = db.query(Employee).filter(
                or_(*[func.lower(Employee.email) == ce.lower() for ce in candidate_emails])
            ).first()

            if emp and u.employee_id != emp.employee_id:
                u.employee_id = emp.employee_id
                db.commit()

        # Ensure core personas exist with valid credentials and linked IDs
        core_demo_personas = [
            ("alice@company.com", "EMP0001", "Alice Employee", "employee"),
            ("bob@company.com", "EMP0002", "Bob Manager", "manager"),
            ("carol@company.com", "EMP0003", "Carol HR Admin", "hr_admin"),
            ("irene@company.com", "EMP0004", "Irene IC Member", "ic_member"),
        ]
        from app.auth.service import hash_password
        default_hash = hash_password("Password123!")

        for c_email, c_eid, c_name, c_role in core_demo_personas:
            u = db.query(UserAuth).filter(func.lower(UserAuth.email) == c_email).first()
            emp = db.query(Employee).filter(
                or_(
                    func.lower(Employee.email) == c_email,
                    Employee.employee_id == c_eid
                )
            ).first()
            resolved_eid = emp.employee_id if emp else c_eid

            if not u:
                u = UserAuth(
                    employee_id=resolved_eid,
                    organization_id=emp.organization_id if emp else "ORG_DEMO_01",
                    email=c_email,
                    password_hash=default_hash,
                    role=c_role,
                    is_verified=True,
                )
                db.add(u)
            else:
                if u.employee_id != resolved_eid:
                    u.employee_id = resolved_eid
                if not u.password_hash:
                    u.password_hash = default_hash
                u.role = c_role
                u.is_verified = True
        db.commit()
