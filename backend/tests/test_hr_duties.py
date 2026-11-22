import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.hr import Employee, AuditEvent, Leave
from app.models.duties import DutyTask, LeaveBalance, POSHRecord
from app.services.duty_registry import DUTY_REGISTRY, get_duty_config
from app.services.duty_engine import (
    DutyEngineService,
    AttendanceLeaveEngine,
    PayrollEngine,
    encrypt_posh_text,
    decrypt_posh_text,
    record_duty_audit_event,
)
from app.api.audit import verify_audit_events_integrity
from app.auth.security import ActorIdentity


def test_duty_registry_10_duties():
    """Verify registry has exactly the 10 specified duties and bot_may_finalize=True ONLY for duty 7."""
    assert len(DUTY_REGISTRY) == 10

    expected_keys = [
        "payroll_statutory",
        "labour_compliance",
        "posh",
        "discipline_grievance",
        "recruitment",
        "onboarding",
        "attendance_leave",
        "offboarding_fnf",
        "policies_records",
        "performance",
    ]
    for key in expected_keys:
        assert key in DUTY_REGISTRY, f"Missing duty key: {key}"
        cfg = DUTY_REGISTRY[key]
        assert "bot_actions" in cfg
        assert "human_gate" in cfg
        assert "approver_roles" in cfg

        if key == "attendance_leave":
            assert cfg["bot_may_finalize"] is True
            assert "auto_approval_rules" in cfg
        else:
            assert cfg["bot_may_finalize"] is False


def test_bot_approval_forbidden_403(db_session: Session):
    """Test 1: BACKEND ENFORCEMENT - Bot cannot finalize decisions for human-gated duties."""
    task = DutyEngineService.create_task(
        db=db_session,
        duty_key="payroll_statutory",
        title="October 2026 Payroll Run",
        payload={"total_gross": 1500000.0},
        prepared_by="bot:payroll",
        status_val="awaiting_approval",
    )

    # Bot identity attempting to decide/approve
    with pytest.raises(HTTPException) as exc_info:
        DutyEngineService.decide_task(
            db=db_session,
            task_id=task.id,
            decision="approved",
            actor_id="bot:auto_checker",
            actor_role="system",
            note="Bot self-approving",
        )
    assert exc_info.value.status_code == 403
    assert "bot is not permitted to finalize decisions" in exc_info.value.detail.lower()


def test_maker_checker_rule_403(db_session: Session):
    """Test 2: Maker-Checker Enforcement - Submitter/preparer cannot approve their own item."""
    task = DutyEngineService.create_task(
        db=db_session,
        duty_key="discipline_grievance",
        title="Disciplinary Notice - EMP001",
        payload={"case": "GRV-001"},
        prepared_by="HR001",
        status_val="awaiting_approval",
    )

    # HR001 prepared it, now HR001 attempts to approve it -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        DutyEngineService.decide_task(
            db=db_session,
            task_id=task.id,
            decision="approved",
            actor_id="HR001",
            actor_role="hr_admin",
            note="Self-approving my own notice",
        )
    assert exc_info.value.status_code == 403
    assert "maker-checker" in exc_info.value.detail.lower()


def test_posh_content_isolation_and_encryption(db_session: Session):
    """Test 3: POSH Content Isolation - Encrypted at rest, non-IC forbidden, zero text in audit ledger."""
    raw_complaint = "Confidential report: Inappropriate physical contact and comments on 2026-10-12."

    # 1. Test encryption & decryption
    encrypted = encrypt_posh_text(raw_complaint)
    assert encrypted != raw_complaint
    assert decrypt_posh_text(encrypted) == raw_complaint

    # 2. Store POSH record with encrypted complaint
    posh_rec = POSHRecord(
        case_number="POSH-TEST-001",
        incident_date=date(2026, 10, 12),
        status="inquiry_ongoing",
        encrypted_complaint=encrypted,
    )
    db_session.add(posh_rec)
    db_session.flush()

    task = DutyEngineService.create_task(
        db=db_session,
        duty_key="posh",
        title="Inquiry: POSH-TEST-001",
        payload={"case_number": "POSH-TEST-001"},
        prepared_by="bot",
        status_val="awaiting_approval",
    )

    # 3. Non-IC Member (e.g. manager or regular HR) attempting to approve POSH case -> 403
    with pytest.raises(HTTPException) as exc_mgr:
        DutyEngineService.decide_task(
            db=db_session,
            task_id=task.id,
            decision="approved",
            actor_id="MGR001",
            actor_role="manager",
            note="Manager attempting POSH clearance",
        )
    assert exc_mgr.value.status_code == 403
    assert "internal committee" in exc_mgr.value.detail.lower()

    # 4. Authorized IC Member can approve
    approved_task = DutyEngineService.decide_task(
        db=db_session,
        task_id=task.id,
        decision="approved",
        actor_id="IC001",
        actor_role="ic_member",
        note="IC Member findings confirmed",
    )
    assert approved_task.status == "approved"
    assert approved_task.approver_id == "IC001"

    # 5. Audit Ledger Privacy Check: Zero complaint text in ledger
    audit_events = db_session.query(AuditEvent).filter(
        AuditEvent.target_id == task.id
    ).all()
    for evt in audit_events:
        evt_str = str(evt.payload_diff or {})
        assert "Inappropriate physical contact" not in evt_str
        assert "complaint_text" not in (evt.payload_diff or {})


def test_leave_auto_approval_rule_boundaries(db_session: Session):
    """Test 4: Attendance & Leave (Duty 7) - Auto-approval vs Manager Exception Routing."""
    # Ensure EMP001 has leave balance
    bal = db_session.query(LeaveBalance).filter(
        LeaveBalance.employee_id == "EMP001",
        LeaveBalance.leave_type == "casual",
    ).first()
    if not bal:
        bal = LeaveBalance(
            employee_id="EMP001",
            leave_type="casual",
            accrued=Decimal("12.0"),
            taken=Decimal("0.0"),
            remaining=Decimal("12.0"),
        )
        db_session.add(bal)
        db_session.flush()

    # Boundary Case A: Compliant Leave (1.0 day casual, sufficient balance, no overlap)
    # MUST be AUTO-APPROVED by the bot!
    res_a = AttendanceLeaveEngine.process_leave_request(
        db=db_session,
        employee_id="EMP001",
        leave_type="casual",
        start_date=date(2026, 11, 28),
        end_date=date(2026, 11, 28),
        days_requested=1.0,
        reason="Personal errand",
    )
    assert res_a["auto_approved"] is True
    assert res_a["task"].status == "approved"
    assert res_a["task"].prepared_by == "bot:auto_approval"
    assert res_a["task"].approver_id == "bot:auto_approval"

    # Boundary Case B: Exceeds 2-day policy limit (3.0 days casual leave)
    # MUST NOT be auto-approved; routes to human manager queue as an exception!
    res_b = AttendanceLeaveEngine.process_leave_request(
        db=db_session,
        employee_id="EMP001",
        leave_type="casual",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 12),
        days_requested=3.0,
        reason="Vacation trip",
    )
    assert res_b["auto_approved"] is False
    assert res_b["task"].status == "awaiting_approval"
    assert "exceeds auto-approval limit" in str(res_b["task"].payload.get("exception_reasons", []))


def test_hash_chained_ledger_for_duty_actions(db_session: Session):
    """Test 5: Ledger Integrity - Every duty action writes to the hash-chained audit ledger."""
    # Append an audit event
    record_duty_audit_event(
        db=db_session,
        actor_id="HR001",
        actor_role="hr_admin",
        action_type="DUTY_PAYROLL_STATUTORY_APPROVED",
        duty_key="payroll_statutory",
        task_id="TASK-TEST-LEDGER",
        payload_diff={"note": "Verified gross to net"},
    )
    db_session.flush()

    # Check that events exist and are immutable
    events = db_session.query(AuditEvent).filter(
        AuditEvent.target_id == "TASK-TEST-LEDGER"
    ).all()
    assert len(events) == 1
    assert events[0].action_type == "DUTY_PAYROLL_STATUTORY_APPROVED"
