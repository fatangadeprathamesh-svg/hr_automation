import os
import csv
import io
import time
from pathlib import Path
from datetime import datetime, date
import pytest
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.master_hr import MasterUpload, MasterHRRecord
from app.models.hr import AuditEvent
from app.services.master_import_service import MasterImportService, COLUMNS
from app.api.master_uploads import (
    get_upload_status,
    get_rejected_rows,
    get_upload_history,
    get_master_records,
    get_master_stats,
)
from app.auth.security import ActorIdentity


def test_row_validation_rules():
    """Unit test individual row validation rules."""
    # 1. Valid employee profile
    row_prof = {
        "record_id": "REC-001",
        "record_type": "employee_profile",
        "employee_id": "EMP001",
        "employee_name": "Alice Wonderland",
        "department": "Engineering",
        "dob": "1990-05-15",
        "monthly_income": "8500.00",
    }
    parsed, rej = MasterImportService.validate_and_parse_row(row_prof, 2)
    assert rej is None
    assert parsed["record_id"] == "REC-001"
    assert parsed["record_type"] == "employee_profile"
    assert parsed["monthly_income"] == 8500.0
    assert parsed["dob"] == date(1990, 5, 15)

    # 2. Valid timesheet with NO employee_id (must NOT be rejected)
    row_ts = {
        "record_id": "REC-002",
        "record_type": "timesheet",
        "employee_name": "Bob Builder",
        "event_date": "2026-10-01",
        "hours_total": "8.5",
        "status": "approved",
    }
    parsed, rej = MasterImportService.validate_and_parse_row(row_ts, 3)
    assert rej is None
    assert parsed["employee_id"] is None
    assert parsed["hours_total"] == 8.5

    # 3. Invalid record_type
    row_bad_type = {
        "record_id": "REC-003",
        "record_type": "unknown_type",
        "employee_name": "Charlie",
    }
    parsed, rej = MasterImportService.validate_and_parse_row(row_bad_type, 4)
    assert parsed is None
    assert "Invalid record_type" in rej["reason"]

    # 4. leave_request with end_date before start_date
    row_bad_leave = {
        "record_id": "REC-004",
        "record_type": "leave_request",
        "employee_id": "EMP002",
        "start_date": "2026-10-15",
        "end_date": "2026-10-10",
        "days": "5.0",
    }
    parsed, rej = MasterImportService.validate_and_parse_row(row_bad_leave, 5)
    assert parsed is None
    assert "cannot be before start_date" in rej["reason"]

    # 5. timesheet with hours_total > 24
    row_bad_hours = {
        "record_id": "REC-005",
        "record_type": "timesheet",
        "employee_name": "David",
        "event_date": "2026-10-02",
        "hours_total": "26.0",
    }
    parsed, rej = MasterImportService.validate_and_parse_row(row_bad_hours, 6)
    assert parsed is None
    assert "hours_total must be between 0 and 24" in rej["reason"]

    # 6. Invalid date format
    row_bad_date = {
        "record_id": "REC-006",
        "record_type": "employee_profile",
        "employee_name": "Eva",
        "hire_date": "10/15/2025",
    }
    parsed, rej = MasterImportService.validate_and_parse_row(row_bad_date, 7)
    assert parsed is None
    assert "Invalid date format" in rej["reason"]

    # 7. Non-numeric in numeric field (currency symbol)
    row_bad_num = {
        "record_id": "REC-007",
        "record_type": "employee_profile",
        "employee_name": "Frank",
        "monthly_income": "$7,500.00",
    }
    parsed, rej = MasterImportService.validate_and_parse_row(row_bad_num, 8)
    assert parsed is None
    assert "Invalid numeric value" in rej["reason"]


def test_sample_csv_upload_and_pipeline(tmp_path):
    """
    Creates a 50-row sample CSV with 45 good rows and 5 bad rows,
    executes background processing, asserts accepted/rejected counts,
    and tests API retrieval, filtering, pagination, and stats.
    """
    csv_file = tmp_path / "sample_master_hr.csv"
    upload_id = "test-upload-uuid-001"
    actor_id = "HR001"
    actor_org = "ORG_DEMO_01"
    actor_role = "hr_admin"

    # Generate 50 rows: 45 good + 5 bad
    rows = []
    # 10 employee_profile (good)
    for i in range(1, 11):
        r = {c: "" for c in COLUMNS}
        r["record_id"] = f"EMP-REC-{i:03d}"
        r["record_type"] = "employee_profile"
        r["employee_id"] = f"EMP{i:03d}"
        r["employee_name"] = f"Employee {i}"
        r["department"] = "Engineering" if i % 2 == 0 else "Sales"
        r["hire_date"] = "2025-01-15"
        r["monthly_income"] = str(5000 + i * 100)
        rows.append(r)

    # 10 leave_request (good)
    for i in range(1, 11):
        r = {c: "" for c in COLUMNS}
        r["record_id"] = f"LV-REC-{i:03d}"
        r["record_type"] = "leave_request"
        r["employee_id"] = f"EMP{i:03d}"
        r["start_date"] = "2026-10-01"
        r["end_date"] = "2026-10-03"
        r["days"] = "2.0"
        r["status"] = "approved"
        rows.append(r)

    # 10 timesheet (good, NO employee_id)
    for i in range(1, 11):
        r = {c: "" for c in COLUMNS}
        r["record_id"] = f"TS-REC-{i:03d}"
        r["record_type"] = "timesheet"
        r["employee_name"] = f"Employee {i}"
        r["event_date"] = "2026-10-05"
        r["hours_total"] = "8.0"
        r["status"] = "approved" if i % 2 == 0 else "pending"
        rows.append(r)

    # 10 training (good)
    for i in range(1, 11):
        r = {c: "" for c in COLUMNS}
        r["record_id"] = f"TRN-REC-{i:03d}"
        r["record_type"] = "training"
        r["employee_id"] = f"EMP{i:03d}"
        r["training_program"] = "Security Awareness 2026"
        r["training_cost"] = "250.00"
        rows.append(r)

    # 5 applicant (good)
    for i in range(1, 6):
        r = {c: "" for c in COLUMNS}
        r["record_id"] = f"APP-REC-{i:03d}"
        r["record_type"] = "applicant"
        r["applicant_id"] = f"APP{i:03d}"
        r["employee_name"] = f"Candidate {i}"
        r["applied_date"] = "2026-09-15"
        rows.append(r)

    # 5 deliberately BAD rows
    # Bad 1: Invalid record type
    b1 = {c: "" for c in COLUMNS}
    b1["record_id"] = "BAD-REC-001"
    b1["record_type"] = "invalid_category"
    b1["employee_name"] = "Bad Type"
    rows.append(b1)

    # Bad 2: leave_request with end_date before start_date
    b2 = {c: "" for c in COLUMNS}
    b2["record_id"] = "BAD-REC-002"
    b2["record_type"] = "leave_request"
    b2["employee_id"] = "EMP001"
    b2["start_date"] = "2026-10-20"
    b2["end_date"] = "2026-10-18"
    b2["days"] = "3.0"
    rows.append(b2)

    # Bad 3: timesheet hours_total > 24
    b3 = {c: "" for c in COLUMNS}
    b3["record_id"] = "BAD-REC-003"
    b3["record_type"] = "timesheet"
    b3["employee_name"] = "Bad Hours"
    b3["event_date"] = "2026-10-06"
    b3["hours_total"] = "28.5"
    rows.append(b3)

    # Bad 4: invalid date format
    b4 = {c: "" for c in COLUMNS}
    b4["record_id"] = "BAD-REC-004"
    b4["record_type"] = "employee_profile"
    b4["employee_name"] = "Bad Date"
    b4["hire_date"] = "2025/01/15"
    rows.append(b4)

    # Bad 5: non-numeric in float field
    b5 = {c: "" for c in COLUMNS}
    b5["record_id"] = "BAD-REC-005"
    b5["record_type"] = "training"
    b5["employee_id"] = "EMP001"
    b5["training_program"] = "Leadership"
    b5["training_cost"] = "FREE"
    rows.append(b5)

    assert len(rows) == 50

    # Write to CSV file with UTF-8
    with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    # Initialize MasterUpload record in DB
    db = SessionLocal()
    try:
        # Clean any prior test records
        db.query(MasterHRRecord).filter(MasterHRRecord.record_id.like("%-REC-%")).delete()
        db.query(MasterUpload).filter(MasterUpload.id.like("test-%")).delete()
        db.commit()

        upload_rec = MasterUpload(
            id=upload_id,
            filename="sample_master_hr.csv",
            sha256="fake_sha256_for_test",
            uploaded_by=actor_id,
            status="queued",
        )
        db.add(upload_rec)
        db.commit()

        # Run background ingestion
        MasterImportService.process_upload_task(
            upload_id=upload_id,
            file_path=str(csv_file),
            actor_id=actor_id,
            actor_org=actor_org,
            actor_role=actor_role,
        )

        actor = ActorIdentity(actor_id=actor_id, organization_id=actor_org, role=actor_role)

        # 1. Verify upload status
        status_resp = get_upload_status(upload_id=upload_id, actor=actor, db=db)
        assert status_resp["status"] == "done"
        assert status_resp["total_rows"] == 50
        assert status_resp["accepted_rows"] == 45
        assert status_resp["rejected_rows"] == 5

        # 2. Verify rejected rows endpoint
        rej_resp = get_rejected_rows(upload_id=upload_id, format=None, actor=actor, db=db)
        assert rej_resp["rejected_count"] == 5
        assert len(rej_resp["rejected_rows"]) == 5
        bad_ids = {r["record_id"] for r in rej_resp["rejected_rows"]}
        assert bad_ids == {"BAD-REC-001", "BAD-REC-002", "BAD-REC-003", "BAD-REC-004", "BAD-REC-005"}

        # 3. Verify upload history
        history_resp = get_upload_history(limit=10, actor=actor, db=db)
        assert any(u["id"] == upload_id for u in history_resp["uploads"])

        # 4. Verify paginated records endpoint
        rec_page1 = get_master_records(page=1, page_size=20, actor=actor, db=db)
        assert rec_page1["total"] >= 45
        assert len(rec_page1["items"]) == 20

        # Filter by record_type
        rec_filtered = get_master_records(page=1, page_size=50, record_type="timesheet", actor=actor, db=db)
        assert all(r["record_type"] == "timesheet" for r in rec_filtered["items"])
        assert len(rec_filtered["items"]) >= 10

        # Search by employee name
        rec_searched = get_master_records(page=1, page_size=50, search="Employee 3", actor=actor, db=db)
        assert any("Employee 3" in r["employee_name"] for r in rec_searched["items"])

        # 5. Verify stats endpoint
        stats = get_master_stats(actor=actor, db=db)
        assert stats["total_records"] >= 45
        assert stats["by_record_type"]["employee_profile"] >= 10
        assert stats["by_record_type"]["leave_request"] >= 10
        assert stats["by_record_type"]["timesheet"] >= 10
        assert stats["totals"]["leave_days_total"] >= 20.0
        assert stats["totals"]["timesheet_hours_total"] >= 80.0

        # 6. Verify Audit Ledger entry
        audit_event = db.query(AuditEvent).filter(
            AuditEvent.action_type == "MASTER_CSV_UPLOAD",
            AuditEvent.target_id == upload_id,
        ).first()
        assert audit_event is not None
        assert audit_event.payload_diff["total_rows"] == 50
        assert audit_event.payload_diff["accepted_rows"] == 45
        assert audit_event.payload_diff["rejected_rows"] == 5

        # 7. Test Idempotent Re-upload (Same records should update, not duplicate)
        prior_count = db.query(MasterHRRecord).filter(MasterHRRecord.record_id.like("%-REC-%")).count()
        assert prior_count == 45

        # Re-run same file in new upload
        reupload_id = "test-reupload-uuid-002"
        reupload_rec = MasterUpload(
            id=reupload_id,
            filename="sample_master_hr.csv",
            sha256="fake_sha256_for_test",
            uploaded_by=actor_id,
            status="queued",
            duplicate_warning=True,
        )
        db.add(reupload_rec)
        db.commit()

        # Re-write csv with one modified value in REC-001 (updated monthly income)
        rows[0]["monthly_income"] = "9999.00"
        with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

        MasterImportService.process_upload_task(
            upload_id=reupload_id,
            file_path=str(csv_file),
            actor_id=actor_id,
            actor_org=actor_org,
            actor_role=actor_role,
        )

        after_reupload_count = db.query(MasterHRRecord).filter(MasterHRRecord.record_id.like("%-REC-%")).count()
        # Count must remain 45 (no duplicates created!)
        assert after_reupload_count == 45
        # Value must be updated
        updated_rec = db.query(MasterHRRecord).filter(MasterHRRecord.record_id == "EMP-REC-001").first()
        assert updated_rec.monthly_income == 9999.0

    finally:
        db.close()
