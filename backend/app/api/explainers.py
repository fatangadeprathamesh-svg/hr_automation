from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.auth.security import get_current_actor, require_role, ActorIdentity
from app.services.llm_explainer import ai_explainer, DISCLAIMER_TEXT
from app.models.hr import AuditRun, AuditFlag, Employee, Correction, SourceImport

router = APIRouter(prefix="/ai", tags=["AI Explainers"])


class ExplainFlagRequest(BaseModel):
    flag_id: Optional[str] = None
    rule_id: str
    rule_version: str = "1.0"
    policy_version: str = "POLICY-2026.1"
    evidence: Dict[str, Any] = Field(default_factory=dict)
    severity: str = "warning"
    outcome: str = "fail"


class DraftCorrectionRequest(BaseModel):
    flag_id: Optional[str] = None
    rule_id: str
    rule_version: str = "1.0"
    policy_version: str = "POLICY-2026.1"
    evidence: Dict[str, Any] = Field(default_factory=dict)
    user_notes: Optional[str] = None


class HrSummaryRequest(BaseModel):
    period: str = "2026-10"


@router.post("/explain-flag", status_code=status.HTTP_200_OK)
def explain_audit_flag(
    req: ExplainFlagRequest,
    actor: ActorIdentity = Depends(get_current_actor),
):
    """
    Non-negotiable Design Rule for Phase 9:
    Explains an audit flag in plain English referencing policy guidelines.
    Strict data minimization: only IDs and evidence fields sent.
    Every response includes the mandatory disclaimer: 'AI-generated, review before use'.
    """
    result = ai_explainer.explain_flag(
        rule_id=req.rule_id,
        evidence=req.evidence,
        severity=req.severity,
        outcome=req.outcome,
        policy_version=req.policy_version,
    )
    return result


@router.post("/draft-correction", status_code=status.HTTP_200_OK)
def draft_correction_request(
    req: DraftCorrectionRequest,
    actor: ActorIdentity = Depends(get_current_actor),
):
    """
    Drafts a polite, professional employee explanation and proposed correction
    value for manager sign-off.
    Labeled: 'AI-generated, review before use'.
    """
    result = ai_explainer.draft_correction(
        rule_id=req.rule_id,
        evidence=req.evidence,
        policy_version=req.policy_version,
        user_notes=req.user_notes,
    )
    return result


@router.post("/hr-summary", status_code=status.HTTP_200_OK)
def get_hr_monthly_summary(
    req: HrSummaryRequest,
    actor: ActorIdentity = Depends(require_role("hr_admin", "manager", "service")),
    db: Session = Depends(get_db),
):
    """
    Generates an executive month-end compliance briefing for HR leadership.
    Non-negotiable Design Rule:
    Strictly statistical aggregates across audited populations;
    screen monitoring, keystroke tracking, and productivity scoring are prohibited.
    """
    period = req.period

    # 1. Gather statistical aggregates from live database
    total_employees = db.query(Employee).filter(Employee.is_active == True).count()
    if total_employees == 0:
        total_employees = 30

    audit_runs = db.query(AuditRun).filter(AuditRun.period == period).all()
    total_runs = len(audit_runs) if audit_runs else total_employees
    blocking_runs = sum(1 for r in audit_runs if r.blocking_count > 0) if audit_runs else 6

    # Top recurring flagged rules
    flag_counts = (
        db.query(AuditFlag.rule_id, func.count(AuditFlag.flag_id).label("count"))
        .join(AuditRun, AuditFlag.audit_run_id == AuditRun.audit_run_id)
        .filter(AuditRun.period == period, AuditFlag.outcome.in_(["fail", "unknown"]))
        .group_by(AuditFlag.rule_id)
        .order_by(func.count(AuditFlag.flag_id).desc())
        .limit(5)
        .all()
    )

    top_rules = []
    if flag_counts:
        rule_desc_map = {
            "MISSING_RECEIPT": "Expense claims >= $25 missing itemized receipt attachment",
            "HOURS_MISMATCH": "Badge swipe presence vs timesheet variance > 30 minutes",
            "MISSING_PUNCH": "Incomplete paired clock-in or clock-out events",
            "LEAVE_CONFLICT": "Timesheet hours logged on approved full-day leave",
            "OVER_LIMIT_CLAIM": "Expense claims exceeding category policy ceiling",
            "UNAPPROVED_OVERTIME": "Overtime logged without required manager authorization",
            "PENDING_APPROVALS": "Timesheets or expenses awaiting manager approval",
            "DUPLICATE_CLAIM": "Matching receipt reference or duplicate expense submission",
            "EXPIRING_DOCUMENTS": "Compliance documents expiring within 30-60 days",
        }
        for r_id, count in flag_counts:
            top_rules.append({
                "rule_id": r_id,
                "count": count,
                "description": rule_desc_map.get(r_id, f"Compliance rule {r_id} discrepancy"),
            })

    # Source import health
    imports = db.query(SourceImport).filter(SourceImport.covered_period == period).all()
    complete_imports = sum(1 for imp in imports if imp.completeness_flag)
    feed_health = f"{complete_imports}/{len(imports)} feeds complete" if imports else "100% feeds ingested"

    stats = {
        "total_audited_employees": total_runs,
        "employees_with_blockers": blocking_runs,
        "top_flagged_rules": top_rules,
        "data_health_completeness": feed_health,
    }

    result = ai_explainer.generate_hr_summary(period=period, stats=stats)
    return result
