import csv
import io
import hashlib
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.hr import (
    Employee,
    SourceImport,
    Attendance,
    Leave,
    Timesheet,
    ExpenseClaim,
    Document,
    AuditEvent,
)
from app.models.base import generate_uuid


def compute_natural_row_hash(source_system: str, row_values: List[str]) -> str:
    """
    Deterministic fallback strategy when source CSV lacks stable source_record_id:
    Computes SHA256 of composite immutable values.
    Equal employee/date alone does NOT prove duplication (e.g. multiple distinct shifts or split punches).
    """
    normalized = "|".join([source_system] + [str(v).strip() for v in row_values])
    return f"GEN_{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]}"


def parse_iso_datetime(val: Optional[str], base_date: Optional[date] = None) -> Optional[datetime]:
    if not val or not str(val).strip():
        return None
    val_str = str(val).strip()

    # If only time is provided (e.g. "17:30" or "17:30:00") and base_date is available
    if base_date:
        for t_fmt in ("%H:%M:%S", "%H:%M"):
            try:
                t_obj = datetime.strptime(val_str, t_fmt).time()
                return datetime.combine(base_date, t_obj).replace(tzinfo=timezone.utc)
            except ValueError:
                pass

    try:
        dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(val_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Invalid datetime format: '{val_str}'")


def parse_iso_date(val: Optional[str]) -> date:
    if not val or not str(val).strip():
        raise ValueError("Date value is required.")
    val_str = str(val).strip()
    return date.fromisoformat(val_str)


class IngestionService:
    @staticmethod
    def ingest_csv(
        db: Session,
        organization_id: str,
        source_system: str,
        covered_period: str,
        file_content: str,
        actor_id: str,
        raw_file_uri: Optional[str] = None,
        is_complete_feed: bool = True,
    ) -> Dict[str, Any]:
        """
        Parses, validates and loads CSV records with strict source provenance,
        foreign key verification, and duplicate replay prevention.
        """
        import_record = SourceImport(
            import_id=generate_uuid(),
            organization_id=organization_id,
            source_system=source_system,
            covered_period=covered_period,
            status="processing",
            completeness_flag=is_complete_feed,
            source_updated_at=datetime.now(timezone.utc),
            imported_at=datetime.now(timezone.utc),
            validation_errors=[],
            raw_file_uri=raw_file_uri or f"memory://{source_system}_{covered_period}.csv",
        )
        db.add(import_record)
        db.flush()

        reader = csv.DictReader(io.StringIO(file_content.strip()))
        if not reader.fieldnames:
            import_record.status = "failed"
            import_record.completeness_flag = False
            import_record.validation_errors = ["Empty file or missing CSV header."]
            db.commit()
            return {
                "import_id": import_record.import_id,
                "status": "failed",
                "completeness_flag": False,
                "total_rows": 0,
                "inserted_rows": 0,
                "skipped_duplicates": 0,
                "errors": import_record.validation_errors,
            }

        reader.fieldnames = [f.strip() for f in reader.fieldnames]

        active_employees = {
            e.employee_id: e for e in db.query(Employee).filter(Employee.organization_id == organization_id).all()
        }

        total_rows = 0
        inserted_rows = 0
        skipped_duplicates = 0
        errors = []

        for row_idx, row in enumerate(reader, start=1):
            total_rows += 1
            cleaned_row = {k.strip(): (v.strip() if v else "") for k, v in row.items() if k}

            try:
                emp_id = cleaned_row.get("employee_id")
                if not emp_id:
                    raise ValueError(f"Row {row_idx}: Missing required 'employee_id'.")
                if emp_id not in active_employees:
                    raise ValueError(f"Row {row_idx}: Employee '{emp_id}' does not exist in organization '{organization_id}'.")

                src_rec_id = cleaned_row.get("source_record_id")
                if not src_rec_id:
                    src_rec_id = compute_natural_row_hash(source_system, list(cleaned_row.values()))

                raw_evidence_ref = f"{import_record.raw_file_uri}#line={row_idx}"

                with db.begin_nested():
                    if source_system == "attendance":
                        inserted = IngestionService._process_attendance_row(
                            db, organization_id, import_record.import_id, src_rec_id, emp_id,
                            cleaned_row, raw_evidence_ref, active_employees[emp_id].timezone
                        )
                    elif source_system == "leave":
                        inserted = IngestionService._process_leave_row(
                            db, organization_id, import_record.import_id, src_rec_id, emp_id,
                            cleaned_row, raw_evidence_ref
                        )
                    elif source_system == "timesheets":
                        inserted = IngestionService._process_timesheet_row(
                            db, organization_id, import_record.import_id, src_rec_id, emp_id,
                            cleaned_row, raw_evidence_ref
                        )
                    elif source_system == "expense_claims":
                        inserted = IngestionService._process_expense_row(
                            db, organization_id, import_record.import_id, src_rec_id, emp_id,
                            cleaned_row, raw_evidence_ref
                        )
                    elif source_system == "documents":
                        inserted = IngestionService._process_document_row(
                            db, organization_id, import_record.import_id, src_rec_id, emp_id,
                            cleaned_row, raw_evidence_ref
                        )
                    else:
                        raise ValueError(f"Unsupported source_system: '{source_system}'")

                if inserted:
                    inserted_rows += 1
                else:
                    skipped_duplicates += 1

            except IntegrityError:
                # Caught duplicate replay at DB constraint level
                skipped_duplicates += 1
            except Exception as e:
                errors.append(str(e))

        # Determine final status
        if errors and inserted_rows == 0:
            import_record.status = "failed"
            import_record.completeness_flag = False
        elif errors and inserted_rows > 0:
            import_record.status = "partial"
            import_record.completeness_flag = False
        else:
            import_record.status = "completed"

        import_record.validation_errors = errors
        db.add(import_record)

        db.add(AuditEvent(
            organization_id=organization_id,
            actor_id=actor_id,
            actor_role="service" if actor_id.startswith("service:") else "hr_admin",
            action_type="IMPORT_CSV",
            target_entity="source_imports",
            target_id=import_record.import_id,
            payload_diff={
                "source_system": source_system,
                "period": covered_period,
                "total_rows": total_rows,
                "inserted_rows": inserted_rows,
                "skipped_duplicates": skipped_duplicates,
                "status": import_record.status,
            }
        ))

        db.commit()

        return {
            "import_id": import_record.import_id,
            "status": import_record.status,
            "completeness_flag": import_record.completeness_flag,
            "total_rows": total_rows,
            "inserted_rows": inserted_rows,
            "skipped_duplicates": skipped_duplicates,
            "errors": errors,
        }

    @staticmethod
    def _process_attendance_row(
        db: Session, org_id: str, import_id: str, src_rec_id: str, emp_id: str,
        row: Dict[str, str], raw_ref: str, default_tz: str
    ) -> bool:
        existing = db.query(Attendance).filter(
            Attendance.organization_id == org_id,
            Attendance.source_system == "attendance",
            Attendance.source_record_id == src_rec_id,
        ).first()
        if existing:
            return False  # Skipped duplicate

        work_date = parse_iso_date(row.get("work_date"))
        clock_in = parse_iso_datetime(row.get("clock_in"))
        clock_out = parse_iso_datetime(row.get("clock_out"))
        tz = row.get("timezone") or default_tz

        record = Attendance(
            id=generate_uuid(),
            organization_id=org_id,
            source_system="attendance",
            source_record_id=src_rec_id,
            source_updated_at=datetime.now(timezone.utc),
            import_id=import_id,
            record_version=1,
            raw_evidence_reference=raw_ref,
            employee_id=emp_id,
            work_date=work_date,
            clock_in=clock_in,
            clock_out=clock_out,
            timezone=tz,
            shift_id=row.get("shift_id", "STANDARD_DAY"),
            approval_state=row.get("approval_state", "approved"),
        )
        db.add(record)
        db.flush()
        return True

    @staticmethod
    def _process_leave_row(
        db: Session, org_id: str, import_id: str, src_rec_id: str, emp_id: str,
        row: Dict[str, str], raw_ref: str
    ) -> bool:
        existing = db.query(Leave).filter(
            Leave.organization_id == org_id,
            Leave.source_system == "leave",
            Leave.source_record_id == src_rec_id,
        ).first()
        if existing:
            return False

        record = Leave(
            id=generate_uuid(),
            organization_id=org_id,
            source_system="leave",
            source_record_id=src_rec_id,
            source_updated_at=datetime.now(timezone.utc),
            import_id=import_id,
            record_version=1,
            raw_evidence_reference=raw_ref,
            employee_id=emp_id,
            leave_type=row.get("leave_type", "annual"),
            start_date=parse_iso_date(row.get("start_date")),
            end_date=parse_iso_date(row.get("end_date")),
            days_taken=float(row.get("days_taken") or 1.0),
            approval_state=row.get("approval_state", "approved"),
        )
        db.add(record)
        db.flush()
        return True

    @staticmethod
    def _process_timesheet_row(
        db: Session, org_id: str, import_id: str, src_rec_id: str, emp_id: str,
        row: Dict[str, str], raw_ref: str
    ) -> bool:
        existing = db.query(Timesheet).filter(
            Timesheet.organization_id == org_id,
            Timesheet.source_system == "timesheets",
            Timesheet.source_record_id == src_rec_id,
        ).first()
        if existing:
            return False

        record = Timesheet(
            id=generate_uuid(),
            organization_id=org_id,
            source_system="timesheets",
            source_record_id=src_rec_id,
            source_updated_at=datetime.now(timezone.utc),
            import_id=import_id,
            record_version=1,
            raw_evidence_reference=raw_ref,
            employee_id=emp_id,
            work_date=parse_iso_date(row.get("work_date")),
            regular_hours=float(row.get("regular_hours") or 8.0),
            overtime_hours=float(row.get("overtime_hours") or 0.0),
            approval_state=row.get("approval_state", "approved"),
        )
        db.add(record)
        db.flush()
        return True

    @staticmethod
    def _process_expense_row(
        db: Session, org_id: str, import_id: str, src_rec_id: str, emp_id: str,
        row: Dict[str, str], raw_ref: str
    ) -> bool:
        existing = db.query(ExpenseClaim).filter(
            ExpenseClaim.organization_id == org_id,
            ExpenseClaim.source_system == "expense_claims",
            ExpenseClaim.source_record_id == src_rec_id,
        ).first()
        if existing:
            return False

        record = ExpenseClaim(
            id=generate_uuid(),
            organization_id=org_id,
            source_system="expense_claims",
            source_record_id=src_rec_id,
            source_updated_at=datetime.now(timezone.utc),
            import_id=import_id,
            record_version=1,
            raw_evidence_reference=raw_ref,
            employee_id=emp_id,
            claim_date=parse_iso_date(row.get("claim_date")),
            category=row.get("category", "General"),
            amount=float(row.get("amount") or 0.0),
            currency=row.get("currency", "USD"),
            receipt_reference=row.get("receipt_reference") or None,
            merchant_name=row.get("merchant_name") or None,
            approval_state=row.get("approval_state", "pending"),
        )
        db.add(record)
        db.flush()
        return True

    @staticmethod
    def _process_document_row(
        db: Session, org_id: str, import_id: str, src_rec_id: str, emp_id: str,
        row: Dict[str, str], raw_ref: str
    ) -> bool:
        existing = db.query(Document).filter(
            Document.organization_id == org_id,
            Document.source_system == "documents",
            Document.source_record_id == src_rec_id,
        ).first()
        if existing:
            return False

        issue_date = parse_iso_date(row.get("issue_date")) if row.get("issue_date") else None
        expiry_date = parse_iso_date(row.get("expiry_date")) if row.get("expiry_date") else None

        record = Document(
            id=generate_uuid(),
            organization_id=org_id,
            source_system="documents",
            source_record_id=src_rec_id,
            source_updated_at=datetime.now(timezone.utc),
            import_id=import_id,
            record_version=1,
            raw_evidence_reference=raw_ref,
            employee_id=emp_id,
            document_type=row.get("document_type", "other"),
            document_reference=row.get("document_reference", "DOC-REF"),
            issue_date=issue_date,
            expiry_date=expiry_date,
            verification_status=row.get("verification_status", "verified"),
        )
        db.add(record)
        db.flush()
        return True
