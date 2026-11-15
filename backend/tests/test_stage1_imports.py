import os
import pytest
from datetime import datetime, timezone
from app.imports.service import IngestionService, compute_natural_row_hash
from app.models.hr import Attendance, SourceImport, AuditEvent
from app.config import settings


def test_valid_attendance_import_and_source_traceability(db_session):
    """
    Exit Condition 1: Source traceability proven.
    Every inserted row retains organization_id, source_system, source_record_id,
    imported_at, import_id, record_version, and raw_evidence_reference.
    """
    csv_data = """source_record_id,employee_id,work_date,clock_in,clock_out,timezone,shift_id,approval_state
ATT_TEST_001,EMP001,2026-10-01,2026-10-01T09:00:00-04:00,2026-10-01T17:30:00-04:00,America/New_York,STANDARD_DAY,approved
"""
    result = IngestionService.ingest_csv(
        db=db_session,
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        covered_period="2026-10",
        file_content=csv_data,
        actor_id="service:n8n",
        raw_file_uri="uploads://attendance_oct.csv",
        is_complete_feed=True,
    )

    assert result["status"] == "completed"
    assert result["inserted_rows"] == 1
    assert result["skipped_duplicates"] == 0
    assert result["errors"] == []

    # Verify database persistence & provenance
    record = db_session.query(Attendance).filter(Attendance.source_record_id == "ATT_TEST_001").first()
    assert record is not None
    assert record.employee_id == "EMP001"
    assert record.organization_id == "ORG_DEMO_01"
    assert record.source_system == "attendance"
    assert record.import_id == result["import_id"]
    assert record.record_version == 1
    assert record.raw_evidence_reference == "uploads://attendance_oct.csv#line=1"
    assert record.imported_at is not None
    assert record.timezone == "America/New_York"


def test_replayed_import_creates_no_duplicates(db_session):
    """
    Exit Condition 2: Replayed imports create no duplicates.
    Ingesting the exact same feed a second time inserts 0 records and increments skipped_duplicates.
    """
    csv_data = """source_record_id,employee_id,work_date,clock_in,clock_out,timezone,shift_id,approval_state
ATT_REPLAY_01,EMP001,2026-10-01,2026-10-01T09:00:00-04:00,2026-10-01T17:30:00-04:00,America/New_York,STANDARD_DAY,approved
"""
    # First Import
    res1 = IngestionService.ingest_csv(
        db=db_session,
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        covered_period="2026-10",
        file_content=csv_data,
        actor_id="service:n8n",
    )
    assert res1["inserted_rows"] == 1
    assert res1["skipped_duplicates"] == 0

    # Second (Replayed) Import
    res2 = IngestionService.ingest_csv(
        db=db_session,
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        covered_period="2026-10",
        file_content=csv_data,
        actor_id="service:n8n",
    )
    assert res2["inserted_rows"] == 0
    assert res2["skipped_duplicates"] == 1
    assert res2["status"] == "completed"

    # Confirm only one record exists in DB
    total = db_session.query(Attendance).filter(Attendance.source_record_id == "ATT_REPLAY_01").count()
    assert total == 1


def test_invalid_csv_rejected_unknown_employee(db_session):
    """
    Exit Condition 3: Invalid files rejected.
    Rows referencing unknown employees are rejected and recorded in validation_errors.
    """
    csv_data = """source_record_id,employee_id,work_date,clock_in,clock_out,timezone
ATT_BAD_EMP,EMP_NONEXISTENT_999,2026-10-01,2026-10-01T09:00:00-04:00,2026-10-01T17:00:00-04:00,America/New_York
"""
    result = IngestionService.ingest_csv(
        db=db_session,
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        covered_period="2026-10",
        file_content=csv_data,
        actor_id="service:n8n",
    )

    assert result["status"] == "failed"
    assert result["inserted_rows"] == 0
    assert len(result["errors"]) == 1
    assert "EMP_NONEXISTENT_999" in result["errors"][0]


def test_invalid_csv_rejected_bad_timestamp(db_session):
    """
    Exit Condition 3b: Corrupt timestamps rejected.
    """
    csv_data = """source_record_id,employee_id,work_date,clock_in,clock_out,timezone
ATT_BAD_TS,EMP001,2026-10-01,CORRUPT_TIMESTAMP,2026-10-01T17:00:00-04:00,America/New_York
"""
    result = IngestionService.ingest_csv(
        db=db_session,
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        covered_period="2026-10",
        file_content=csv_data,
        actor_id="service:n8n",
    )

    assert result["status"] == "failed"
    assert result["inserted_rows"] == 0
    assert any("Invalid datetime format" in err for err in result["errors"])


def test_fallback_natural_hash_when_source_id_missing(db_session):
    """
    Strategy test: If a CSV lacks stable IDs, deterministic SHA256 natural key hash is computed.
    Equal employee/date values alone do not prove a duplicate (e.g. split shifts).
    """
    csv_data = """employee_id,work_date,clock_in,clock_out,timezone
EMP001,2026-10-05,2026-10-05T09:00:00-04:00,2026-10-05T13:00:00-04:00,America/New_York
EMP001,2026-10-05,2026-10-05T14:00:00-04:00,2026-10-05T18:00:00-04:00,America/New_York
"""
    result = IngestionService.ingest_csv(
        db=db_session,
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        covered_period="2026-10",
        file_content=csv_data,
        actor_id="service:n8n",
    )

    assert result["status"] == "completed"
    assert result["inserted_rows"] == 2

    records = db_session.query(Attendance).filter(
        Attendance.employee_id == "EMP001",
        Attendance.work_date == datetime(2026, 10, 5).date()
    ).all()
    assert len(records) == 2
    assert records[0].source_record_id.startswith("GEN_")
    assert records[1].source_record_id.startswith("GEN_")
    assert records[0].source_record_id != records[1].source_record_id


def test_overnight_shift_preservation_with_timezone(db_session):
    """
    Overnight shift test: Punch in at 22:00 on Day 1, punch out at 06:00 on Day 2.
    Attributes properly with timezone intact.
    """
    csv_data = """source_record_id,employee_id,work_date,clock_in,clock_out,timezone,shift_id
ATT_NIGHT_01,EMP001,2026-10-10,2026-10-10T22:00:00-04:00,2026-10-11T06:00:00-04:00,America/New_York,NIGHT_SHIFT
"""
    result = IngestionService.ingest_csv(
        db=db_session,
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        covered_period="2026-10",
        file_content=csv_data,
        actor_id="service:n8n",
    )

    assert result["status"] == "completed"
    record = db_session.query(Attendance).filter(Attendance.source_record_id == "ATT_NIGHT_01").first()
    assert record is not None
    assert record.work_date == datetime(2026, 10, 10).date()
    assert record.clock_in.hour == 22 or record.clock_in.hour == 2  # depending on UTC conversion
    assert record.timezone == "America/New_York"


def test_audit_events_immutability(db_session):
    """
    Non-negotiable Design Rule: audit_events must be protected from ordinary edits.
    Attempting to update or delete an AuditEvent must raise PermissionError.
    """
    # 1. Test update prevention
    event1 = AuditEvent(
        organization_id="ORG_DEMO_01",
        actor_id="service:n8n",
        actor_role="service",
        action_type="TEST_ACTION_UPDATE",
        target_entity="employees",
        target_id="EMP001",
        payload_diff={"test": True},
    )
    db_session.add(event1)
    db_session.commit()

    event1.action_type = "TAMPERED_ACTION"
    with pytest.raises(PermissionError, match="immutable and cannot be updated"):
        db_session.commit()

    db_session.rollback()

    # 2. Test delete prevention on fresh event
    event2 = AuditEvent(
        organization_id="ORG_DEMO_01",
        actor_id="service:n8n",
        actor_role="service",
        action_type="TEST_ACTION_DELETE",
        target_entity="employees",
        target_id="EMP001",
        payload_diff={"test": True},
    )
    db_session.add(event2)
    db_session.commit()

    db_session.delete(event2)
    with pytest.raises(PermissionError, match="immutable and cannot be deleted"):
        db_session.commit()

    db_session.rollback()


def test_api_import_endpoint_with_auth(client):
    """
    API Test: POST /imports with service API key succeeds,
    and unauthenticated or unauthorized role is rejected.
    """
    # 1. Reject without auth
    resp_no_auth = client.post(
        "/imports",
        data={"source_system": "attendance", "covered_period": "2026-10", "is_complete_feed": "true"},
        files={"file": ("test.csv", "source_record_id,employee_id,work_date\nATT1,EMP001,2026-10-01", "text/csv")},
    )
    assert resp_no_auth.status_code == 401

    # 2. Reject with wrong role (e.g. employee attempting to ingest imports)
    from app.auth.security import create_access_token
    emp_token = create_access_token({"sub": "EMP001", "role": "employee", "org_id": "ORG_DEMO_01"})
    resp_emp = client.post(
        "/imports",
        headers={"Authorization": f"Bearer {emp_token}"},
        data={"source_system": "attendance", "covered_period": "2026-10", "is_complete_feed": "true"},
        files={"file": ("test.csv", "source_record_id,employee_id,work_date\nATT1,EMP001,2026-10-01", "text/csv")},
    )
    assert resp_emp.status_code == 403

    # 3. Accept with service key
    csv_content = """source_record_id,employee_id,work_date,clock_in,clock_out,timezone
ATT_API_001,EMP001,2026-10-01,2026-10-01T09:00:00-04:00,2026-10-01T17:00:00-04:00,America/New_York
"""
    resp_service = client.post(
        "/imports",
        headers={"X-Service-Key": settings.N8N_SERVICE_API_KEY},
        data={"source_system": "attendance", "covered_period": "2026-10", "is_complete_feed": "true"},
        files={"file": ("attendance.csv", csv_content, "text/csv")},
    )
    assert resp_service.status_code == 201
    data = resp_service.json()
    assert data["status"] == "completed"
    assert data["inserted_rows"] == 1

    # 4. Check GET /imports/{id}
    import_id = data["import_id"]
    get_resp = client.get(
        f"/imports/{import_id}",
        headers={"X-Service-Key": settings.N8N_SERVICE_API_KEY},
    )
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["import_id"] == import_id
    assert get_data["completeness_flag"] is True


def test_ingest_all_sample_data_files(db_session):
    """
    End-to-End test: Ingests all generated synthetic CSV files from sample-data/
    and confirms ledger integrity across attendance, leave, timesheets, expense claims, and documents.
    """
    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sample-data"))

    # Ingest Attendance
    with open(os.path.join(sample_dir, "attendance_valid.csv"), "r") as f:
        att_res = IngestionService.ingest_csv(
            db=db_session,
            organization_id="ORG_DEMO_01",
            source_system="attendance",
            covered_period="2026-10",
            file_content=f.read(),
            actor_id="service:n8n",
            raw_file_uri="sample-data/attendance_valid.csv",
        )
    assert att_res["status"] == "completed"
    assert att_res["inserted_rows"] == 4

    # Ingest Leave
    with open(os.path.join(sample_dir, "leave_valid.csv"), "r") as f:
        leave_res = IngestionService.ingest_csv(
            db=db_session,
            organization_id="ORG_DEMO_01",
            source_system="leave",
            covered_period="2026-10",
            file_content=f.read(),
            actor_id="service:n8n",
            raw_file_uri="sample-data/leave_valid.csv",
        )
    assert leave_res["status"] == "completed"
    assert leave_res["inserted_rows"] == 2

    # Ingest Timesheets
    with open(os.path.join(sample_dir, "timesheets_valid.csv"), "r") as f:
        ts_res = IngestionService.ingest_csv(
            db=db_session,
            organization_id="ORG_DEMO_01",
            source_system="timesheets",
            covered_period="2026-10",
            file_content=f.read(),
            actor_id="service:n8n",
            raw_file_uri="sample-data/timesheets_valid.csv",
        )
    assert ts_res["status"] == "completed"
    assert ts_res["inserted_rows"] == 4

    # Ingest Expense Claims
    with open(os.path.join(sample_dir, "expense_claims_valid.csv"), "r") as f:
        exp_res = IngestionService.ingest_csv(
            db=db_session,
            organization_id="ORG_DEMO_01",
            source_system="expense_claims",
            covered_period="2026-10",
            file_content=f.read(),
            actor_id="service:n8n",
            raw_file_uri="sample-data/expense_claims_valid.csv",
        )
    assert exp_res["status"] == "completed"
    assert exp_res["inserted_rows"] == 5

    # Ingest Documents
    with open(os.path.join(sample_dir, "documents_valid.csv"), "r") as f:
        doc_res = IngestionService.ingest_csv(
            db=db_session,
            organization_id="ORG_DEMO_01",
            source_system="documents",
            covered_period="2026-10",
            file_content=f.read(),
            actor_id="service:n8n",
            raw_file_uri="sample-data/documents_valid.csv",
        )
    assert doc_res["status"] == "completed"
    assert doc_res["inserted_rows"] == 4


def test_incomplete_feed_status_tracking(db_session):
    """
    Test: Feeding an incomplete attendance batch properly sets completeness_flag to False.
    """
    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sample-data"))
    with open(os.path.join(sample_dir, "attendance_incomplete.csv"), "r") as f:
        res = IngestionService.ingest_csv(
            db=db_session,
            organization_id="ORG_DEMO_01",
            source_system="attendance",
            covered_period="2026-10",
            file_content=f.read(),
            actor_id="service:n8n",
            raw_file_uri="sample-data/attendance_incomplete.csv",
            is_complete_feed=False,
        )
    assert res["status"] == "completed"
    assert res["completeness_flag"] is False
    assert res["inserted_rows"] == 1
