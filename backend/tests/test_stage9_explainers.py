import pytest
from fastapi import HTTPException
from app.services.llm_explainer import (
    AIExplainerService,
    sanitize_for_ai,
    DISCLAIMER_TEXT,
)
from app.config import settings
from app.auth.security import ActorIdentity, require_role
from app.api.explainers import (
    explain_audit_flag,
    draft_correction_request,
    get_hr_monthly_summary,
    ExplainFlagRequest,
    DraftCorrectionRequest,
    HrSummaryRequest,
)


# ============================================================================
# 1. Data Minimization & Privacy Unit Tests
# ============================================================================

def test_sanitize_for_ai_removes_personal_identifiers():
    """
    Non-negotiable Rule for Phase 9:
    Strict data minimization: personal names, emails, addresses are NEVER sent to LLM.
    Only IDs and evidence fields are retained.
    """
    raw_evidence = {
        "record_id": "REC_901",
        "first_name": "Alice",
        "last_name": "Smith",
        "full_name": "Alice Smith",
        "email": "alice.smith@corporate.com",
        "phone": "+1-555-0199",
        "home_address": "123 Main St, Springfield",
        "salary": 120000,
        "work_date": "2026-10-15",
        "regular_hours": 8.0,
        "attendance_hours": 6.5,
        "notes": "Sent notification to supervisor bob.manager@corporate.com regarding badge issue.",
    }

    sanitized = sanitize_for_ai(raw_evidence)

    # Personal identity fields must be completely removed
    assert "first_name" not in sanitized
    assert "last_name" not in sanitized
    assert "full_name" not in sanitized
    assert "email" not in sanitized
    assert "phone" not in sanitized
    assert "home_address" not in sanitized
    assert "salary" not in sanitized

    # Structural IDs and metrics must be retained
    assert sanitized["record_id"] == "REC_901"
    assert sanitized["work_date"] == "2026-10-15"
    assert sanitized["regular_hours"] == 8.0
    assert sanitized["attendance_hours"] == 6.5

    # Any email inside string fields must be redacted
    assert "bob.manager@corporate.com" not in sanitized["notes"]
    assert "[REDACTED_EMAIL]" in sanitized["notes"]


# ============================================================================
# 2. Service Unit Tests: Explain Flag
# ============================================================================

def test_explain_flag_deterministic_template():
    """Verifies that explain_flag returns clear, policy-grounded explanation with disclaimer."""
    service = AIExplainerService()
    res = service.explain_flag(
        rule_id="MISSING_PUNCH",
        evidence={"work_date": "2026-10-12", "missing": "clock_out"},
        severity="blocking",
        outcome="fail",
        policy_version="POLICY-2026.1",
    )

    assert res["disclaimer"] == DISCLAIMER_TEXT
    assert res["rule_id"] == "MISSING_PUNCH"
    assert res["severity"] == "blocking"
    assert res["is_blocking"] is True
    assert "clock_out" in res["explanation"]
    assert "punch correction" in res["suggested_action"].lower()


@pytest.mark.parametrize("rule_id", [
    "HOURS_MISMATCH",
    "MISSING_RECEIPT",
    "LEAVE_CONFLICT",
    "DUPLICATE_CLAIM",
    "OVER_LIMIT_CLAIM",
    "UNAPPROVED_OVERTIME",
    "PENDING_APPROVALS",
    "EXPIRING_DOCUMENTS",
])
def test_explain_flag_covers_all_rules(rule_id):
    """Verifies that every one of the 9 rules has an accurate explainer."""
    service = AIExplainerService()
    res = service.explain_flag(
        rule_id=rule_id,
        evidence={"amount": 85.0, "work_date": "2026-10-14", "category": "meals"},
        severity="warning",
        outcome="fail",
    )
    assert res["disclaimer"] == DISCLAIMER_TEXT
    assert len(res["explanation"]) > 20
    assert len(res["suggested_action"]) > 10


# ============================================================================
# 3. Service Unit Tests: Draft Correction
# ============================================================================

def test_draft_correction_generates_polite_employee_draft():
    """Verifies that draft_correction proposes realistic adjustment values and respectful justification."""
    service = AIExplainerService()
    res = service.draft_correction(
        rule_id="HOURS_MISMATCH",
        evidence={"work_date": "2026-10-08", "attendance_hours": 8.0, "timesheet_hours": 6.5},
        policy_version="POLICY-2026.1",
        user_notes="Visited offsite datacenter for client maintenance.",
    )

    assert res["disclaimer"] == DISCLAIMER_TEXT
    assert "8.0" in res["proposed_value"]
    assert "Visited offsite datacenter" in res["draft_reason"]
    assert "manager" in res["draft_reason"].lower()


# ============================================================================
# 4. Service Unit Tests: HR Monthly Summary
# ============================================================================

def test_generate_hr_summary_statistical_and_no_surveillance():
    """
    Non-negotiable Rule for Phase 9:
    Statistical 'needs review' check ONLY.
    No screen monitoring, keystroke tracking, or productivity scoring.
    """
    service = AIExplainerService()
    sample_stats = {
        "total_audited_employees": 30,
        "employees_with_blockers": 5,
        "top_flagged_rules": [
            {"rule_id": "MISSING_RECEIPT", "count": 10, "description": "Claims missing receipts"},
            {"rule_id": "HOURS_MISMATCH", "count": 6, "description": "Badge vs timesheet variance"},
        ],
        "data_health_completeness": "100% complete",
    }

    res = service.generate_hr_summary(period="2026-10", stats=sample_stats)

    assert res["disclaimer"] == DISCLAIMER_TEXT
    assert res["period"] == "2026-10"
    assert "83.3%" in res["readiness_rate"]  # (25 / 30) = 83.3%
    assert len(res["key_insights"]) >= 2
    assert len(res["recommended_actions"]) >= 2
    # Check explicit anti-surveillance guarantee
    assert "screen monitoring" in res["surveillance_notice"].lower()
    assert "keystroke tracking" in res["surveillance_notice"].lower()


# ============================================================================
# 5. API Endpoints Tests
# ============================================================================

def test_api_explain_flag_endpoint():
    """Authenticated employee can trigger an explanation for any audit flag."""
    actor = ActorIdentity(actor_id="EMP001", organization_id=settings.ORGANIZATION_ID, role="employee")
    req = ExplainFlagRequest(
        rule_id="OVER_LIMIT_CLAIM",
        evidence={
            "amount": 120.0,
            "policy_limit": 75.0,
            "excess_amount": 45.0,
            "category": "meals",
        },
        severity="blocking",
        outcome="fail",
    )
    data = explain_audit_flag(req, actor)
    assert data["disclaimer"] == DISCLAIMER_TEXT
    assert data["rule_id"] == "OVER_LIMIT_CLAIM"
    assert data["is_blocking"] is True
    assert "120.0" in data["explanation"] or "75.0" in data["explanation"]


def test_api_draft_correction_endpoint():
    """Authenticated employee can generate a correction draft."""
    actor = ActorIdentity(actor_id="EMP001", organization_id=settings.ORGANIZATION_ID, role="employee")
    req = DraftCorrectionRequest(
        rule_id="MISSING_PUNCH",
        evidence={"work_date": "2026-10-18", "missing": "clock_out"},
        user_notes="Badge sensor red-lighted when leaving through west door.",
    )
    data = draft_correction_request(req, actor)
    assert data["disclaimer"] == DISCLAIMER_TEXT
    assert "17:30" in data["proposed_value"] or "Clock-out" in data["proposed_value"]
    assert "Badge sensor" in data["draft_reason"]


def test_api_hr_summary_endpoint_and_rbac(db_session):
    """
    RBAC: Employee role is FORBIDDEN from accessing HR executive summary;
    HR Admin role is ALLOWED.
    """
    checker = require_role("hr_admin", "manager", "service")
    emp_actor = ActorIdentity(actor_id="EMP001", organization_id=settings.ORGANIZATION_ID, role="employee")
    with pytest.raises(HTTPException) as exc_info:
        checker(emp_actor)
    assert exc_info.value.status_code == 403

    hr_actor = ActorIdentity(actor_id="HR001", organization_id=settings.ORGANIZATION_ID, role="hr_admin")
    validated_actor = checker(hr_actor)
    assert validated_actor.role == "hr_admin"

    req = HrSummaryRequest(period="2026-10")
    data = get_hr_monthly_summary(req, hr_actor, db_session)
    assert data["disclaimer"] == DISCLAIMER_TEXT
    assert data["period"] == "2026-10"
    assert "executive_summary" in data
    assert "key_insights" in data
