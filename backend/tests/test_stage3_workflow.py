import pytest
from datetime import datetime, date, timezone
from app.models.hr import Attendance, ExpenseClaim, Correction, Approval, AuditEvent, Employee
from app.auth.security import create_access_token


def test_employee_submit_correction_version_bound(client, db_session):
    """
    Test: Employee submits correction for an attendance record.
    Binds to current record_version (v1) and logs audit event.
    """
    att = Attendance(
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        source_record_id="ATT_CORR_01",
        import_id="IMP_01",
        employee_id="EMP001",
        work_date=date(2026, 10, 2),
        clock_in=datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc),
        clock_out=None,  # Missing clock out
        record_version=1,
    )
    db_session.add(att)
    db_session.commit()

    token = create_access_token({"sub": "EMP001", "role": "employee", "org_id": "ORG_DEMO_01"})

    payload = {
        "entity_name": "attendance",
        "entity_id": att.id,
        "proposed_data": {"clock_out": "2026-10-02T17:30:00+00:00"},
        "employee_reason": "Forgot to clock out before medical appointment.",
    }

    resp = client.post(
        "/corrections",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending_review"
    assert data["bound_record_version"] == 1

    # Verify AuditEvent was logged
    event = db_session.query(AuditEvent).filter(
        AuditEvent.action_type == "SUBMIT_CORRECTION",
        AuditEvent.target_id == att.id,
    ).first()
    assert event is not None
    assert event.actor_id == "EMP001"
    assert event.payload_diff["bound_record_version"] == 1


def test_manager_approves_correction_and_increments_version(client, db_session):
    """
    Test: Assigned manager Bob (MGR001) reviews and approves Alice's (EMP001) correction.
    Target record is updated, record_version incremented from 1 to 2, and approval recorded.
    """
    att = Attendance(
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        source_record_id="ATT_APPR_01",
        import_id="IMP_01",
        employee_id="EMP001",
        work_date=date(2026, 10, 2),
        clock_in=datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc),
        clock_out=None,
        record_version=1,
    )
    db_session.add(att)
    db_session.commit()

    # Create pending correction
    corr = Correction(
        flag_id=None,
        employee_id="EMP001",
        entity_name="attendance",
        entity_id=att.id,
        original_record_version=1,
        original_data={"clock_in": "2026-10-02T09:00:00+00:00", "clock_out": None},
        proposed_data={"clock_out": "2026-10-02T17:30:00+00:00"},
        employee_reason="Card reader unpowered at exit.",
        status="pending_review",
    )
    db_session.add(corr)
    db_session.commit()

    mgr_token = create_access_token({"sub": "MGR001", "role": "manager", "org_id": "ORG_DEMO_01"})

    resp = client.post(
        f"/corrections/{corr.correction_id}/decision",
        headers={"Authorization": f"Bearer {mgr_token}"},
        json={
            "decision": "approved",
            "manager_reason": "Confirmed presence in office until 17:30.",
        },
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["decision"] == "approved"
    assert res_data["bound_record_version"] == 1
    assert res_data["new_record_version"] == 2

    # Verify DB state
    db_session.refresh(att)
    assert att.record_version == 2
    assert att.clock_out is not None

    approval = db_session.query(Approval).filter(Approval.correction_id == corr.correction_id).first()
    assert approval is not None
    assert approval.reviewer_id == "MGR001"
    assert approval.bound_record_version == 1
    assert approval.decision == "approved"


def test_cross_manager_unauthorized_decision_denied_and_logged(client, db_session):
    """
    Security Test: A manager who is NOT assigned to the employee cannot approve corrections.
    Returns HTTP 403 and writes security alert to immutable audit_events.
    """
    # Create an unassigned manager
    unassigned_mgr = Employee(
        employee_id="MGR999",
        organization_id="ORG_DEMO_01",
        email="unassigned.mgr@example.com",
        full_name="Unassigned Manager",
        hire_date=date(2024, 1, 1),
    )
    db_session.add(unassigned_mgr)

    att = Attendance(
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        source_record_id="ATT_SEC_01",
        import_id="IMP_01",
        employee_id="EMP001",
        work_date=date(2026, 10, 2),
        clock_in=datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc),
        record_version=1,
    )
    db_session.add(att)
    db_session.commit()

    corr = Correction(
        employee_id="EMP001",
        entity_name="attendance",
        entity_id=att.id,
        original_record_version=1,
        original_data={},
        proposed_data={"clock_out": "2026-10-02T17:00:00+00:00"},
        employee_reason="Forgot clock out",
        status="pending_review",
    )
    db_session.add(corr)
    db_session.commit()

    # Attempt review as unassigned manager
    unauth_token = create_access_token({"sub": "MGR999", "role": "manager", "org_id": "ORG_DEMO_01"})

    resp = client.post(
        f"/corrections/{corr.correction_id}/decision",
        headers={"Authorization": f"Bearer {unauth_token}"},
        json={
            "decision": "approved",
            "manager_reason": "Attempting unauthorized approval.",
        },
    )
    assert resp.status_code == 403
    assert "not the assigned manager" in resp.json()["detail"]

    # Verify security audit event logged
    sec_event = db_session.query(AuditEvent).filter(
        AuditEvent.action_type == "UNAUTHORIZED_DECISION_ATTEMPT",
        AuditEvent.actor_id == "MGR999",
    ).first()
    assert sec_event is not None
    assert sec_event.payload_diff["attempted_target_employee"] == "EMP001"


def test_concurrent_reviewer_conflict_rejected(client, db_session):
    """
    Non-negotiable Rule 5: Concurrency Conflict.
    If record_version changes before manager decision is recorded, stale decision is rejected (HTTP 409).
    """
    att = Attendance(
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        source_record_id="ATT_CONC_01",
        import_id="IMP_01",
        employee_id="EMP001",
        work_date=date(2026, 10, 2),
        clock_in=datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc),
        record_version=1,
    )
    db_session.add(att)
    db_session.commit()

    corr = Correction(
        employee_id="EMP001",
        entity_name="attendance",
        entity_id=att.id,
        original_record_version=1,
        original_data={},
        proposed_data={"clock_out": "2026-10-02T17:00:00+00:00"},
        employee_reason="Reason",
        status="pending_review",
    )
    db_session.add(corr)
    db_session.commit()

    # Simulate concurrent modification to the record (e.g. batch re-sync bumped version to 2)
    att.record_version = 2
    db_session.commit()

    mgr_token = create_access_token({"sub": "MGR001", "role": "manager", "org_id": "ORG_DEMO_01"})

    resp = client.post(
        f"/corrections/{corr.correction_id}/decision",
        headers={"Authorization": f"Bearer {mgr_token}"},
        json={"decision": "approved", "manager_reason": "Approved late"},
    )
    assert resp.status_code == 409
    assert "Concurrency Conflict" in resp.json()["detail"]


def test_claim_changed_after_approval_invalidates_approval(client, db_session):
    """
    Failure Test: A claim changed after approval increments version and requires new approval.
    """
    claim = ExpenseClaim(
        organization_id="ORG_DEMO_01",
        source_system="expense_claims",
        source_record_id="EXP_REV_01",
        import_id="IMP_01",
        employee_id="EMP001",
        claim_date=date(2026, 10, 5),
        category="Meals",
        amount=50.0,
        receipt_reference="s3://rec1.pdf",
        approval_state="approved",
        record_version=1,
    )
    db_session.add(claim)
    db_session.commit()

    # Bind initial approval to v1
    approval = Approval(
        correction_id="INITIAL_CORR",
        reviewer_id="MGR001",
        bound_record_version=1,
        bound_policy_version="POLICY-2026.1",
        decision="approved",
        manager_reason="Approved $50",
    )
    db_session.add(approval)
    db_session.commit()

    # Employee submits modification to increase amount to $75
    token = create_access_token({"sub": "EMP001", "role": "employee", "org_id": "ORG_DEMO_01"})

    resp = client.post(
        "/corrections",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "entity_name": "expense_claim",
            "entity_id": claim.id,
            "proposed_data": {"amount": 75.0},
            "employee_reason": "Correcting missing tip amount.",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending_review"

    # Verify old approval does NOT cover the new request
    assert approval.bound_record_version == 1


def test_pending_corrections_listing_for_manager(client, db_session):
    """
    Test: Manager Bob (MGR001) retrieves pending corrections for direct report Alice (EMP001).
    """
    att = Attendance(
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        source_record_id="ATT_LIST_01",
        import_id="IMP_01",
        employee_id="EMP001",
        work_date=date(2026, 10, 2),
        record_version=1,
    )
    db_session.add(att)
    db_session.commit()

    corr = Correction(
        employee_id="EMP001",
        entity_name="attendance",
        entity_id=att.id,
        original_record_version=1,
        original_data={"clock_out": None},
        proposed_data={"clock_out": "2026-10-02T17:00:00+00:00"},
        employee_reason="Forgot clock out",
        status="pending_review",
    )
    db_session.add(corr)
    db_session.commit()

    mgr_token = create_access_token({"sub": "MGR001", "role": "manager", "org_id": "ORG_DEMO_01"})

    resp = client.get(
        "/corrections/pending",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    target = next((c for c in items if c["correction_id"] == corr.correction_id), None)
    assert target is not None
    assert target["employee_id"] == "EMP001"
    assert "original_data" in target
    assert "proposed_data" in target
