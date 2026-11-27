from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.database import get_db
from app.auth.security import get_current_actor, ActorIdentity
from app.exports.service import SubmissionGateService
from app.models.hr import SubmissionPack, Employee

router = APIRouter(prefix="/submissions", tags=["Submissions & Snapshots"])


class CreateSubmissionRequest(BaseModel):
    period: str = Field(..., pattern=r"^\d{4}-\d{2}$")


class HRDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|returned)$")
    hr_reason: str = Field(..., min_length=3)
    assigned_owner: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_month_end(
    req: CreateSubmissionRequest,
    x_idempotency_key: Optional[str] = Header(None),
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Submission Gate: Revalidates blockers, feed completeness, and approvals.
    Freezes point-in-time snapshot of the employee's period state.
    """
    if actor.role not in ("employee", "hr_admin", "service"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only employees or HR administrators can submit month-end packs.",
        )

    result = SubmissionGateService.evaluate_and_freeze_submission(
        db=db,
        employee_id=actor.actor_id,
        period=req.period,
        actor_id=actor.actor_id,
        organization_id=actor.organization_id,
    )
    return result


@router.post("/{snapshot_id}/hr-decision", status_code=status.HTTP_200_OK)
def hr_decision_on_submission(
    snapshot_id: str,
    req: HRDecisionRequest,
    x_idempotency_key: Optional[str] = Header(None),
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    HR Review: Approves submission pack for export OR returns with reason and remediation owner.
    """
    if actor.role not in ("hr_admin", "service"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only HR administrators can make submission decisions.",
        )

    result = SubmissionGateService.hr_review_decision(
        db=db,
        snapshot_id=snapshot_id,
        hr_actor_id=actor.actor_id,
        decision=req.decision,
        reason=req.hr_reason,
        assigned_owner=req.assigned_owner,
        organization_id=actor.organization_id,
    )
    return result


@router.get("", status_code=status.HTTP_200_OK)
def list_submissions(
    period: Optional[str] = None,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Retrieves submission packs:
    - For Employees: own submission packs.
    - For Managers: direct reports' submissions + own.
    - For HR / Service: all submission packs (filtered by period if provided).
    """
    query = db.query(SubmissionPack)
    if actor.role == "employee":
        clean_email = (actor.email or "").strip().lower()
        candidate_emails = [clean_email]
        if "@example.com" in clean_email:
            candidate_emails.append(clean_email.replace("@example.com", "@company.com"))
        elif "@company.com" in clean_email:
            candidate_emails.append(clean_email.replace("@company.com", "@example.com"))

        emp = db.query(Employee).filter(
            or_(
                Employee.employee_id == actor.actor_id,
                *[func.lower(Employee.email) == ce for ce in candidate_emails]
            )
        ).first()
        target_id = emp.employee_id if emp else actor.actor_id
        query = query.filter(SubmissionPack.employee_id == target_id)
    elif actor.role == "manager":
        mgr_emp = db.query(Employee).filter(
            or_(
                Employee.employee_id == actor.actor_id,
                func.lower(Employee.email) == (actor.email or "").lower()
            )
        ).first()
        mgr_name = mgr_emp.full_name if mgr_emp else actor.actor_id
        team_emps = db.query(Employee).filter(
            or_(
                Employee.manager == mgr_name,
                Employee.manager_id == actor.actor_id,
                Employee.employee_id == actor.actor_id
            )
        ).all()
        team_ids = [e.employee_id for e in team_emps] or [actor.actor_id]
        query = query.filter(SubmissionPack.employee_id.in_(team_ids))
    elif actor.role not in ("hr_admin", "hr", "service"):
        query = query.filter(SubmissionPack.employee_id == actor.actor_id)

    if period:
        query = query.filter(SubmissionPack.period == period)
    packs = query.order_by(SubmissionPack.submitted_at.desc()).all()
    return [
        {
            "snapshot_id": p.snapshot_id,
            "employee_id": p.employee_id,
            "period": p.period,
            "policy_version": p.policy_version,
            "status": p.status,
            "submitted_at": p.submitted_at,
            "hr_reviewer_id": p.hr_reviewer_id,
            "hr_decision": p.hr_decision,
            "hr_return_reason": p.hr_return_reason,
            "frozen_data": p.frozen_data,
        }
        for p in packs
    ]


@router.get("/{snapshot_id}")
def get_submission_snapshot(
    snapshot_id: str,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Retrieves frozen submission pack snapshot."""
    pack = db.query(SubmissionPack).filter(SubmissionPack.snapshot_id == snapshot_id).first()
    if not pack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")

    # Cross-employee access check
    if actor.role == "employee" and pack.employee_id != actor.actor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return {
        "snapshot_id": pack.snapshot_id,
        "employee_id": pack.employee_id,
        "period": pack.period,
        "policy_version": pack.policy_version,
        "status": pack.status,
        "submitted_at": pack.submitted_at,
        "hr_reviewer_id": pack.hr_reviewer_id,
        "hr_decision": pack.hr_decision,
        "hr_return_reason": pack.hr_return_reason,
        "frozen_data": pack.frozen_data,
    }
