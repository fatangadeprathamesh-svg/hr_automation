import hashlib
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.consent import ConsentLog

router = APIRouter(prefix="/api/consent", tags=["Consent"])


class ConsentChoices(BaseModel):
    necessary: bool = True
    preferences: bool = False
    analytics: bool = False


class ConsentRequest(BaseModel):
    anonymous_id: str = Field(..., description="Stable client-generated anonymous UUID")
    policy_version: str = Field("2026.1", description="Policy version consented to")
    choices: ConsentChoices = Field(..., description="Explicit choices per category")


@router.post("", status_code=201)
@router.post("/", status_code=201)
def record_consent(payload: ConsentRequest, request: Request, db: Session = Depends(get_db)):
    """
    Record proof of user consent for auditing under the DPDP Act 2023.
    Accepts anonymous identifiers with no personal data linkage.
    """
    user_agent = request.headers.get("user-agent", "")[:250]
    client_host = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_host.encode("utf-8")).hexdigest()[:32]

    log_entry = ConsentLog(
        anonymous_id=payload.anonymous_id,
        policy_version=payload.policy_version,
        necessary=True,  # strictly necessary is always true
        preferences=bool(payload.choices.preferences),
        analytics=bool(payload.choices.analytics),
        user_agent=user_agent,
        ip_hash=ip_hash,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    return {
        "status": "recorded",
        "id": log_entry.id,
        "anonymous_id": log_entry.anonymous_id,
        "policy_version": log_entry.policy_version,
        "choices": {
            "necessary": log_entry.necessary,
            "preferences": log_entry.preferences,
            "analytics": log_entry.analytics,
        },
        "created_at": log_entry.created_at.isoformat() if log_entry.created_at else None,
    }


@router.get("/{anonymous_id}")
def get_latest_consent(anonymous_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the most recent proof of consent for an anonymous client identifier.
    """
    record = (
        db.query(ConsentLog)
        .filter(ConsentLog.anonymous_id == anonymous_id)
        .order_by(desc(ConsentLog.created_at))
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="No consent record found for this identifier")

    return {
        "id": record.id,
        "anonymous_id": record.anonymous_id,
        "policy_version": record.policy_version,
        "choices": {
            "necessary": record.necessary,
            "preferences": record.preferences,
            "analytics": record.analytics,
        },
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
