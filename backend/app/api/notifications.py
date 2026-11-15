from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.security import get_current_actor, ActorIdentity
from app.models.hr import AuditEvent

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# In-memory delivery registry for deduplication cache in dev
_DELIVERED_FINGERPRINTS = set()


class DedupCheckRequest(BaseModel):
    employee_id: str
    fingerprint: str


class DispatchNotificationRequest(BaseModel):
    employee_id: str
    fingerprint: str
    message_body: str
    portal_url: str


@router.post("/check-dedup", status_code=status.HTTP_200_OK)
def check_deduplication(
    req: DedupCheckRequest,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Checks if identical unresolved flag notification was already sent.
    Deduplicates to prevent employee alert spam.
    """
    key = f"{req.employee_id}:{req.fingerprint}"
    is_duplicate = key in _DELIVERED_FINGERPRINTS

    # Also check audit_events table for persisted history
    if not is_duplicate:
        existing_event = db.query(AuditEvent).filter(
            AuditEvent.action_type == "DISPATCH_NOTIFICATION",
            AuditEvent.actor_id == req.employee_id,
            AuditEvent.target_id == req.fingerprint,
        ).first()
        if existing_event:
            is_duplicate = True
            _DELIVERED_FINGERPRINTS.add(key)

    return {"is_duplicate": is_duplicate, "fingerprint": req.fingerprint}


@router.post("/dispatch", status_code=status.HTTP_200_OK)
def dispatch_notification(
    req: DispatchNotificationRequest,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Dispatches a minimal, privacy-safe notification and records immutable delivery history.
    Enforces Non-negotiable Rule: ZERO sensitive payroll, receipt, or detailed punch data in body.
    """
    # Verify privacy constraints: ensure no sensitive keywords present in body
    forbidden_terms = ["salary", "wage", "ssn", "hourly_rate", "receipt_url", "punch_details"]
    lowered = req.message_body.lower()
    for term in forbidden_terms:
        if term in lowered:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security violation: Notification body contains sensitive term '{term}'.",
            )

    key = f"{req.employee_id}:{req.fingerprint}"
    _DELIVERED_FINGERPRINTS.add(key)

    # Record delivery history in immutable audit ledger
    db.add(AuditEvent(
        organization_id=actor.organization_id,
        actor_id=req.employee_id,
        actor_role="system",
        action_type="DISPATCH_NOTIFICATION",
        target_entity="notifications",
        target_id=req.fingerprint,
        payload_diff={
            "message_body": req.message_body,
            "portal_url": req.portal_url,
            "channel": "portal_link",
        }
    ))
    db.commit()

    return {
        "status": "delivered",
        "employee_id": req.employee_id,
        "fingerprint": req.fingerprint,
        "message_body": req.message_body,
    }
