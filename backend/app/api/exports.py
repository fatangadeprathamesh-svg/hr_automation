import os
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.security import get_current_actor, ActorIdentity
from app.exports.service import SubmissionGateService
from app.models.hr import ExportRun

router = APIRouter(prefix="/exports", tags=["Exports & Payroll Packs"])


class CreateExportRequest(BaseModel):
    snapshot_id: str
    export_type: str = "PDF_JSON_PACK"
    destination_system: str = "payroll_staging"


class DeliverDestinationRequest(BaseModel):
    export_run_id: str
    destination: str = "payroll_staging"


@router.post("", status_code=status.HTTP_201_CREATED)
def create_export(
    req: CreateExportRequest,
    x_idempotency_key: Optional[str] = Header(None),
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Generates identical PDF and JSON packs from the frozen snapshot.
    Handles repeated export attempts idempotently.
    """
    if actor.role not in ("hr_admin", "service"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only HR administrators or service accounts can generate export packs.",
        )

    result = SubmissionGateService.generate_export_pack(
        db=db,
        snapshot_id=req.snapshot_id,
        export_type=req.export_type,
        destination_system=req.destination_system,
        idempotency_key=x_idempotency_key,
    )
    return result


@router.get("", status_code=status.HTTP_200_OK)
def list_exports(
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Lists all generated export runs with status and download references."""
    runs = db.query(ExportRun).order_by(ExportRun.created_at.desc()).all()
    return [
        {
            "export_run_id": run.export_run_id,
            "snapshot_id": run.snapshot_id,
            "export_type": run.export_type,
            "pack_pdf_uri": run.pack_pdf_uri,
            "pack_json_uri": run.pack_json_uri,
            "status": run.status,
            "destination_system": run.destination_system,
            "delivery_acknowledgement": run.delivery_acknowledgement,
            "created_at": run.created_at,
        }
        for run in runs
    ]


@router.get("/{export_run_id}")
def get_export_status(
    export_run_id: str,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Retrieves export run details, file URIs, and delivery state."""
    run = db.query(ExportRun).filter(ExportRun.export_run_id == export_run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export run not found.")

    return {
        "export_run_id": run.export_run_id,
        "snapshot_id": run.snapshot_id,
        "export_type": run.export_type,
        "pack_pdf_uri": run.pack_pdf_uri,
        "pack_json_uri": run.pack_json_uri,
        "status": run.status,
        "destination_system": run.destination_system,
        "delivery_acknowledgement": run.delivery_acknowledgement,
        "created_at": run.created_at,
    }


@router.get("/{export_run_id}/download/{file_type}")
def download_export_file(
    export_run_id: str,
    file_type: str,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Serves the generated PDF or JSON audit pack file for viewing or downloading."""
    run = db.query(ExportRun).filter(ExportRun.export_run_id == export_run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export run not found.")

    file_type = file_type.lower()
    if file_type == "pdf":
        file_path = run.pack_pdf_uri
        media_type = "application/pdf"
    elif file_type == "json":
        file_path = run.pack_json_uri
        media_type = "application/json"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_type must be 'pdf' or 'json'.")

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file does not exist on disk.")

    filename = os.path.basename(file_path)
    return FileResponse(file_path, media_type=media_type, filename=filename)


@router.post("/deliver-destination", status_code=status.HTTP_200_OK)
def deliver_export_to_destination(
    req: DeliverDestinationRequest,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Reconciles acknowledgement and finalizes delivery to destination system."""
    if actor.role not in ("service", "hr_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return SubmissionGateService.reconcile_and_deliver(
        db=db,
        export_run_id=req.export_run_id,
        destination=req.destination,
    )
