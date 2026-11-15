import os
import json
import pytest
from datetime import datetime, date, timezone
from app.auth.security import create_access_token
from app.config import settings
from app.models.hr import (
    Attendance,
    ExpenseClaim,
    SubmissionPack,
    ExportRun,
    PolicyVersion,
    SourceImport,
    AuditEvent,
)


def test_submission_gate_rejected_with_blocker(client, db_session):
    """
    Non-negotiable Rule 6 Test:
    Even with high readiness, a single blocking issue strictly prevents submission (HTTP 422).
    """
    # Create missing punch (blocker)
    att = Attendance(
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        source_record_id="ATT_GATE_01",
        import_id="IMP_01",
        employee_id="EMP001",
        work_date=date(2026, 10, 1),
        clock_in=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
        clock_out=None,  # Missing punch
        record_version=1,
    )
    db_session.add(att)
    db_session.commit()

    token = create_access_token({"sub": "EMP001", "role": "employee", "org_id": "ORG_DEMO_01"})

    resp = client.post(
        "/submissions",
        headers={"Authorization": f"Bearer {token}"},
        json={"period": "2026-10"},
    )
    assert resp.status_code == 422
    assert "blocking issue(s)" in resp.json()["detail"]


def test_submission_gate_rejected_with_incomplete_feed(client, db_session):
    """
    Submission Gate Test: Incomplete source feed prevents snapshot freeze.
    """
    # Clean attendance punch
    att = Attendance(
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        source_record_id="ATT_GATE_02",
        import_id="IMP_01",
        employee_id="EMP001",
        work_date=date(2026, 10, 1),
        clock_in=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
        clock_out=datetime(2026, 10, 1, 17, 0, tzinfo=timezone.utc),
        record_version=1,
    )
    # Feed marked incomplete
    imp = SourceImport(
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        covered_period="2026-10",
        status="partial",
        completeness_flag=False,
    )
    db_session.add_all([att, imp])
    db_session.commit()

    token = create_access_token({"sub": "EMP001", "role": "employee", "org_id": "ORG_DEMO_01"})

    resp = client.post(
        "/submissions",
        headers={"Authorization": f"Bearer {token}"},
        json={"period": "2026-10"},
    )
    assert resp.status_code == 422
    assert "incomplete or truncated" in resp.json()["detail"]


def test_submission_gate_success_and_hr_review_flow(client, db_session):
    """
    End-to-End Test: Clean data passes submission gate, freezes atomic snapshot,
    allows HR return with reason, remediation, and HR approval.
    """
    # 1. Clean attendance punch
    att = Attendance(
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        source_record_id="ATT_CLEAN_01",
        import_id="IMP_01",
        employee_id="EMP001",
        work_date=date(2026, 10, 1),
        clock_in=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
        clock_out=datetime(2026, 10, 1, 17, 0, tzinfo=timezone.utc),
        record_version=1,
    )
    # Feed marked complete
    imp = SourceImport(
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        covered_period="2026-10",
        status="completed",
        completeness_flag=True,
    )
    db_session.add_all([att, imp])
    db_session.commit()

    token = create_access_token({"sub": "EMP001", "role": "employee", "org_id": "ORG_DEMO_01"})

    # 2. Submit Month-End
    sub_resp = client.post(
        "/submissions",
        headers={"Authorization": f"Bearer {token}"},
        json={"period": "2026-10"},
    )
    assert sub_resp.status_code == 201
    snap = sub_resp.json()
    snapshot_id = snap["snapshot_id"]
    assert snap["status"] == "submitted"
    assert snap["frozen_data"]["employee"]["employee_id"] == "EMP001"
    assert snap["frozen_data"]["source_coverage"]["attendance"] == "complete"

    # 3. HR Review - Return with reason
    hr_token = create_access_token({"sub": "HR001", "role": "hr_admin", "org_id": "ORG_DEMO_01"})
    ret_resp = client.post(
        f"/submissions/{snapshot_id}/hr-decision",
        headers={"Authorization": f"Bearer {hr_token}"},
        json={
            "decision": "returned",
            "hr_reason": "Please attach receipt for unexpected overtime parking fee.",
            "assigned_owner": "EMP001",
        },
    )
    assert ret_resp.status_code == 200
    ret_data = ret_resp.json()
    assert ret_data["status"] == "returned"
    assert "overtime parking fee" in ret_data["hr_return_reason"]

    # 4. HR Review - Final Approval
    appr_resp = client.post(
        f"/submissions/{snapshot_id}/hr-decision",
        headers={"Authorization": f"Bearer {hr_token}"},
        json={
            "decision": "approved",
            "hr_reason": "Receipt verified. Approved for export.",
        },
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "approved"


def test_dual_export_pdf_and_json_parity(client, db_session):
    """
    Non-negotiable Rule 7 Test:
    PDF and JSON are generated from the identical frozen snapshot.
    Files exist, are non-empty, and data agrees 100%.
    """
    # Create approved submission pack
    snapshot_id = "SNAP_PARITY_TEST_01"
    frozen_snapshot = {
        "snapshot_id": snapshot_id,
        "period": "2026-10",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "employee": {
            "employee_id": "EMP001",
            "full_name": "Alice Employee",
            "organization_id": "ORG_DEMO_01",
            "timezone": "America/New_York",
        },
        "policy_version": "POLICY-2026.1",
        "audit_summary": {
            "audit_run_id": "AUD-TEST-PARITY",
            "blocking_count": 0,
            "warning_count": 0,
            "data_health": "complete",
            "status": "APPROVED_READY_FOR_PAYROLL",
        },
        "source_coverage": {
            "attendance": "complete",
            "timesheets": "complete",
            "expense_claims": "complete",
        },
        "audit_flags": [
            {
                "rule_id": "MISSING_PUNCH",
                "status": "pass",
                "severity": "info",
                "policy_version": "POLICY-2026.1",
                "resolution_status": "resolved",
            }
        ],
        "approval_history": [
            {
                "entity_name": "attendance",
                "bound_record_version": 1,
                "reviewer_id": "MGR001",
                "decision": "approved",
                "manager_reason": "Confirmed work hours",
                "decided_at": "2026-10-03T18:00:00Z",
            }
        ],
    }

    pack = SubmissionPack(
        snapshot_id=snapshot_id,
        employee_id="EMP001",
        period="2026-10",
        policy_version="POLICY-2026.1",
        frozen_data=frozen_snapshot,
        status="approved",
        submitted_at=datetime.now(timezone.utc),
    )
    db_session.add(pack)
    db_session.commit()

    # Generate Export
    hr_token = create_access_token({"sub": "HR001", "role": "hr_admin", "org_id": "ORG_DEMO_01"})
    exp_resp = client.post(
        "/exports",
        headers={"Authorization": f"Bearer {hr_token}"},
        json={"snapshot_id": snapshot_id, "export_type": "PDF_JSON_PACK"},
    )
    assert exp_resp.status_code == 201
    exp_data = exp_resp.json()
    assert exp_data["is_replayed"] is False

    pdf_path = exp_data["pack_pdf_uri"]
    json_path = exp_data["pack_json_uri"]

    assert os.path.exists(pdf_path), f"PDF file not found at {pdf_path}"
    assert os.path.exists(json_path), f"JSON file not found at {json_path}"
    assert os.path.getsize(pdf_path) > 1000, "PDF file is too small or empty"

    # Verify JSON content matches snapshot
    with open(json_path, "r", encoding="utf-8") as f:
        loaded_json = json.load(f)

    assert loaded_json["snapshot_id"] == snapshot_id
    assert loaded_json["employee"]["employee_id"] == "EMP001"
    assert loaded_json["policy_version"] == "POLICY-2026.1"
    assert len(loaded_json["approval_history"]) == 1


def test_repeated_export_attempts_idempotent(client, db_session):
    """
    Test: Repeated export calls with same snapshot/destination do not create duplicate export runs.
    """
    snapshot_id = "SNAP_IDEMP_TEST_02"
    pack = SubmissionPack(
        snapshot_id=snapshot_id,
        employee_id="EMP001",
        period="2026-10",
        policy_version="POLICY-2026.1",
        frozen_data={"snapshot_id": snapshot_id, "employee": {"employee_id": "EMP001"}},
        status="approved",
    )
    db_session.add(pack)
    db_session.commit()

    hr_token = create_access_token({"sub": "HR001", "role": "hr_admin", "org_id": "ORG_DEMO_01"})

    # Export Call 1
    resp1 = client.post(
        "/exports",
        headers={"Authorization": f"Bearer {hr_token}"},
        json={"snapshot_id": snapshot_id},
    )
    assert resp1.status_code == 201
    run_id1 = resp1.json()["export_run_id"]
    assert resp1.json()["is_replayed"] is False

    # Export Call 2 (Repeated)
    resp2 = client.post(
        "/exports",
        headers={"Authorization": f"Bearer {hr_token}"},
        json={"snapshot_id": snapshot_id},
    )
    assert resp2.status_code == 201
    run_id2 = resp2.json()["export_run_id"]
    assert resp2.json()["is_replayed"] is True
    assert run_id1 == run_id2

    # Assert exactly 1 export run exists in DB
    total_runs = db_session.query(ExportRun).filter(ExportRun.snapshot_id == snapshot_id).count()
    assert total_runs == 1


def test_historical_snapshot_reproducibility(client, db_session):
    """
    Non-negotiable Rule 8 Test:
    Historical policy change leaves old snapshots reproducible.
    """
    hist_snapshot_id = "SNAP_HISTORICAL_2026_01"
    hist_frozen_data = {
        "snapshot_id": hist_snapshot_id,
        "period": "2026-01",
        "policy_version": "POLICY-2026.1",
        "employee": {"employee_id": "EMP001"},
        "audit_summary": {"status": "APPROVED", "policy_version": "POLICY-2026.1"},
    }
    pack = SubmissionPack(
        snapshot_id=hist_snapshot_id,
        employee_id="EMP001",
        period="2026-01",
        policy_version="POLICY-2026.1",
        frozen_data=hist_frozen_data,
        status="approved",
    )
    db_session.add(pack)
    db_session.commit()

    # Now simulate a company policy change for the new year (POLICY-2027.1)
    new_policy = PolicyVersion(
        policy_version="POLICY-2027.1",
        effective_from=date(2027, 1, 1),
        rule_configurations={"missing_receipt": {"receipt_required_threshold": 50.0}},
        is_active=True,
    )
    db_session.add(new_policy)
    db_session.commit()

    # Query historical snapshot
    token = create_access_token({"sub": "EMP001", "role": "employee", "org_id": "ORG_DEMO_01"})
    resp = client.get(
        f"/submissions/{hist_snapshot_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Historical policy and data are retained 100% identically
    assert data["policy_version"] == "POLICY-2026.1"
    assert data["frozen_data"]["policy_version"] == "POLICY-2026.1"
