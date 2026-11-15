from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.security import get_current_actor, ActorIdentity
from app.rules.engine import AuditEngine
from app.models.hr import AuditRun, AuditFlag, SourceImport, Employee

router = APIRouter(tags=["Audit"])


class AuditRunRequest(BaseModel):
    employee_id: str
    period: str
    trigger: str = "manual"
    policy_version: Optional[str] = None


@router.post("/audit-runs", status_code=status.HTTP_200_OK)
def trigger_audit_run(
    req: AuditRunRequest,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Executes deterministic audit rules for an employee and period.
    Adheres strictly to the contract defined in Section 4 of the Implementation Guide.
    """
    # Authorization: Employees can only audit themselves; Managers can audit their direct reports; HR/service can audit all.
    if actor.role == "employee" and actor.actor_id != req.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Employee '{actor.actor_id}' cannot execute audit run for employee '{req.employee_id}'.",
        )

    engine = AuditEngine()
    result = engine.run_audit(
        db=db,
        employee_id=req.employee_id,
        period=req.period,
        trigger_source=req.trigger,
        policy_version_id=req.policy_version,
    )
    return result


@router.get("/employees/me/readiness")
def get_my_readiness(
    period: str = Query("2026-10", description="Audit period format YYYY-MM"),
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Returns current month-end self-audit readiness for the authenticated employee.
    Derives employee_id server-side from actor.actor_id.
    """
    employee_id = actor.actor_id

    # Run fresh audit to ensure up-to-the-second state
    engine = AuditEngine()
    audit_summary = engine.run_audit(
        db=db,
        employee_id=employee_id,
        period=period,
        trigger_source="readiness_check",
    )

    all_flags = audit_summary.get("flags", [])
    blocking_issues = [f for f in all_flags if f["status"] == "fail" and f["severity"] == "blocking"]
    warnings = [f for f in all_flags if f["severity"] == "warning"]
    passed_checks = [f for f in all_flags if f["status"] == "pass"]
    applicable_checks = [f for f in all_flags if f["status"] in ("pass", "fail", "unknown")]

    total_applicable = len(applicable_checks)
    if total_applicable > 0:
        readiness_score = round((len(passed_checks) / total_applicable) * 100.0, 1)
    else:
        readiness_score = 100.0

    # Non-negotiable Rule 6: Submission gate.
    # Readiness percentage is informational only and MUST NEVER override a blocker.
    submission_allowed = (len(blocking_issues) == 0 and audit_summary["data_health"] == "complete")

    # Source coverage
    imports = db.query(SourceImport).filter(SourceImport.covered_period == period).all()
    feed_status = {}
    for imp in imports:
        feed_status[imp.source_system] = "complete" if imp.completeness_flag else "incomplete"

    return {
        "employee_id": employee_id,
        "period": period,
        "data_health": audit_summary["data_health"],
        "readiness_score": readiness_score,
        "readiness_formula": "readiness_score = (passed_checks / total_applicable_checks) * 100 (Informational only; blockers prevent submission)",
        "submission_allowed": submission_allowed,
        "blocking_count": len(blocking_issues),
        "warning_count": len(warnings),
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "source_coverage": feed_status,
        "latest_audit_run_id": audit_summary["audit_run_id"],
    }
