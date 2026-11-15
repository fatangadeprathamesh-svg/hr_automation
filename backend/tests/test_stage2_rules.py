import pytest
from datetime import datetime, date, timezone
from app.rules.base import RuleOutcome, RuleSeverity
from app.rules.missing_punch import MissingPunchRule
from app.rules.hours_mismatch import HoursMismatchRule
from app.rules.missing_receipt import MissingReceiptRule
from app.rules.engine import AuditEngine
from app.models.hr import Attendance, Timesheet, ExpenseClaim, PolicyVersion, SourceImport
from app.auth.security import create_access_token


def test_missing_punch_normal_pass():
    """Rule 1 Normal: Valid punch pair returns PASS."""
    rule = MissingPunchRule()
    att = Attendance(
        source_record_id="ATT_01",
        work_date=date(2026, 10, 1),
        clock_in=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
        clock_out=datetime(2026, 10, 1, 17, 30, tzinfo=timezone.utc),
    )
    results = rule.evaluate(
        context={"attendance": [att], "attendance_feed_complete": True},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.PASS
    assert results[0].evidence["duration_hours"] == 8.5


def test_missing_punch_exception_fail():
    """Rule 1 Exception: Clock-in present but clock-out missing returns FAIL (blocking)."""
    rule = MissingPunchRule()
    att = Attendance(
        source_record_id="ATT_02",
        work_date=date(2026, 10, 2),
        clock_in=datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc),
        clock_out=None,
    )
    results = rule.evaluate(
        context={"attendance": [att], "attendance_feed_complete": True},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.FAIL
    assert results[0].severity == RuleSeverity.BLOCKING
    assert results[0].evidence["missing"] == "clock_out"
    assert "manager-reviewed clock-out correction" in results[0].suggested_action


def test_missing_punch_incomplete_feed_returns_unknown():
    """
    Non-negotiable Rule 3: Missing/incomplete feed data is 'unknown', NEVER employee fault.
    """
    rule = MissingPunchRule()
    results = rule.evaluate(
        context={"attendance": [], "attendance_feed_complete": False},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.UNKNOWN
    assert results[0].is_data_health_issue is True
    assert "system feed issue, not employee fault" in results[0].evidence["message"]


def test_hours_mismatch_normal_pass():
    """Rule 3 Normal: Timesheet hours matching punch hours returns PASS."""
    rule = HoursMismatchRule()
    att = Attendance(
        source_record_id="ATT_01",
        work_date=date(2026, 10, 1),
        clock_in=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
        clock_out=datetime(2026, 10, 1, 17, 0, tzinfo=timezone.utc),  # 8.0 hours
    )
    ts = Timesheet(
        source_record_id="TS_01",
        work_date=date(2026, 10, 1),
        regular_hours=8.0,
        overtime_hours=0.0,
    )
    results = rule.evaluate(
        context={"attendance": [att], "timesheets": [ts], "leave": []},
        policy_config={"hours_mismatch": {"tolerance_minutes": 30}},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.PASS
    assert results[0].evidence["delta_minutes"] == 0.0


def test_hours_mismatch_boundary_pass():
    """Rule 3 Boundary: Discrepancy exactly at 30 min tolerance returns PASS."""
    rule = HoursMismatchRule()
    att = Attendance(
        source_record_id="ATT_01",
        work_date=date(2026, 10, 1),
        clock_in=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
        clock_out=datetime(2026, 10, 1, 16, 30, tzinfo=timezone.utc),  # 7.5 hours
    )
    ts = Timesheet(
        source_record_id="TS_01",
        work_date=date(2026, 10, 1),
        regular_hours=8.0,  # Delta is 30 mins
        overtime_hours=0.0,
    )
    results = rule.evaluate(
        context={"attendance": [att], "timesheets": [ts], "leave": []},
        policy_config={"hours_mismatch": {"tolerance_minutes": 30}},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.PASS
    assert results[0].evidence["delta_minutes"] == 30.0


def test_hours_mismatch_exception_fail():
    """Rule 3 Exception: Discrepancy of 2 hours (>30m tolerance) returns FAIL."""
    rule = HoursMismatchRule()
    att = Attendance(
        source_record_id="ATT_01",
        work_date=date(2026, 10, 1),
        clock_in=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
        clock_out=datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc),  # 6.0 hours
    )
    ts = Timesheet(
        source_record_id="TS_01",
        work_date=date(2026, 10, 1),
        regular_hours=8.0,  # Delta is 120 mins
        overtime_hours=0.0,
    )
    results = rule.evaluate(
        context={"attendance": [att], "timesheets": [ts], "leave": []},
        policy_config={"hours_mismatch": {"tolerance_minutes": 30}},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.FAIL
    assert results[0].severity == RuleSeverity.BLOCKING
    assert results[0].evidence["delta_minutes"] == 120.0


def test_hours_mismatch_incomplete_punch_returns_unknown():
    """Incomplete punch prevents hour comparison -> returns UNKNOWN data health."""
    rule = HoursMismatchRule()
    att = Attendance(
        source_record_id="ATT_01",
        work_date=date(2026, 10, 1),
        clock_in=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
        clock_out=None,  # Incomplete
    )
    ts = Timesheet(
        source_record_id="TS_01",
        work_date=date(2026, 10, 1),
        regular_hours=8.0,
    )
    results = rule.evaluate(
        context={"attendance": [att], "timesheets": [ts], "leave": []},
        policy_config={"hours_mismatch": {"tolerance_minutes": 30}},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.UNKNOWN
    assert results[0].is_data_health_issue is True


def test_missing_receipt_normal_pass():
    """Rule 6 Normal: Claim $75 with valid receipt returns PASS."""
    rule = MissingReceiptRule()
    claim = ExpenseClaim(
        source_record_id="EXP_01",
        amount=75.0,
        currency="USD",
        category="Travel",
        receipt_reference="s3://hr-receipts/rec_01.pdf",
    )
    results = rule.evaluate(
        context={"expense_claims": [claim]},
        policy_config={"missing_receipt": {"receipt_required_threshold": 25.0}},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.PASS


def test_missing_receipt_boundary_threshold():
    """Rule 6 Boundary: Under $25 does not require receipt; exactly $25 requires receipt."""
    rule = MissingReceiptRule()
    claim_under = ExpenseClaim(source_record_id="EXP_UNDER", amount=24.99, receipt_reference=None)
    claim_exact = ExpenseClaim(source_record_id="EXP_EXACT", amount=25.00, receipt_reference=None)

    res_under = rule.evaluate(
        context={"expense_claims": [claim_under]},
        policy_config={"missing_receipt": {"receipt_required_threshold": 25.0}},
        policy_version="POLICY-2026.1",
    )
    assert res_under[0].status == RuleOutcome.NOT_APPLICABLE

    res_exact = rule.evaluate(
        context={"expense_claims": [claim_exact]},
        policy_config={"missing_receipt": {"receipt_required_threshold": 25.0}},
        policy_version="POLICY-2026.1",
    )
    assert res_exact[0].status == RuleOutcome.FAIL
    assert res_exact[0].severity == RuleSeverity.BLOCKING


def test_missing_receipt_exception_fail():
    """Rule 6 Exception: Claim $85 with missing receipt returns FAIL (blocking)."""
    rule = MissingReceiptRule()
    claim = ExpenseClaim(
        source_record_id="EXP_FAIL",
        amount=85.0,
        currency="USD",
        category="Meals",
        receipt_reference=None,
    )
    results = rule.evaluate(
        context={"expense_claims": [claim]},
        policy_config={"missing_receipt": {"receipt_required_threshold": 25.0}},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.FAIL
    assert results[0].severity == RuleSeverity.BLOCKING
    assert "Upload receipt document" in results[0].suggested_action


def test_audit_engine_aggregate_and_persistence(db_session):
    """
    Integration test: AuditEngine evaluates DB records for EMP001,
    records AuditRun and AuditFlag rows, computes blocking count and submission gate.
    """
    engine = AuditEngine()
    # Add a normal punch and an unreceipted expense
    att = Attendance(
        organization_id="ORG_DEMO_01",
        source_system="attendance",
        source_record_id="ATT_DB_01",
        import_id="IMP_01",
        employee_id="EMP001",
        work_date=date(2026, 10, 1),
        clock_in=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
        clock_out=datetime(2026, 10, 1, 17, 0, tzinfo=timezone.utc),
    )
    claim = ExpenseClaim(
        organization_id="ORG_DEMO_01",
        source_system="expense_claims",
        source_record_id="EXP_DB_01",
        import_id="IMP_01",
        employee_id="EMP001",
        claim_date=date(2026, 10, 2),
        category="Meals",
        amount=95.0,
        receipt_reference=None,  # Causes blocking flag
    )
    db_session.add_all([att, claim])
    db_session.commit()

    res = engine.run_audit(
        db=db_session,
        employee_id="EMP001",
        period="2026-10",
        trigger_source="manual",
    )

    assert res["audit_run_id"] is not None
    assert res["employee_id"] == "EMP001"
    assert res["policy_version"] == "POLICY-2026.1"
    assert res["blocking_count"] >= 1
    assert res["submission_allowed"] is False


def test_readiness_api_blocker_prevents_submission(client, db_session):
    """
    Readiness API test: High readiness score with 1 blocker strictly prevents submission.
    """
    # Create claim with missing receipt
    claim = ExpenseClaim(
        organization_id="ORG_DEMO_01",
        source_system="expense_claims",
        source_record_id="EXP_API_01",
        import_id="IMP_01",
        employee_id="EMP001",
        claim_date=date(2026, 10, 5),
        category="Travel",
        amount=150.0,
        receipt_reference=None,
    )
    db_session.add(claim)
    db_session.commit()

    token = create_access_token({"sub": "EMP001", "role": "employee", "org_id": "ORG_DEMO_01"})

    resp = client.get(
        "/employees/me/readiness?period=2026-10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["employee_id"] == "EMP001"
    assert data["blocking_count"] >= 1
    # Non-negotiable Rule 6: Blocker strictly prevents submission
    assert data["submission_allowed"] is False
    assert len(data["blocking_issues"]) >= 1


def test_cross_employee_audit_denied(client):
    """
    Security Test: Employee EMP001 attempting to trigger audit for EMP002 is denied (403).
    """
    emp1_token = create_access_token({"sub": "EMP001", "role": "employee", "org_id": "ORG_DEMO_01"})

    resp = client.post(
        "/audit-runs",
        headers={"Authorization": f"Bearer {emp1_token}"},
        json={"employee_id": "MGR001", "period": "2026-10"},
    )
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]
