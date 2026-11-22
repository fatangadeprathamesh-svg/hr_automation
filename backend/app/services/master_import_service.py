import os
import csv
import time
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.master_hr import MasterUpload, MasterHRRecord
from app.models.hr import AuditEvent

logger = logging.getLogger(__name__)

# Master 55 columns in exact specification order
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
    "trainer", "training_location", "training_cost", "desired_salary", "country"
]

DATE_FIELDS = {
    "dob", "hire_date", "exit_date", "event_date", "start_date", "end_date", "applied_date"
}

NUMERIC_FLOAT_FIELDS = {
    "monthly_income", "years_experience", "salary_hike_pct", "days",
    "hours_total", "hours_scheduled", "break_minutes", "leave_entitlement",
    "leave_taken_so_far", "leave_remaining", "engagement_score",
    "satisfaction_score", "work_life_balance_score", "training_cost", "desired_salary"
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
    desired_salary, country, created_at, updated_at
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
    :desired_salary, :country, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
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
    updated_at = CURRENT_TIMESTAMP
"""


class MasterImportService:

    @staticmethod
    def validate_and_parse_row(
        row_dict: Dict[str, str], row_num: int
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

        # Required fields by record_type
        emp_id = (row_dict.get("employee_id") or "").strip()
        emp_name = (row_dict.get("employee_name") or "").strip()
        app_id = (row_dict.get("applicant_id") or "").strip()
        start_d_str = (row_dict.get("start_date") or "").strip()
        end_d_str = (row_dict.get("end_date") or "").strip()
        event_d_str = (row_dict.get("event_date") or "").strip()
        train_prog = (row_dict.get("training_program") or "").strip()

        if record_type == "leave_request":
            if not emp_id:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "leave_request requires employee_id", "raw_preview": str(row_dict)[:120]}
            if not start_d_str or not end_d_str:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "leave_request requires both start_date and end_date", "raw_preview": str(row_dict)[:120]}

        elif record_type == "timesheet":
            # Timesheet rows have NO employee_id (name only). This is intentional: never reject them for that reason.
            if not emp_name:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "timesheet requires employee_name", "raw_preview": str(row_dict)[:120]}
            if not event_d_str:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "timesheet requires event_date", "raw_preview": str(row_dict)[:120]}

        elif record_type == "employee_profile":
            if not emp_name:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "employee_profile requires employee_name", "raw_preview": str(row_dict)[:120]}

        elif record_type == "leave_balance":
            if not emp_id:
                return None, {"row_num": row_num, "record_id": record_id, "reason": "leave_balance requires employee_id", "raw_preview": str(row_dict)[:120]}

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

        # Check end_date not before start_date
        if parsed_dates.get("start_date") and parsed_dates.get("end_date"):
            if parsed_dates["end_date"] < parsed_dates["start_date"]:
                return None, {
                    "row_num": row_num,
                    "record_id": record_id,
                    "reason": f"end_date ({parsed_dates['end_date']}) cannot be before start_date ({parsed_dates['start_date']})",
                    "raw_preview": str(row_dict)[:120],
                }

        # Parse and validate numeric fields
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

        # Construct parameter record
        record_params = {
            "record_id": record_id,
            "upload_id": None,  # Set by caller
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
            "status": (row_dict.get("status") or "").strip() or None,
            "category": (row_dict.get("category") or "").strip() or None,
            "reason": (row_dict.get("reason") or "").strip() or None,
            "days": parsed_nums.get("days"),
            "clock_in": (row_dict.get("clock_in") or "").strip() or None,
            "clock_out": (row_dict.get("clock_out") or "").strip() or None,
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
    ):
        """
        Background task: streams CSV in chunks of 5,000 rows, validates each row,
        performs bulk UPSERT, collects rejected rows, updates progress live, and
        records audit event. Flat memory consumption.
        """
        start_time = time.time()
        db: Session = SessionLocal()
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

            # Open streaming CSV reader (handles utf-8 and BOM utf-8-sig)
            with open(file_path, "r", encoding="utf-8-sig", newline="", errors="replace") as f:
                # Detect delimiter (default comma)
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

                # Normalize headers: strip quotes, lowercase, whitespace
                header_map = {}
                for idx, col in enumerate(raw_header):
                    norm_col = col.strip().lower().replace(" ", "_")
                    header_map[norm_col] = idx

                # Check required header columns
                missing_essential = []
                for essential in ["record_id", "record_type"]:
                    if essential not in header_map:
                        missing_essential.append(essential)

                unknown_cols = [c for c in header_map.keys() if c not in COLUMNS]

                if missing_essential:
                    upload.status = "failed"
                    err_msg = f"Missing required column(s): {', '.join(missing_essential)}."
                    if unknown_cols:
                        err_msg += f" Unknown column(s) ignored: {', '.join(unknown_cols[:10])}."
                    upload.error_message = err_msg
                    db.commit()
                    return

                total_rows = 0
                accepted_rows = 0
                rejected_rows = 0
                batch_params: List[Dict[str, Any]] = []
                rejected_details: List[Dict[str, Any]] = []
                BATCH_SIZE = 5000

                # Open rejected CSV writer
                with open(rejected_file_path, "w", encoding="utf-8", newline="") as rej_f:
                    rej_writer = csv.writer(rej_f)
                    rej_writer.writerow(["row_num", "record_id", "reason", "raw_preview"])

                    for row_idx, row in enumerate(reader, start=2):
                        total_rows += 1

                        # Build row dictionary from header_map
                        row_dict = {}
                        for col_name, col_idx in header_map.items():
                            if col_idx < len(row):
                                row_dict[col_name] = row[col_idx]
                            else:
                                row_dict[col_name] = ""

                        parsed, rejection = cls.validate_and_parse_row(row_dict, row_idx)

                        if rejection:
                            rejected_rows += 1
                            rej_writer.writerow([
                                rejection["row_num"],
                                rejection["record_id"],
                                rejection["reason"],
                                rejection["raw_preview"]
                            ])
                            # Store first 5000 in memory/DB for immediate JSON display
                            if len(rejected_details) < 5000:
                                rejected_details.append(rejection)
                        else:
                            parsed["upload_id"] = upload_id
                            batch_params.append(parsed)
                            accepted_rows += 1

                        # Execute batch insert every BATCH_SIZE rows
                        if len(batch_params) >= BATCH_SIZE:
                            db.execute(text(UPSERT_SQL), batch_params)
                            db.commit()
                            batch_params.clear()

                            # Update progress in DB so UI live-polls
                            upload.total_rows = total_rows
                            upload.accepted_rows = accepted_rows
                            upload.rejected_rows = rejected_rows
                            upload.duration_seconds = round(time.time() - start_time, 2)
                            db.commit()

                    # Flush remaining rows
                    if batch_params:
                        db.execute(text(UPSERT_SQL), batch_params)
                        db.commit()
                        batch_params.clear()

            duration = time.time() - start_time

            # Update final upload record
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

        except Exception as e:
            logger.exception("Error processing master upload %s: %s", upload_id, e)
            try:
                upload = db.query(MasterUpload).filter(MasterUpload.id == upload_id).first()
                if upload:
                    upload.status = "failed"
                    upload.error_message = str(e)
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()
            # Clean up temporary uploaded source file (keep rejected file for download)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
