import pytest
from app.models.hr import SubmissionPack, ExportRun
from app.config import settings
from datetime import datetime, timezone


def test_dev_token_authentication(client):
    """Verifies that development tokens work seamlessly for all 3 personas."""
    # Employee
    r_emp = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer DEV_TOKEN_EMP001_employee"},
    )
    assert r_emp.status_code == 200
    assert r_emp.json()["actor_id"] == "EMP001"
    assert r_emp.json()["role"] == "employee"

    # Manager
    r_mgr = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer DEV_TOKEN_MGR001_manager"},
    )
    assert r_mgr.status_code == 200
    assert r_mgr.json()["actor_id"] == "MGR001"
    assert r_mgr.json()["role"] == "manager"

    # HR Admin
    r_hr = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer DEV_TOKEN_HR001_hr_admin"},
    )
    assert r_hr.status_code == 200
    assert r_hr.json()["actor_id"] == "HR001"
    assert r_hr.json()["role"] == "hr_admin"


def test_get_persona_jwt_endpoint(client):
    """Verifies minting real JWTs via /auth/token/{persona_id}."""
    resp = client.get("/auth/token/EMP001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["persona_id"] == "EMP001"
    assert data["role"] == "employee"
    assert "access_token" in data

    # Verify token works
    me_resp = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["actor_id"] == "EMP001"


def test_submissions_and_exports_listing(client, db_session):
    """Verifies listing submissions and exports."""
    # Create submission
    pack = SubmissionPack(
        snapshot_id="SNAP_LIST_01",
        employee_id="EMP001",
        period="2026-10",
        policy_version="POLICY-2026.1",
        frozen_data={"test": True},
        status="submitted",
        submitted_at=datetime.now(timezone.utc),
    )
    db_session.add(pack)
    db_session.commit()

    # Query submissions as HR
    resp = client.get(
        "/submissions",
        headers={"Authorization": "Bearer DEV_TOKEN_HR001_hr_admin"},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert any(s["snapshot_id"] == "SNAP_LIST_01" for s in items)

    # Query exports
    exp = ExportRun(
        export_run_id="EXP_LIST_01",
        snapshot_id="SNAP_LIST_01",
        export_type="PDF_JSON_PACK",
        pack_pdf_uri="test.pdf",
        pack_json_uri="test.json",
        status="pending",
        destination_system="payroll_staging",
    )
    db_session.add(exp)
    db_session.commit()

    exp_resp = client.get(
        "/exports",
        headers={"Authorization": "Bearer DEV_TOKEN_HR001_hr_admin"},
    )
    assert exp_resp.status_code == 200
    exp_items = exp_resp.json()
    assert len(exp_items) >= 1
    assert any(e["export_run_id"] == "EXP_LIST_01" for e in exp_items)
