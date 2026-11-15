from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.hr import (
    Employee,
    Attendance,
    Timesheet,
    ExpenseClaim,
    AuditFlag,
    Correction,
    Approval,
    AuditEvent,
    PolicyVersion,
)
from app.models.base import generate_uuid
from app.rules.engine import AuditEngine, DEFAULT_POLICY_VERSION


class WorkflowService:
    @staticmethod
    def submit_correction(
        db: Session,
        employee_id: str,
        flag_id: Optional[str],
        entity_name: str,
        entity_id: str,
        proposed_data: Dict[str, Any],
        employee_reason: str,
        organization_id: str,
    ) -> Dict[str, Any]:
        """
        Creates a pending correction request bound to the current record_version of the entity.
        Enforces Non-negotiable Rule 5: Decision version binding.
        """
        # 1. Fetch target entity and verify ownership
        entity, current_version, original_data = WorkflowService._get_entity_and_version(
            db, entity_name, entity_id, employee_id
        )

        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity '{entity_name}' with ID '{entity_id}' not found for employee '{employee_id}'.",
            )

        correction = Correction(
            correction_id=generate_uuid(),
            flag_id=flag_id,
            employee_id=employee_id,
            entity_name=entity_name,
            entity_id=entity_id,
            original_record_version=current_version,
            original_data=original_data,
            proposed_data=proposed_data,
            employee_reason=employee_reason,
            status="pending_review",
            requested_at=datetime.now(timezone.utc),
        )
        db.add(correction)

        # Audit Event log
        db.add(AuditEvent(
            organization_id=organization_id,
            actor_id=employee_id,
            actor_role="employee",
            action_type="SUBMIT_CORRECTION",
            target_entity=entity_name,
            target_id=entity_id,
            payload_diff={
                "correction_id": correction.correction_id,
                "bound_record_version": current_version,
                "original_data": original_data,
                "proposed_data": proposed_data,
                "reason": employee_reason,
            }
        ))

        db.commit()
        db.refresh(correction)

        return {
            "correction_id": correction.correction_id,
            "status": correction.status,
            "bound_record_version": correction.original_record_version,
            "entity_name": correction.entity_name,
            "entity_id": correction.entity_id,
            "requested_at": correction.requested_at,
        }

    @staticmethod
    def decide_correction(
        db: Session,
        correction_id: str,
        reviewer_id: str,
        reviewer_role: str,
        decision: str,  # "approved" or "rejected"
        manager_reason: str,
        organization_id: str,
    ) -> Dict[str, Any]:
        """
        Evaluates a correction decision with strict optimistic concurrency checking
        and version binding. Re-audits automatically upon approval.
        """
        # Fetch correction
        correction = db.query(Correction).filter(Correction.correction_id == correction_id).first()
        if not correction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Correction '{correction_id}' not found.",
            )

        if correction.status != "pending_review":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Correction '{correction_id}' is already in status '{correction.status}'.",
            )

        # Verify manager authority: reviewer must be assigned manager or hr_admin/service
        employee = db.query(Employee).filter(Employee.employee_id == correction.employee_id).first()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")

        if reviewer_role == "manager" and employee.manager_id != reviewer_id:
            # Unauthorized manager access attempt - Log security event!
            db.add(AuditEvent(
                organization_id=organization_id,
                actor_id=reviewer_id,
                actor_role="manager",
                action_type="UNAUTHORIZED_DECISION_ATTEMPT",
                target_entity="corrections",
                target_id=correction_id,
                payload_diff={"attempted_target_employee": employee.employee_id, "actual_manager": employee.manager_id}
            ))
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Reviewer '{reviewer_id}' is not the assigned manager for employee '{employee.employee_id}'.",
            )

        # 2. Transactionally recheck target entity with row-level lock
        entity, current_version, _ = WorkflowService._get_entity_and_version(
            db, correction.entity_name, correction.entity_id, correction.employee_id, lock_for_update=True
        )

        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target entity '{correction.entity_name}' '{correction.entity_id}' no longer exists.",
            )

        # Optimistic concurrency check: Reject stale decisions!
        if current_version != correction.original_record_version:
            db.add(AuditEvent(
                organization_id=organization_id,
                actor_id=reviewer_id,
                actor_role=reviewer_role,
                action_type="CONCURRENCY_CONFLICT_REJECTED",
                target_entity=correction.entity_name,
                target_id=correction.entity_id,
                payload_diff={
                    "correction_bound_version": correction.original_record_version,
                    "actual_current_version": current_version,
                }
            ))
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Concurrency Conflict: Record was modified (current version: {current_version}) after correction was submitted (bound version: {correction.original_record_version}). Stale decision rejected.",
            )

        # Get active policy version
        active_policy = db.query(PolicyVersion).filter(PolicyVersion.is_active == True).first()
        policy_v = active_policy.policy_version if active_policy else DEFAULT_POLICY_VERSION

        # 3. Create Approval record
        approval = Approval(
            approval_id=generate_uuid(),
            correction_id=correction.correction_id,
            reviewer_id=reviewer_id,
            bound_record_version=current_version,
            bound_policy_version=policy_v,
            decision=decision,
            manager_reason=manager_reason,
            decided_at=datetime.now(timezone.utc),
        )
        db.add(approval)

        # 4. Apply changes if approved
        correction.status = decision
        if decision == "approved":
            WorkflowService._apply_entity_changes(entity, correction.proposed_data)
            # Increment record version
            entity.record_version = current_version + 1
            db.add(entity)

            # Resolve linked flag if exists
            if correction.flag_id:
                flag = db.query(AuditFlag).filter(AuditFlag.flag_id == correction.flag_id).first()
                if flag:
                    flag.resolution_status = "corrected"
                    db.add(flag)

        # Log audit event
        db.add(AuditEvent(
            organization_id=organization_id,
            actor_id=reviewer_id,
            actor_role=reviewer_role,
            action_type="DECIDE_CORRECTION",
            target_entity="corrections",
            target_id=correction.correction_id,
            payload_diff={
                "decision": decision,
                "bound_record_version": current_version,
                "new_record_version": entity.record_version if decision == "approved" else current_version,
                "manager_reason": manager_reason,
            }
        ))

        db.commit()

        # 5. Automatically re-audit if approved to refresh employee readiness!
        re_audit_summary = None
        if decision == "approved":
            engine = AuditEngine()
            # Determine period from work_date or claim_date
            period_str = WorkflowService._extract_period(entity)
            if period_str:
                re_audit_summary = engine.run_audit(
                    db=db,
                    employee_id=correction.employee_id,
                    period=period_str,
                    trigger_source="correction_approved",
                )

        return {
            "approval_id": approval.approval_id,
            "correction_id": correction.correction_id,
            "decision": decision,
            "bound_record_version": current_version,
            "new_record_version": entity.record_version if decision == "approved" else current_version,
            "status": correction.status,
            "re_audit_summary": re_audit_summary,
        }

    @staticmethod
    def _get_entity_and_version(
        db: Session, entity_name: str, entity_id: str, employee_id: str, lock_for_update: bool = False
    ):
        query = None
        if entity_name == "attendance":
            query = db.query(Attendance).filter(
                (Attendance.id == entity_id) | (Attendance.source_record_id == entity_id),
                Attendance.employee_id == employee_id,
            )
        elif entity_name in ("timesheet", "timesheets"):
            query = db.query(Timesheet).filter(
                (Timesheet.id == entity_id) | (Timesheet.source_record_id == entity_id),
                Timesheet.employee_id == employee_id,
            )
        elif entity_name in ("expense_claim", "expense_claims"):
            query = db.query(ExpenseClaim).filter(
                (ExpenseClaim.id == entity_id) | (ExpenseClaim.source_record_id == entity_id),
                ExpenseClaim.employee_id == employee_id,
            )
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid entity_name '{entity_name}'.")

        if lock_for_update:
            # Apply row-level lock where supported
            query = query.with_for_update()

        entity = query.first()
        if not entity:
            return None, None, None

        # Build original data snapshot
        original_data = {}
        if entity_name == "attendance":
            original_data = {
                "work_date": str(entity.work_date),
                "clock_in": entity.clock_in.isoformat() if entity.clock_in else None,
                "clock_out": entity.clock_out.isoformat() if entity.clock_out else None,
                "timezone": entity.timezone,
            }
        elif entity_name in ("timesheet", "timesheets"):
            original_data = {
                "work_date": str(entity.work_date),
                "regular_hours": float(entity.regular_hours or 0.0),
                "overtime_hours": float(entity.overtime_hours or 0.0),
            }
        elif entity_name in ("expense_claim", "expense_claims"):
            original_data = {
                "claim_date": str(entity.claim_date),
                "amount": float(entity.amount or 0.0),
                "category": entity.category,
                "receipt_reference": entity.receipt_reference,
            }

        return entity, entity.record_version, original_data

    @staticmethod
    def _apply_entity_changes(entity: Any, proposed_data: Dict[str, Any]):
        """Applies validated changes to the target entity."""
        from app.imports.service import parse_iso_datetime

        base_date = getattr(entity, "work_date", None)
        if "clock_out" in proposed_data:
            entity.clock_out = parse_iso_datetime(proposed_data["clock_out"], base_date=base_date)
        if "clock_in" in proposed_data:
            entity.clock_in = parse_iso_datetime(proposed_data["clock_in"], base_date=base_date)
        if "regular_hours" in proposed_data:
            entity.regular_hours = float(proposed_data["regular_hours"])
        if "overtime_hours" in proposed_data:
            entity.overtime_hours = float(proposed_data["overtime_hours"])
        if "receipt_reference" in proposed_data:
            entity.receipt_reference = proposed_data["receipt_reference"]
        if "amount" in proposed_data:
            entity.amount = float(proposed_data["amount"])

    @staticmethod
    def _extract_period(entity: Any) -> Optional[str]:
        if hasattr(entity, "work_date") and entity.work_date:
            return entity.work_date.strftime("%Y-%m")
        if hasattr(entity, "claim_date") and entity.claim_date:
            return entity.claim_date.strftime("%Y-%m")
        return None
