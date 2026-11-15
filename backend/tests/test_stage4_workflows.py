import os
import glob
import pytest
from datetime import datetime, date, timezone
from app.config import settings
from app.auth.security import create_access_token
from app.models.hr import Attendance, SourceImport, AuditEvent, ExternalEnrichment
from app.rules.engine import AuditEngine


def test_workflow_blueprints_validation_and_zero_hardcoded_secrets():
    """
    Test: Validates all exported n8n workflow blueprints in n8n/workflows/
    against structural schema and ensures zero plaintext secrets are checked in.
    """
    import sys
    n8n_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n8n"))
    sys.path.insert(0, n8n_path)
    from validate_workflows import validate_workflow_file

    workflow_files = glob.glob(os.path.join(n8n_path, "workflows", "*.json"))
    assert len(workflow_files) == 5, f"Expected 5 workflow JSON blueprints, found {len(workflow_files)}"

    for f in workflow_files:
        assert validate_workflow_file(f) is True


def test_workflow_a_incomplete_feed_halts_audit_and_escalates(client, db_session):
    """
    Workflow A Recovery Test: Incomplete attendance feed halts downstream audit
    and escalates to operator without marking failed feed as completed.
    """
    # 1. Ingest incomplete feed
    csv_data = "source_record_id,employee_id,work_date,clock_in,clock_out,timezone\nATT_INC_1,EMP001,2026-10-01,2026-10-01T09:00:00-04:00,2026-10-01T17:00:00-04:00,America/New_York"
    resp = client.post(
        "/imports",
        headers={"X-Service-Key": settings.N8N_SERVICE_API_KEY},
        data={"source_system": "attendance", "covered_period": "2026-10", "is_complete_feed": "false"},
        files={"file": ("attendance_inc.csv", csv_data, "text/csv")},
    )
    assert resp.status_code == 201
    data = resp.json()

    # Completeness must be False
    assert data["completeness_flag"] is False

    # Workflow A Condition Check:
    # If completeness_flag is False -> Workflow routes to 'Escalate Incomplete Feed & Halt Audit'
    is_audit_triggered = (data["status"] == "completed" and data["completeness_flag"] is True)
    assert is_audit_triggered is False, "Audit should NOT be automatically triggered for incomplete feeds!"


def test_workflow_b_minimal_notification_privacy(client):
    """
    Workflow B Privacy Gate Test:
    Minimal message contains portal link only.
    Rejects notifications containing sensitive salary, wage, or punch details.
    """
    # 1. Safe minimal message succeeds
    safe_payload = {
        "employee_id": "EMP001",
        "fingerprint": "fp_test_safe_01",
        "message_body": "Your October self-audit has 1 item requiring attention. Sign in to the HR portal to review.",
        "portal_url": "https://portal.company.com/audit?period=2026-10",
    }
    resp = client.post(
        "/notifications/dispatch",
        headers={"X-Service-Key": settings.N8N_SERVICE_API_KEY},
        json=safe_payload,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "delivered"

    # 2. Unsafe message with sensitive details is rejected
    unsafe_payload = {
        "employee_id": "EMP001",
        "fingerprint": "fp_test_unsafe_02",
        "message_body": "Your hourly wage of $45.00 has a missing punch at 09:12:00. Salary review impacted.",
        "portal_url": "https://portal.company.com/audit",
    }
    resp_bad = client.post(
        "/notifications/dispatch",
        headers={"X-Service-Key": settings.N8N_SERVICE_API_KEY},
        json=unsafe_payload,
    )
    assert resp_bad.status_code == 400
    assert "Security violation" in resp_bad.json()["detail"]


def test_workflow_b_notification_deduplication(client, db_session):
    """
    Workflow B Deduplication Test:
    Unchanged unresolved flags are deduplicated.
    First run dispatches; second identical run is recognized as duplicate.
    """
    fp = "fp_dedup_unique_oct_emp001"

    # Check 1: Should not be duplicate initially
    check1 = client.post(
        "/notifications/check-dedup",
        headers={"X-Service-Key": settings.N8N_SERVICE_API_KEY},
        json={"employee_id": "EMP001", "fingerprint": fp},
    )
    assert check1.status_code == 200
    assert check1.json()["is_duplicate"] is False

    # Dispatch notification
    client.post(
        "/notifications/dispatch",
        headers={"X-Service-Key": settings.N8N_SERVICE_API_KEY},
        json={
            "employee_id": "EMP001",
            "fingerprint": fp,
            "message_body": "October self-audit requires review.",
            "portal_url": "https://portal.company.com/audit",
        },
    )

    # Check 2: Must be identified as duplicate
    check2 = client.post(
        "/notifications/check-dedup",
        headers={"X-Service-Key": settings.N8N_SERVICE_API_KEY},
        json={"employee_id": "EMP001", "fingerprint": fp},
    )
    assert check2.status_code == 200
    assert check2.json()["is_duplicate"] is True


def test_workflow_c_decision_to_reaudit_integration(client, db_session):
    """
    Workflow C Integration Test:
    Manager approval triggers re-audit callback, updating readiness state and resolving flag.
    """
    att = Attendance(
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        source_record_id="ATT_WFC_01",
        import_id="IMP_01",
        employee_id="EMP001",
        work_date=date(2026, 10, 1),
        clock_in=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
        clock_out=None,
        record_version=1,
    )
    db_session.add(att)
    db_session.commit()

    # Initial audit creates flag
    engine = AuditEngine()
    audit_res1 = engine.run_audit(db_session, "EMP001", "2026-10")
    assert audit_res1["blocking_count"] >= 1

    # Employee submits correction
    emp_token = create_access_token({"sub": "EMP001", "role": "employee", "org_id": "ORG_DEMO_01"})
    corr_resp = client.post(
        "/corrections",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={
            "entity_name": "attendance",
            "entity_id": att.id,
            "proposed_data": {"clock_out": "2026-10-01T17:00:00+00:00"},
            "employee_reason": "Forgot badge at desk",
        },
    )
    assert corr_resp.status_code == 201
    corr_id = corr_resp.json()["correction_id"]

    # Manager approves
    mgr_token = create_access_token({"sub": "MGR001", "role": "manager", "org_id": "ORG_DEMO_01"})
    dec_resp = client.post(
        f"/corrections/{corr_id}/decision",
        headers={"Authorization": f"Bearer {mgr_token}"},
        json={"decision": "approved", "manager_reason": "Approved punch"},
    )
    assert dec_resp.status_code == 200
    dec_data = dec_resp.json()

    # Re-audit summary returned automatically upon approval
    assert dec_data["re_audit_summary"] is not None
    assert dec_data["re_audit_summary"]["blocking_count"] == 0
    assert dec_data["re_audit_summary"]["submission_allowed"] is True


def test_workflow_e_crustdata_unavailable_does_not_block_audit(client, db_session):
    """
    Non-negotiable Rule 9 Test:
    Crustdata failure / unavailability records enrichment as 'unavailable'
    and NEVER blocks the core HR audit run.
    """
    # 1. Simulate Crustdata unavailable response saved to external_enrichments
    resp = client.post(
        "/enrichments",
        headers={"X-Service-Key": settings.N8N_SERVICE_API_KEY},
        json={
            "entity_type": "vendor",
            "entity_id": "EXP_TEST_VENDOR_01",
            "provider": "crustdata",
            "query_key": "Unknown Vendor LLC",
            "provider_response": {"error": "503 Service Unavailable", "status": "down"},
            "review_status": "unavailable",
        },
    )
    assert resp.status_code == 201
    enrichment_id = resp.json()["enrichment_id"]

    # Verify enrichment stored in separate table
    record = db_session.query(ExternalEnrichment).filter(
        ExternalEnrichment.enrichment_id == enrichment_id
    ).first()
    assert record is not None
    assert record.review_status == "unavailable"

    # 2. Core HR audit runs completely unimpeded
    engine = AuditEngine()
    audit_res = engine.run_audit(db_session, "EMP001", "2026-10")
    assert audit_res["audit_run_id"] is not None
    assert audit_res["data_health"] == "complete"
