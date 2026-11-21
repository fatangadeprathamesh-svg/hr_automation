import os
import uuid
import hashlib
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc
from app.database import get_db
from app.config import settings
from app.auth.security import get_current_actor, ActorIdentity, require_role
from app.models.master_hr import MasterUpload, MasterHRRecord
from app.services.master_import_service import MasterImportService

router = APIRouter(tags=["Master HR Uploads"])

TEMP_DIR = Path("temp_uploads")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/api/uploads", status_code=status.HTTP_202_ACCEPTED)
async def upload_master_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    actor: ActorIdentity = Depends(require_role("hr_admin", "hr", "service")),
    db: Session = Depends(get_db),
):
    """
    Upload one master HR CSV file.
    Accepts .csv only, with size limit (default 200MB).
    Streams chunks directly to temp file without loading into memory.
    Launches background processing task and returns immediately.
    """
    filename = file.filename or "master_hr.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only .csv files are supported.",
        )

    upload_id = str(uuid.uuid4())
    temp_file_path = TEMP_DIR / f"upload_{upload_id}.csv"
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total_bytes = 0
    hasher = hashlib.sha256()

    # Stream chunks to temp file
    try:
        with open(temp_file_path, "wb") as out_f:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunk
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    out_f.close()
                    if temp_file_path.exists():
                        temp_file_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
                    )
                hasher.update(chunk)
                out_f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if temp_file_path.exists():
            temp_file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving uploaded file: {str(e)}",
        )

    file_sha256 = hasher.hexdigest()

    # Check for idempotent re-upload / duplicate file warning
    prev_upload = db.query(MasterUpload).filter(
        MasterUpload.sha256 == file_sha256,
        MasterUpload.status == "done"
    ).first()
    duplicate_warning = (prev_upload is not None)

    # Create upload record
    upload_record = MasterUpload(
        id=upload_id,
        filename=filename,
        sha256=file_sha256,
        uploaded_by=actor.actor_id,
        status="queued",
        total_rows=0,
        accepted_rows=0,
        rejected_rows=0,
        duplicate_warning=duplicate_warning,
    )
    db.add(upload_record)
    db.commit()

    # Launch background streaming processor
    background_tasks.add_task(
        MasterImportService.process_upload_task,
        upload_id,
        str(temp_file_path),
        actor.actor_id,
        actor.organization_id,
        actor.role,
    )

    return {
        "upload_id": upload_id,
        "filename": filename,
        "sha256": file_sha256,
        "status": "queued",
        "duplicate_warning": duplicate_warning,
        "message": "File accepted and queued for background ingestion."
    }


@router.get("/api/uploads/{upload_id}")
def get_upload_status(
    upload_id: str,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Retrieves status and live progress of a specific upload."""
    upload = db.query(MasterUpload).filter(MasterUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload batch '{upload_id}' not found.",
        )

    rows_per_second = 0.0
    if upload.duration_seconds and upload.duration_seconds > 0:
        rows_per_second = round(upload.total_rows / upload.duration_seconds, 1)

    return {
        "id": upload.id,
        "filename": upload.filename,
        "sha256": upload.sha256,
        "uploaded_by": upload.uploaded_by,
        "uploaded_at": upload.uploaded_at.isoformat() if upload.uploaded_at else None,
        "status": upload.status,
        "total_rows": upload.total_rows,
        "accepted_rows": upload.accepted_rows,
        "rejected_rows": upload.rejected_rows,
        "duration_seconds": upload.duration_seconds,
        "rows_per_second": rows_per_second,
        "duplicate_warning": upload.duplicate_warning,
        "error_message": upload.error_message,
    }


@router.get("/api/uploads/{upload_id}/rejected")
def get_rejected_rows(
    upload_id: str,
    format: Optional[str] = Query(None, description="Set to 'csv' to download as CSV file"),
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Returns rejected rows for an upload.
    If format=csv, streams a downloadable CSV file.
    """
    upload = db.query(MasterUpload).filter(MasterUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload batch '{upload_id}' not found.",
        )

    rejected_csv_path = TEMP_DIR / f"rejected_{upload_id}.csv"

    if format == "csv":
        if rejected_csv_path.exists():
            return FileResponse(
                path=str(rejected_csv_path),
                filename=f"rejected_rows_{upload_id}.csv",
                media_type="text/csv",
            )
        else:
            # Fall back to generating from JSON if file was cleaned
            import io
            import csv
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["row_num", "record_id", "reason", "raw_preview"])
            for r in (upload.rejected_details or []):
                writer.writerow([r.get("row_num"), r.get("record_id"), r.get("reason"), r.get("raw_preview")])
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=rejected_rows_{upload_id}.csv"},
            )

    return {
        "upload_id": upload.id,
        "rejected_count": upload.rejected_rows,
        "rejected_rows": upload.rejected_details or [],
    }


@router.get("/api/uploads")
def get_upload_history(
    limit: int = Query(50, ge=1, le=200),
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Returns upload history ordered by upload date descending."""
    uploads = db.query(MasterUpload).order_by(desc(MasterUpload.uploaded_at)).limit(limit).all()

    items = []
    for u in uploads:
        rps = round(u.total_rows / u.duration_seconds, 1) if u.duration_seconds and u.duration_seconds > 0 else 0.0
        items.append({
            "id": u.id,
            "filename": u.filename,
            "sha256": u.sha256,
            "uploaded_by": u.uploaded_by,
            "uploaded_at": u.uploaded_at.isoformat() if u.uploaded_at else None,
            "status": u.status,
            "total_rows": u.total_rows,
            "accepted_rows": u.accepted_rows,
            "rejected_rows": u.rejected_rows,
            "duration_seconds": u.duration_seconds,
            "rows_per_second": rps,
            "duplicate_warning": u.duplicate_warning,
            "error_message": u.error_message,
        })

    return {"uploads": items}


@router.get("/api/records")
def get_master_records(
    page: int = 1,
    page_size: int = 50,
    record_type: Optional[str] = None,
    department: Optional[str] = None,
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Server-side paginated retrieval of Master HR Records.
    Supports filtering by record_type, department, employee_id, status, date range, and text search.
    Never returns all rows at once.
    """
    query = db.query(MasterHRRecord)

    # Sanitize pagination limits
    page = max(1, int(page) if isinstance(page, (int, str)) else 1)
    page_size = min(200, max(1, int(page_size) if isinstance(page_size, (int, str)) else 50))

    if record_type and isinstance(record_type, str):
        query = query.filter(MasterHRRecord.record_type == record_type.strip().lower())
    if department and isinstance(department, str):
        query = query.filter(MasterHRRecord.department == department.strip())
    if employee_id and isinstance(employee_id, str):
        query = query.filter(MasterHRRecord.employee_id == employee_id.strip())
    if status and isinstance(status, str):
        query = query.filter(MasterHRRecord.status == status.strip())
    if start_date and isinstance(start_date, str):
        try:
            d_val = datetime.strptime(start_date.strip(), "%Y-%m-%d").date()
            query = query.filter(
                or_(
                    MasterHRRecord.event_date >= d_val,
                    MasterHRRecord.start_date >= d_val,
                    MasterHRRecord.hire_date >= d_val,
                )
            )
        except ValueError:
            pass
    if end_date and isinstance(end_date, str):
        try:
            d_val = datetime.strptime(end_date.strip(), "%Y-%m-%d").date()
            query = query.filter(
                or_(
                    MasterHRRecord.event_date <= d_val,
                    MasterHRRecord.end_date <= d_val,
                    MasterHRRecord.exit_date <= d_val,
                )
            )
        except ValueError:
            pass
    if search and isinstance(search, str):
        s_term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(MasterHRRecord.employee_name).like(s_term),
                func.lower(MasterHRRecord.first_name).like(s_term),
                func.lower(MasterHRRecord.last_name).like(s_term),
                func.lower(MasterHRRecord.employee_id).like(s_term),
                func.lower(MasterHRRecord.record_id).like(s_term),
            )
        )

    total = query.count()
    offset = (page - 1) * page_size
    records = query.order_by(desc(MasterHRRecord.created_at)).offset(offset).limit(page_size).all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    items = []
    for r in records:
        items.append({
            "record_id": r.record_id,
            "upload_id": r.upload_id,
            "record_type": r.record_type,
            "employee_id": r.employee_id,
            "applicant_id": r.applicant_id,
            "employee_name": r.employee_name,
            "department": r.department,
            "position": r.position,
            "division": r.division,
            "manager": r.manager,
            "event_date": r.event_date.isoformat() if r.event_date else None,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "status": r.status,
            "category": r.category,
            "days": r.days,
            "hours_total": r.hours_total,
            "hours_scheduled": r.hours_scheduled,
            "leave_remaining": r.leave_remaining,
            "training_program": r.training_program,
            "engagement_score": r.engagement_score,
            "monthly_income": r.monthly_income,
            "source_file": r.source_file,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/api/stats")
def get_master_stats(
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Returns row count per record_type and key operational totals:
    - leave days total
    - timesheet hours total
    - unapproved timesheets count
    - total employees
    - total applicants
    """
    total_records = db.query(MasterHRRecord).count()

    # Counts by record_type
    counts_by_type = dict(
        db.query(MasterHRRecord.record_type, func.count(MasterHRRecord.record_id))
        .group_by(MasterHRRecord.record_type)
        .all()
    )

    # Simple Totals
    leave_days_sum = (
        db.query(func.coalesce(func.sum(MasterHRRecord.days), 0.0))
        .filter(MasterHRRecord.record_type == "leave_request")
        .scalar()
    ) or 0.0

    timesheet_hours_sum = (
        db.query(func.coalesce(func.sum(MasterHRRecord.hours_total), 0.0))
        .filter(MasterHRRecord.record_type == "timesheet")
        .scalar()
    ) or 0.0

    unapproved_timesheets_count = (
        db.query(func.count(MasterHRRecord.record_id))
        .filter(
            MasterHRRecord.record_type == "timesheet",
            or_(
                MasterHRRecord.status == None,
                MasterHRRecord.status != "approved",
            )
        )
        .scalar()
    ) or 0

    return {
        "total_records": total_records,
        "by_record_type": {
            "employee_profile": counts_by_type.get("employee_profile", 0),
            "leave_request": counts_by_type.get("leave_request", 0),
            "leave_balance": counts_by_type.get("leave_balance", 0),
            "timesheet": counts_by_type.get("timesheet", 0),
            "training": counts_by_type.get("training", 0),
            "engagement_survey": counts_by_type.get("engagement_survey", 0),
            "applicant": counts_by_type.get("applicant", 0),
        },
        "totals": {
            "leave_days_total": round(float(leave_days_sum), 2),
            "timesheet_hours_total": round(float(timesheet_hours_sum), 2),
            "unapproved_timesheets": int(unapproved_timesheets_count),
            "employees_count": counts_by_type.get("employee_profile", 0),
            "applicants_count": counts_by_type.get("applicant", 0),
        }
    }
