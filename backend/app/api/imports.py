from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.security import get_current_actor, ActorIdentity, require_role
from app.imports.service import IngestionService
from app.models.hr import SourceImport

router = APIRouter(prefix="/imports", tags=["Imports"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_import(
    source_system: str = Form(...),
    covered_period: str = Form(...),
    is_complete_feed: bool = Form(True),
    file: UploadFile = File(...),
    x_idempotency_key: Optional[str] = Header(None),
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Ingests source CSV data into the database ledger with strict provenance,
    foreign key validation, and replay prevention.
    """
    # Authorization: Only service or HR Admin can perform imports
    if actor.role not in ("service", "hr_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only service accounts or HR administrators can trigger source imports.",
        )

    content_bytes = await file.read()
    try:
        content_str = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content must be UTF-8 encoded text.",
        )

    result = IngestionService.ingest_csv(
        db=db,
        organization_id=actor.organization_id,
        source_system=source_system.strip().lower(),
        covered_period=covered_period.strip(),
        file_content=content_str,
        actor_id=actor.actor_id,
        raw_file_uri=f"uploads://{file.filename}",
        is_complete_feed=is_complete_feed,
    )

    return result


@router.get("/{import_id}")
def get_import(
    import_id: str,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Retrieves metadata and status for a specific source import batch."""
    record = db.query(SourceImport).filter(
        SourceImport.import_id == import_id,
        SourceImport.organization_id == actor.organization_id,
    ).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Import batch '{import_id}' not found.",
        )

    return {
        "import_id": record.import_id,
        "organization_id": record.organization_id,
        "source_system": record.source_system,
        "covered_period": record.covered_period,
        "status": record.status,
        "completeness_flag": record.completeness_flag,
        "imported_at": record.imported_at,
        "validation_errors": record.validation_errors,
        "raw_file_uri": record.raw_file_uri,
    }
