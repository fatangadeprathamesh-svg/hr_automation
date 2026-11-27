import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db


@pytest.fixture
def override_db(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield db_session
    app.dependency_overrides.clear()


def test_employee_rbac_rejections(override_db):
    client = TestClient(app)
    emp_token = "DEV_TOKEN_EMP0001_employee"
    headers = {"Authorization": f"Bearer {emp_token}"}

    # 1. Master HR upload endpoints reject employee
    res = client.get("/api/uploads", headers=headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    res = client.get("/api/records", headers=headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    res = client.get("/api/stats", headers=headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    # 2. HR Summary explainer rejects employee
    res = client.post("/api/ai/hr-summary", json={"period": "2026-10"}, headers=headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    # 3. Audit log rejects employee
    res = client.get("/audit-events", headers=headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    # 4. HR metrics rejects employee
    res = client.get("/api/audit/hr-metrics", headers=headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    # 5. Manager metrics rejects employee
    res = client.get("/api/audit/manager-metrics", headers=headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"


def test_ic_member_posh_only_access(override_db):
    client = TestClient(app)
    ic_token = "DEV_TOKEN_EMP0004_ic_member"
    headers = {"Authorization": f"Bearer {ic_token}"}

    # IC member gets 403 on other duties
    res = client.get("/api/duties/attendance_leave", headers=headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    res = client.get("/api/duties/payroll_statutory", headers=headers)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"

    # IC member can access POSH duty
    res = client.get("/api/duties/posh", headers=headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

    # Hub returns only POSH for IC member
    res = client.get("/api/duties/hub", headers=headers)
    assert res.status_code == 200
    duties = res.json().get("duties", [])
    assert len(duties) == 1
    assert duties[0]["key"] == "posh"


def test_sync_status_endpoint(override_db):
    client = TestClient(app)
    hr_token = "DEV_TOKEN_EMP0003_hr_admin"
    headers = {"Authorization": f"Bearer {hr_token}"}

    res = client.get("/api/sync/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "rows_mapped_per_audit_table" in data
    assert "findings_per_rule" in data
    assert "role_scope" in data
    assert data["role_scope"] == "hr_admin"
    assert "no-store" in res.headers.get("Cache-Control", "").lower()


def test_audit_periods_empty_when_no_data(override_db):
    from app.api.audit import invalidate_audit_cache
    invalidate_audit_cache()
    client = TestClient(app)
    headers = {"Authorization": "Bearer DEV_TOKEN_EMP0001_employee"}
    res = client.get("/api/audit/periods", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["periods"], list)
    assert len(data["periods"]) == 0
    assert data["default_period"] is None
