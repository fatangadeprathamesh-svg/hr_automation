import pytest
from datetime import datetime, date, timezone, timedelta
from app.rules.base import RuleOutcome, RuleSeverity
from app.rules.leave_conflict import LeaveConflictRule
from app.rules.duplicate_claim import DuplicateClaimRule
from app.rules.over_limit_claim import OverLimitClaimRule
from app.rules.unapproved_overtime import UnapprovedOvertimeRule
from app.rules.pending_approvals import PendingApprovalsRule
from app.rules.expiring_documents import ExpiringDocumentsRule
from app.rules.engine import AuditEngine
from app.models.hr import (
    Employee,
    Attendance,
    Leave,
    Timesheet,
    ExpenseClaim,
    Document,
    Correction,
    PolicyVersion,
    SourceImport,
)


# ============================================================================
# Rule 4: LEAVE_CONFLICT Tests
# ============================================================================

def test_leave_conflict_normal_pass():
    """Approved leave on day with no punches or timesheet hours passes cleanly."""
    rule = LeaveConflictRule()
    lv = Leave(
        source_record_id="LV-01",
        start_date=date(2026, 10, 15),
        end_date=date(2026, 10, 15),
        leave_type="annual",
        days_taken=1.0,
        approval_state="approved",
    )
    results = rule.evaluate(
        context={"leave": [lv], "attendance": [], "timesheets": []},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.PASS
    assert results[0].severity == RuleSeverity.INFO


def test_leave_conflict_full_day_with_attendance_fail_blocking():
    """Full-day approved leave with attendance punch is a blocking conflict."""
    rule = LeaveConflictRule()
    lv = Leave(
        source_record_id="LV-02",
        start_date=date(2026, 10, 16),
        end_date=date(2026, 10, 16),
        leave_type="sick",
        days_taken=1.0,
        approval_state="approved",
    )
    att = Attendance(
        source_record_id="ATT-02",
        work_date=date(2026, 10, 16),
        clock_in=datetime(2026, 10, 16, 9, 0, tzinfo=timezone.utc),
        clock_out=datetime(2026, 10, 16, 17, 0, tzinfo=timezone.utc),
    )
    results = rule.evaluate(
        context={"leave": [lv], "attendance": [att], "timesheets": []},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.FAIL
    assert results[0].severity == RuleSeverity.BLOCKING
    assert results[0].evidence["conflict_date"] == "2026-10-16"


def test_leave_conflict_half_day_tolerance():
    """Half day leave: <= 4.5h timesheet passes, > 4.5h triggers warning."""
    rule = LeaveConflictRule()
    lv = Leave(
        source_record_id="LV-03",
        start_date=date(2026, 10, 17),
        end_date=date(2026, 10, 17),
        leave_type="medical",
        days_taken=0.5,
        approval_state="approved",
    )
    # Under half day limit (4.0 hours)
    ts_ok = Timesheet(
        source_record_id="TS-03A",
        work_date=date(2026, 10, 17),
        regular_hours=4.0,
        overtime_hours=0.0,
    )
    res_ok = rule.evaluate(
        context={"leave": [lv], "attendance": [], "timesheets": [ts_ok]},
        policy_config={"leave_conflict": {"half_day_tolerance_hours": 4.5}},
        policy_version="POLICY-2026.1",
    )
    assert len(res_ok) == 1
    assert res_ok[0].status == RuleOutcome.PASS

    # Exceeding half day limit (6.0 hours)
    ts_excess = Timesheet(
        source_record_id="TS-03B",
        work_date=date(2026, 10, 17),
        regular_hours=6.0,
        overtime_hours=0.0,
    )
    res_excess = rule.evaluate(
        context={"leave": [lv], "attendance": [], "timesheets": [ts_excess]},
        policy_config={"leave_conflict": {"half_day_tolerance_hours": 4.5}},
        policy_version="POLICY-2026.1",
    )
    assert len(res_excess) == 1
    assert res_excess[0].status == RuleOutcome.FAIL
    assert res_excess[0].severity == RuleSeverity.WARNING


def test_leave_conflict_data_health_unknown():
    """Corrupted leave dates or negative days_taken return UNKNOWN data health issue."""
    rule = LeaveConflictRule()
    # Missing dates
    lv_nodate = Leave(source_record_id="LV-ERR1", start_date=None, end_date=None, days_taken=1.0)
    # Start after end
    lv_badrange = Leave(source_record_id="LV-ERR2", start_date=date(2026, 10, 20), end_date=date(2026, 10, 19), days_taken=1.0)
    # Negative days
    lv_neg = Leave(source_record_id="LV-ERR3", start_date=date(2026, 10, 10), end_date=date(2026, 10, 10), days_taken=-1.0)

    for lv in [lv_nodate, lv_badrange, lv_neg]:
        res = rule.evaluate(
            context={"leave": [lv], "attendance": [], "timesheets": []},
            policy_config={},
            policy_version="POLICY-2026.1",
        )
        assert len(res) == 1
        assert res[0].status == RuleOutcome.UNKNOWN
        assert res[0].is_data_health_issue is True
        assert res[0].severity == RuleSeverity.WARNING


# ============================================================================
# Rule 5: DUPLICATE_CLAIM Tests
# ============================================================================

def test_duplicate_claim_normal_pass():
    """Distinct claims with different dates, receipts, and amounts pass."""
    rule = DuplicateClaimRule()
    c1 = ExpenseClaim(
        source_record_id="EXP-01",
        claim_date=date(2026, 10, 5),
        amount=45.0,
        category="meals",
        merchant_name="Cafe Alpha",
        receipt_reference="REC-001",
    )
    c2 = ExpenseClaim(
        source_record_id="EXP-02",
        claim_date=date(2026, 10, 6),
        amount=80.0,
        category="travel",
        merchant_name="Trainline",
        receipt_reference="REC-002",
    )
    results = rule.evaluate(
        context={"expense_claims": [c1, c2]},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 2
    assert all(r.status == RuleOutcome.PASS for r in results)


def test_duplicate_claim_identical_receipt_fail_blocking():
    """Identical receipt references across two distinct claims trigger duplicate FAIL (blocking)."""
    rule = DuplicateClaimRule()
    c1 = ExpenseClaim(
        source_record_id="EXP-03",
        claim_date=date(2026, 10, 10),
        amount=50.0,
        category="meals",
        receipt_reference="SHARED-REC-999",
    )
    c2 = ExpenseClaim(
        source_record_id="EXP-04",
        claim_date=date(2026, 10, 12),
        amount=50.0,
        category="meals",
        receipt_reference="SHARED-REC-999",
    )
    results = rule.evaluate(
        context={"expense_claims": [c1, c2]},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 2
    assert all(r.status == RuleOutcome.FAIL for r in results)
    assert all(r.severity == RuleSeverity.BLOCKING for r in results)


def test_duplicate_claim_same_date_amount_merchant_fail():
    """Same date, amount, and merchant name triggers duplicate FAIL (blocking)."""
    rule = DuplicateClaimRule()
    c1 = ExpenseClaim(
        source_record_id="EXP-05",
        claim_date=date(2026, 10, 14),
        amount=120.0,
        category="supplies",
        merchant_name="Office Depot",
        receipt_reference="REC-AAA",
    )
    c2 = ExpenseClaim(
        source_record_id="EXP-06",
        claim_date=date(2026, 10, 14),
        amount=120.0,
        category="supplies",
        merchant_name="Office Depot",
        receipt_reference="REC-BBB",
    )
    results = rule.evaluate(
        context={"expense_claims": [c1, c2]},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 2
    assert all(r.status == RuleOutcome.FAIL for r in results)
    assert all(r.severity == RuleSeverity.BLOCKING for r in results)


def test_duplicate_claim_data_health_unknown():
    """Negative amount or missing claim date triggers UNKNOWN (data health)."""
    rule = DuplicateClaimRule()
    c_neg = ExpenseClaim(source_record_id="EXP-ERR1", claim_date=date(2026, 10, 1), amount=-30.0)
    c_nodate = ExpenseClaim(source_record_id="EXP-ERR2", claim_date=None, amount=30.0)

    for c in [c_neg, c_nodate]:
        res = rule.evaluate(
            context={"expense_claims": [c]},
            policy_config={},
            policy_version="POLICY-2026.1",
        )
        assert len(res) == 1
        assert res[0].status == RuleOutcome.UNKNOWN
        assert res[0].is_data_health_issue is True


# ============================================================================
# Rule 6: OVER_LIMIT_CLAIM Tests
# ============================================================================

def test_over_limit_claim_normal_pass():
    """Claims within category policy limits return PASS."""
    rule = OverLimitClaimRule()
    c = ExpenseClaim(
        source_record_id="EXP-OK",
        claim_date=date(2026, 10, 8),
        amount=55.0,
        category="meals",
    )
    results = rule.evaluate(
        context={"expense_claims": [c]},
        policy_config={"over_limit_claim": {"category_limits": {"meals": 75.0}}},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.PASS
    assert results[0].evidence["policy_limit"] == 75.0


def test_over_limit_claim_excess_fail_blocking():
    """Claim exceeding category limit returns FAIL (blocking) with excess calculation."""
    rule = OverLimitClaimRule()
    c = ExpenseClaim(
        source_record_id="EXP-OVER",
        claim_date=date(2026, 10, 8),
        amount=110.0,
        category="meals",
    )
    results = rule.evaluate(
        context={"expense_claims": [c]},
        policy_config={"over_limit_claim": {"category_limits": {"meals": 75.0}}},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.FAIL
    assert results[0].severity == RuleSeverity.BLOCKING
    assert results[0].evidence["excess_amount"] == 35.0


def test_over_limit_claim_fallback_limit():
    """Unlisted category uses default fallback limit."""
    rule = OverLimitClaimRule()
    c = ExpenseClaim(
        source_record_id="EXP-MISC",
        claim_date=date(2026, 10, 8),
        amount=350.0,
        category="miscellaneous_software",
    )
    results = rule.evaluate(
        context={"expense_claims": [c]},
        policy_config={"over_limit_claim": {"category_limits": {}, "default_limit": 300.0}},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.FAIL
    assert results[0].severity == RuleSeverity.BLOCKING
    assert results[0].evidence["excess_amount"] == 50.0


# ============================================================================
# Rule 7: UNAPPROVED_OVERTIME Tests
# ============================================================================

def test_unapproved_overtime_standard_pass():
    """Standard 8.0 regular hours with 0 overtime returns PASS."""
    rule = UnapprovedOvertimeRule()
    ts = Timesheet(
        source_record_id="TS-01",
        work_date=date(2026, 10, 1),
        regular_hours=8.0,
        overtime_hours=0.0,
        approval_state="pending",
    )
    results = rule.evaluate(
        context={"timesheets": [ts]},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.PASS


def test_unapproved_overtime_approved_ot_pass():
    """Overtime hours that are manager-approved return PASS."""
    rule = UnapprovedOvertimeRule()
    ts = Timesheet(
        source_record_id="TS-02",
        work_date=date(2026, 10, 2),
        regular_hours=8.0,
        overtime_hours=2.5,
        approval_state="approved",
    )
    results = rule.evaluate(
        context={"timesheets": [ts]},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.PASS


def test_unapproved_overtime_unapproved_ot_fail_warning():
    """Unapproved overtime between 8.0h and 12.0h returns FAIL (warning)."""
    rule = UnapprovedOvertimeRule()
    ts = Timesheet(
        source_record_id="TS-03",
        work_date=date(2026, 10, 3),
        regular_hours=8.0,
        overtime_hours=2.0,
        approval_state="pending",
    )
    results = rule.evaluate(
        context={"timesheets": [ts]},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.FAIL
    assert results[0].severity == RuleSeverity.WARNING
    assert results[0].evidence["unapproved_overtime_hours"] == 2.0


def test_unapproved_overtime_excessive_fail_blocking():
    """Daily hours > 12.0h returns FAIL (blocking) regardless of approval."""
    rule = UnapprovedOvertimeRule()
    ts = Timesheet(
        source_record_id="TS-04",
        work_date=date(2026, 10, 4),
        regular_hours=8.0,
        overtime_hours=5.0,  # Total 13.0 hours
        approval_state="approved",
    )
    results = rule.evaluate(
        context={"timesheets": [ts]},
        policy_config={"unapproved_overtime": {"overtime_blocking_threshold": 12.0}},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.FAIL
    assert results[0].severity == RuleSeverity.BLOCKING
    assert results[0].evidence["total_hours"] == 13.0


def test_unapproved_overtime_corrupted_data_health():
    """Hours > 24 or negative hours return UNKNOWN (data health issue)."""
    rule = UnapprovedOvertimeRule()
    ts_24 = Timesheet(source_record_id="TS-ERR1", work_date=date(2026, 10, 5), regular_hours=20.0, overtime_hours=10.0)
    ts_neg = Timesheet(source_record_id="TS-ERR2", work_date=date(2026, 10, 6), regular_hours=-4.0, overtime_hours=0.0)

    for ts in [ts_24, ts_neg]:
        res = rule.evaluate(
            context={"timesheets": [ts]},
            policy_config={},
            policy_version="POLICY-2026.1",
        )
        assert len(res) == 1
        assert res[0].status == RuleOutcome.UNKNOWN
        assert res[0].is_data_health_issue is True


# ============================================================================
# Rule 8: PENDING_APPROVALS Tests
# ============================================================================

def test_pending_approvals_all_resolved_pass():
    """When all timesheets, expenses, and corrections are approved/resolved, returns PASS."""
    rule = PendingApprovalsRule()
    ts = Timesheet(source_record_id="TS-OK", approval_state="approved")
    exp = ExpenseClaim(source_record_id="EXP-OK", approval_state="approved")
    corr = Correction(correction_id="CORR-OK", status="approved")

    results = rule.evaluate(
        context={"timesheets": [ts], "expense_claims": [exp], "leave": [], "corrections": [corr]},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.PASS
    assert results[0].evidence["decided_records_count"] == 3


def test_pending_approvals_pending_items_fail_blocking():
    """Pending timesheets or corrections trigger FAIL (blocking)."""
    rule = PendingApprovalsRule()
    ts = Timesheet(source_record_id="TS-PEND", approval_state="pending")
    corr = Correction(correction_id="CORR-PEND", status="pending_review")

    results = rule.evaluate(
        context={"timesheets": [ts], "expense_claims": [], "leave": [], "corrections": [corr]},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 2
    assert all(r.status == RuleOutcome.FAIL for r in results)
    assert all(r.severity == RuleSeverity.BLOCKING for r in results)


def test_pending_approvals_missing_state_unknown():
    """Missing approval state triggers UNKNOWN data health issue."""
    rule = PendingApprovalsRule()
    ts = Timesheet(source_record_id="TS-ERR", approval_state=None)
    results = rule.evaluate(
        context={"timesheets": [ts], "expense_claims": [], "leave": [], "corrections": []},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.UNKNOWN
    assert results[0].is_data_health_issue is True


# ============================================================================
# Rule 9: EXPIRING_DOCUMENTS Tests
# ============================================================================

def test_expiring_documents_far_expiry_pass():
    """Documents with > 60 days remaining return PASS."""
    rule = ExpiringDocumentsRule()
    ref_d = date(2026, 10, 31)
    doc = Document(
        source_record_id="DOC-PASS",
        document_type="passport",
        document_reference="P12345678",
        expiry_date=date(2027, 5, 1),  # ~180 days away
    )
    results = rule.evaluate(
        context={"documents": [doc], "reference_date": ref_d},
        policy_config={"expiring_documents": {"warning_days": 60, "blocking_days": 30}},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.PASS


def test_expiring_documents_warning_window():
    """Document expiring within 31-60 days returns FAIL (warning)."""
    rule = ExpiringDocumentsRule()
    ref_d = date(2026, 10, 31)
    doc = Document(
        source_record_id="DOC-WARN",
        document_type="work_permit",
        document_reference="WP-9988",
        expiry_date=ref_d + timedelta(days=45),
    )
    results = rule.evaluate(
        context={"documents": [doc], "reference_date": ref_d},
        policy_config={"expiring_documents": {"warning_days": 60, "blocking_days": 30}},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.FAIL
    assert results[0].severity == RuleSeverity.WARNING
    assert results[0].evidence["days_remaining"] == 45


def test_expiring_documents_blocking_critical_window():
    """Document expiring in <= 30 days returns FAIL (blocking)."""
    rule = ExpiringDocumentsRule()
    ref_d = date(2026, 10, 31)
    doc = Document(
        source_record_id="DOC-CRIT",
        document_type="visa",
        document_reference="V-4455",
        expiry_date=ref_d + timedelta(days=15),
    )
    results = rule.evaluate(
        context={"documents": [doc], "reference_date": ref_d},
        policy_config={"expiring_documents": {"warning_days": 60, "blocking_days": 30}},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.FAIL
    assert results[0].severity == RuleSeverity.BLOCKING
    assert results[0].evidence["days_remaining"] == 15


def test_expiring_documents_already_expired():
    """Already expired document returns FAIL (blocking)."""
    rule = ExpiringDocumentsRule()
    ref_d = date(2026, 10, 31)
    doc = Document(
        source_record_id="DOC-EXP",
        document_type="passport",
        document_reference="P-EXPIRED",
        expiry_date=date(2026, 10, 20),  # Expired 11 days before period end
    )
    results = rule.evaluate(
        context={"documents": [doc], "reference_date": ref_d},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.FAIL
    assert results[0].severity == RuleSeverity.BLOCKING
    assert results[0].evidence["days_expired"] == 11


def test_expiring_documents_data_health_missing_expiry():
    """Mandatory passport missing expiry date returns UNKNOWN data health issue."""
    rule = ExpiringDocumentsRule()
    doc = Document(
        source_record_id="DOC-ERR",
        document_type="passport",
        document_reference="P-CORRUPT",
        expiry_date=None,
    )
    results = rule.evaluate(
        context={"documents": [doc]},
        policy_config={},
        policy_version="POLICY-2026.1",
    )
    assert len(results) == 1
    assert results[0].status == RuleOutcome.UNKNOWN
    assert results[0].is_data_health_issue is True


# ============================================================================
# Integration: 9-Rule Engine Execution
# ============================================================================

def test_audit_engine_evaluates_all_nine_rules(db_session):
    """Verifies that AuditEngine instantiates and evaluates all 9 rules against DB data."""
    engine = AuditEngine()
    assert len(engine.rules) == 9

    # Create test employee
    emp = Employee(
        employee_id="EMP-9RULES",
        organization_id="ORG_TEST",
        full_name="Ada Lovelace",
        email="ada.lovelace@example.com",
        timezone="America/New_York",
        is_active=True,
    )
    imp = SourceImport(
        import_id="IMP-STAGE8",
        organization_id="ORG_TEST",
        source_system="attendance",
        covered_period="2026-10",
        status="completed",
        completeness_flag=True,
    )
    db_session.add_all([emp, imp])
    db_session.commit()

    # 1. Clean attendance record
    att = Attendance(
        employee_id="EMP-9RULES",
        source_system="attendance",
        source_record_id="ATT-P9-1",
        import_id="IMP-STAGE8",
        organization_id="ORG_TEST",
        work_date=date(2026, 10, 1),
        clock_in=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
        clock_out=datetime(2026, 10, 1, 17, 30, tzinfo=timezone.utc),
    )
    # 2. Matching timesheet
    ts = Timesheet(
        employee_id="EMP-9RULES",
        source_system="timesheet",
        source_record_id="TS-P9-1",
        import_id="IMP-STAGE8",
        organization_id="ORG_TEST",
        work_date=date(2026, 10, 1),
        regular_hours=8.5,
        overtime_hours=0.0,
        approval_state="approved",
    )
    # 3. Clean expense claim with receipt
    exp = ExpenseClaim(
        employee_id="EMP-9RULES",
        source_system="expense",
        source_record_id="EXP-P9-1",
        import_id="IMP-STAGE8",
        organization_id="ORG_TEST",
        claim_date=date(2026, 10, 5),
        category="meals",
        amount=30.0,
        currency="USD",
        receipt_reference="REC-CLEAN-9",
        merchant_name="Bistro Clean",
        approval_state="approved",
    )
    # 4. Valid document far in future
    doc = Document(
        employee_id="EMP-9RULES",
        source_system="hris",
        source_record_id="DOC-P9-1",
        import_id="IMP-STAGE8",
        organization_id="ORG_TEST",
        document_type="passport",
        document_reference="PASS-998811",
        issue_date=date(2024, 1, 1),
        expiry_date=date(2030, 1, 1),
        verification_status="verified",
    )
    db_session.add_all([att, ts, exp, doc])
    db_session.commit()

    # Execute complete audit
    result = engine.run_audit(
        db=db_session,
        employee_id="EMP-9RULES",
        period="2026-10",
        trigger_source="stage8_integration_test",
    )

    assert result["audit_run_id"] is not None
    assert result["blocking_count"] == 0
    assert result["submission_allowed"] is True
    assert result["data_health"] == "complete"

    rule_ids_evaluated = {f["rule_id"] for f in result["flags"]}
    assert "MISSING_PUNCH" in rule_ids_evaluated
    assert "HOURS_MISMATCH" in rule_ids_evaluated
    assert "MISSING_RECEIPT" in rule_ids_evaluated
    assert "LEAVE_CONFLICT" in rule_ids_evaluated
    assert "DUPLICATE_CLAIM" in rule_ids_evaluated
    assert "OVER_LIMIT_CLAIM" in rule_ids_evaluated
    assert "UNAPPROVED_OVERTIME" in rule_ids_evaluated
    assert "PENDING_APPROVALS" in rule_ids_evaluated
    assert "EXPIRING_DOCUMENTS" in rule_ids_evaluated
