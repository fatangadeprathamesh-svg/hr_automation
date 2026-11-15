from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.security import get_current_actor, ActorIdentity
from app.workflow.service import WorkflowService
from app.models.hr import Correction, Employee

router = APIRouter(prefix="/corrections", tags=["Corrections & Workflow"])


class SubmitCorrectionRequest(BaseModel):
    flag_id: Optional[str] = None
    entity_name: str
    entity_id: str
    proposed_data: Dict[str, Any]
    employee_reason: str = Field(..., min_length=3)


class CorrectionDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")
    manager_reason: str = Field(..., min_length=3)


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_correction(
    req: SubmitCorrectionRequest,
    x_idempotency_key: Optional[str] = Header(None),
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Submits an employee correction request bound to the current record_version of the entity.
    """
    if actor.role not in ("employee", "service", "hr_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employees can submit self-audit corrections.",
        )

    result = WorkflowService.submit_correction(
        db=db,
        employee_id=actor.actor_id,
        flag_id=req.flag_id,
        entity_name=req.entity_name.lower().strip(),
        entity_id=req.entity_id,
        proposed_data=req.proposed_data,
        employee_reason=req.employee_reason,
        organization_id=actor.organization_id,
    )
    return result


@router.post("/{correction_id}/decision", status_code=status.HTTP_200_OK)
def decide_correction(
    correction_id: str,
    req: CorrectionDecisionRequest,
    x_idempotency_key: Optional[str] = Header(None),
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Records a version-bound manager approval or rejection.
    Re-checks state transactionally and rejects stale decisions (HTTP 409).
    """
    if actor.role not in ("manager", "hr_admin", "service"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only assigned managers or HR administrators can make correction decisions.",
        )

    result = WorkflowService.decide_correction(
        db=db,
        correction_id=correction_id,
        reviewer_id=actor.actor_id,
        reviewer_role=actor.role,
        decision=req.decision,
        manager_reason=req.manager_reason,
        organization_id=actor.organization_id,
    )
    return result


@router.get("/pending", status_code=status.HTTP_200_OK)
def list_pending_corrections(
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Retrieves pending corrections:
    - For Managers: corrections submitted by direct reports with before/after diffs.
    - For Employees: corrections submitted by self.
    - For HR/Service: all pending corrections.
    """
    query = db.query(Correction)

    if actor.role == "manager":
        # Find direct reports
        reports = db.query(Employee.employee_id).filter(Employee.manager_id == actor.actor_id).all()
        report_ids = [r[0] for r in reports]
        query = query.filter(Correction.employee_id.in_(report_ids), Correction.status == "pending_review")

    elif actor.role == "employee":
        query = query.filter(Correction.employee_id == actor.actor_id)

    else:
        # HR Admin or Service
        query = query.filter(Correction.status == "pending_review")

    corrections = query.order_by(Correction.requested_at.desc()).all()

    return [
        {
            "correction_id": c.correction_id,
            "flag_id": c.flag_id,
            "employee_id": c.employee_id,
            "entity_name": c.entity_name,
            "entity_id": c.entity_id,
            "original_record_version": c.original_record_version,
            "original_data": c.original_data,
            "proposed_data": c.proposed_data,
            "employee_reason": c.employee_reason,
            "status": c.status,
            "requested_at": c.requested_at,
        }
        for c in corrections
    ]
