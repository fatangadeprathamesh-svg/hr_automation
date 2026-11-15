from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.security import get_current_actor, ActorIdentity
from app.models.hr import ExternalEnrichment
from app.models.base import generate_uuid

router = APIRouter(prefix="/enrichments", tags=["External Enrichment"])


class EnrichmentSaveRequest(BaseModel):
    entity_type: str
    entity_id: str
    provider: str = "crustdata"
    query_key: str
    provider_response: Dict[str, Any]
    review_status: str = "unreviewed"


@router.post("", status_code=status.HTTP_201_CREATED)
def record_external_enrichment(
    req: EnrichmentSaveRequest,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Non-negotiable Design Rule 9:
    Writes to a separate external_enrichments table.
    NEVER overwrites employee master data, NEVER affects payroll.
    Failure or unavailability of enrichment provider NEVER blocks core audit.
    """
    enrichment = ExternalEnrichment(
        enrichment_id=generate_uuid(),
        entity_type=req.entity_type,
        entity_id=req.entity_id,
        provider=req.provider,
        query_key=req.query_key,
        provider_response=req.provider_response,
        review_status=req.review_status,
    )
    db.add(enrichment)
    db.commit()
    db.refresh(enrichment)

    return {
        "enrichment_id": enrichment.enrichment_id,
        "entity_id": enrichment.entity_id,
        "provider": enrichment.provider,
        "review_status": enrichment.review_status,
        "retrieved_at": enrichment.retrieved_at,
    }
