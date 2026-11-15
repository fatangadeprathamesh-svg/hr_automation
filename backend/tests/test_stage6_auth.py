import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.auth import UserAuth, OTPVerification
from app.models.hr import Employee, Correction, SubmissionPack
from app.auth.service import hash_password, verify_password, AuthService, auth_rate_limiter
from app.auth.security import create_access_token


def test_password_hashing_and_verification():
    """Verifies bcrypt password hashing and verification."""
    password = "MySecurePassword2026!"
    hashed = hash_password(password)
    assert hashed != password
    assert hashed.startswith("$2b$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_login_flow_and_otp_generation(client: TestClient, db_session: Session):
    """Verifies login endpoint checks credentials and generates 6-digit OTP."""
    auth_rate_limiter.hits.clear()

    # Successful login triggers OTP
    res = client.post("/api/auth/login", json={
        "email": "alice@example.com",
        "password": "Password123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "dev_code" in data
    assert len(data["dev_code"]) == 6

    # Bad password returns 401
    bad_res = client.post("/api/auth/login", json={
        "email": "alice@example.com",
        "password": "IncorrectPassword!"
    })
    assert bad_res.status_code == 401
    assert "Invalid email or password" in bad_res.json()["detail"]


def test_otp_verification_wrong_code(client: TestClient, db_session: Session):
    """Verifies that wrong OTP code decrements attempts and returns 400 Bad Request."""
    auth_rate_limiter.hits.clear()
    email = "david.wrongcode@example.com"

    emp = db_session.query(Employee).filter(Employee.email == email).first()
    if not emp:
        emp = Employee(
            employee_id="EMP_TEST_WRONG",
            organization_id="ORG_DEMO_01",
            email=email,
            full_name="David Test",
            is_active=True,
        )
        db_session.add(emp)
        db_session.commit()

    # Generate OTP
    otp, real_code = AuthService.create_or_refresh_otp(db_session, email)

    # Submit wrong code
    res = client.post("/api/auth/verify-otp", json={
        "email": email,
        "code": "000000"
    })
    assert res.status_code == 400
    assert "Invalid verification code" in res.json()["detail"]

    # Verify attempt was recorded in DB
    refreshed_otp = db_session.query(OTPVerification).filter(OTPVerification.verification_id == otp.verification_id).first()
    assert refreshed_otp.attempts == 1


def test_otp_max_attempts_lockout(client: TestClient, db_session: Session):
    """Verifies that after 5 failed attempts, the OTP is permanently locked."""
    auth_rate_limiter.hits.clear()
    email = "lockout.test@example.com"

    emp = db_session.query(Employee).filter(Employee.email == email).first()
    if not emp:
        emp = Employee(
            employee_id="EMP_TEST_LOCKOUT",
            organization_id="ORG_DEMO_01",
            email=email,
            full_name="Lockout Test",
            is_active=True,
        )
        db_session.add(emp)
        db_session.commit()

    otp, real_code = AuthService.create_or_refresh_otp(db_session, email)

    # Fail 5 times
    for attempt in range(1, 6):
        res = client.post("/api/auth/verify-otp", json={
            "email": email,
            "code": "111111"
        })
        assert res.status_code == 400

    # 6th attempt is locked out even with the real code
    lockout_res = client.post("/api/auth/verify-otp", json={
        "email": email,
        "code": real_code
    })
    assert lockout_res.status_code == 400
    assert "Maximum verification attempts exceeded" in lockout_res.json()["detail"]


def test_otp_expired_code(client: TestClient, db_session: Session):
    """Verifies that an expired OTP code is rejected with 400 Bad Request."""
    auth_rate_limiter.hits.clear()
    email = "expired.test@example.com"

    emp = db_session.query(Employee).filter(Employee.email == email).first()
    if not emp:
        emp = Employee(
            employee_id="EMP_TEST_EXPIRED",
            organization_id="ORG_DEMO_01",
            email=email,
            full_name="Expired Test",
            is_active=True,
        )
        db_session.add(emp)
        db_session.commit()

    otp, real_code = AuthService.create_or_refresh_otp(db_session, email)

    # Artificially expire the code in DB (15 minutes in the past)
    otp.expires_at = datetime.now(timezone.utc) - timedelta(minutes=15)
    db_session.commit()

    res = client.post("/api/auth/verify-otp", json={
        "email": email,
        "code": real_code
    })
    assert res.status_code == 400
    assert "expired" in res.json()["detail"].lower()


def test_otp_resend_cooldown(client: TestClient, db_session: Session):
    """Verifies 60-second cooldown is enforced on resend requests."""
    auth_rate_limiter.hits.clear()
    email = "cooldown.test@example.com"

    emp = db_session.query(Employee).filter(Employee.email == email).first()
    if not emp:
        emp = Employee(
            employee_id="EMP_TEST_COOLDOWN",
            organization_id="ORG_DEMO_01",
            email=email,
            full_name="Cooldown Test",
            is_active=True,
        )
        db_session.add(emp)
        db_session.commit()

    # Request first OTP
    res1 = client.post("/api/auth/resend-otp", json={"email": email})
    assert res1.status_code == 200

    # Immediate second request triggers 429 cooldown
    res2 = client.post("/api/auth/resend-otp", json={"email": email})
    assert res2.status_code == 429
    assert "wait" in res2.json()["detail"].lower()


def test_httponly_cookie_issuance_and_auth_me(client: TestClient, db_session: Session):
    """Verifies httpOnly cookie is set upon OTP verification and works for /api/auth/me."""
    auth_rate_limiter.hits.clear()
    email = "alice@example.com"

    # Use DEV bypass code 123456
    res = client.post("/api/auth/verify-otp", json={
        "email": email,
        "code": "123456"
    })
    assert res.status_code == 200
    assert "access_token" in res.cookies
    cookie_value = res.cookies.get("access_token")
    assert cookie_value is not None

    # Call /api/auth/me using the cookie without Authorization header
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    profile = me_res.json()
    assert profile["actor_id"] == "EMP001"
    assert profile["role"] == "employee"


def test_google_sso_authentication(client: TestClient, db_session: Session):
    """Verifies Google Identity Services ID token verification flow."""
    auth_rate_limiter.hits.clear()
    mock_credential = "MOCK_GOOGLE_TOKEN_FOR_carol.hr@example.com"

    res = client.post("/api/auth/google", json={"credential": mock_credential})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["role"] == "hr_admin"
    assert "access_token" in res.cookies


def test_unauthenticated_request_returns_401(client: TestClient):
    """Verifies protected endpoints reject unauthenticated requests with HTTP 401."""
    # Ensure no cookies and no headers
    client.cookies.clear()
    res = client.get("/employees/me/readiness")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


def test_cross_employee_access_returns_403(client: TestClient, db_session: Session):
    """Verifies Employee A cannot view or access submission snapshot of Employee B."""
    client.cookies.clear()
    # Token for EMP002 (Bryan Baker)
    token_emp2 = create_access_token({
        "sub": "EMP002",
        "role": "employee",
        "org_id": "ORG_DEMO_01",
        "email": "bryan.baker@example.com"
    })

    # Query or create snapshot belonging strictly to EMP001
    snap = db_session.query(SubmissionPack).filter(SubmissionPack.employee_id == "EMP001").first()
    if not snap:
        snap = SubmissionPack(
            snapshot_id="SNAP_CROSS_TEST_01",
            employee_id="EMP001",
            period="2026-10",
            policy_version="POLICY-2026.2",
            frozen_data={"employee": {"employee_id": "EMP001"}},
            status="submitted",
        )
        db_session.add(snap)
        db_session.commit()

    # EMP002 attempts to access EMP001's snapshot
    res = client.get(
        f"/submissions/{snap.snapshot_id}",
        headers={"Authorization": f"Bearer {token_emp2}"}
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


def test_unassigned_manager_decision_returns_403(client: TestClient, db_session: Session):
    """Verifies Manager A (MGR002) cannot approve a correction for Employee reporting to Manager B (MGR001)."""
    client.cookies.clear()
    token_mgr2 = create_access_token({
        "sub": "MGR002",
        "role": "manager",
        "org_id": "ORG_DEMO_01",
        "email": "sarah.manager@example.com"
    })

    emp1 = db_session.query(Employee).filter(Employee.employee_id == "EMP001").first()
    assert emp1.manager_id == "MGR001"

    # Create a pending correction for EMP001
    corr = db_session.query(Correction).filter(
        Correction.employee_id == "EMP001",
        Correction.status == "pending_review"
    ).first()

    if not corr:
        corr = Correction(
            correction_id="CORR_RBAC_UNASSIGNED_TEST",
            employee_id="EMP001",
            entity_name="attendance",
            entity_id="ATT_001",
            original_record_version=1,
            original_data={"work_date": "2026-10-01"},
            proposed_data={"work_date": "2026-10-01", "punch_out": "17:00"},
            employee_reason="Forgot punch out",
            status="pending_review",
        )
        db_session.add(corr)
        db_session.commit()

    # MGR002 attempts to decide MGR001's direct report's correction
    res = client.post(
        f"/corrections/{corr.correction_id}/decision",
        headers={"Authorization": f"Bearer {token_mgr2}"},
        json={
            "decision": "approved",
            "manager_reason": "Attempting unauthorized approval"
        }
    )
    assert res.status_code == 403
    assert "is not the assigned manager" in res.json()["detail"]


def test_auth_rate_limiting(client: TestClient):
    """Verifies that exceeding the rate limit returns 429 Too Many Requests."""
    auth_rate_limiter.hits.clear()
    # auth_rate_limiter max requests is 10
    for i in range(10):
        res = client.post("/api/auth/login", json={
            "email": "ratelimit.test@example.com",
            "password": "Password123!"
        })

    # 11th request triggers rate limit 429
    res_limited = client.post("/api/auth/login", json={
        "email": "ratelimit.test@example.com",
        "password": "Password123!"
    })
    assert res_limited.status_code == 429
    assert "Rate limit exceeded" in res_limited.json()["detail"]
