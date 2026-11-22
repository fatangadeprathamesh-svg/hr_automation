import json
import logging
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional
from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.config import settings
from app.models.hr import Employee, Attendance, Leave, AuditEvent
from app.models.duties import (
    DutyTask,
    PayrollConfig,
    EmployeeSalary,
    PayrollRun,
    ComplianceDeadline,
    POSHRecord,
    POSHCommitteeMember,
    POSHAwarenessSession,
    POSHAcknowledgment,
    GrievanceCase,
    DisciplinaryNotice,
    JobOpening,
    JobApplicant,
    OnboardingChecklist,
    LeaveBalance,
    OffboardingCase,
    PolicyLibraryItem,
    PolicyAckRecord,
    RetentionRecord,
    PerformanceCycle,
    PerformanceReview,
)
from app.services.duty_registry import DUTY_REGISTRY, get_duty_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cryptographic Security Helpers for POSH Confidentiality
# ---------------------------------------------------------------------------

def _get_fernet() -> Fernet:
    key = settings.POSH_ENCRYPTION_KEY.encode("utf-8")
    return Fernet(key)


def encrypt_posh_text(plain_text: str) -> str:
    """Encrypts confidential POSH complaint text at rest."""
    if not plain_text:
        return ""
    f = _get_fernet()
    return f.encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt_posh_text(encrypted_text: str) -> str:
    """Decrypts confidential POSH complaint text. Accessible strictly to IC Members."""
    if not encrypted_text:
        return ""
    f = _get_fernet()
    return f.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")


# ---------------------------------------------------------------------------
# Hash-Chained Audit Ledger Recording
# ---------------------------------------------------------------------------

def record_duty_audit_event(
    db: Session,
    actor_id: str,
    actor_role: str,
    action_type: str,
    duty_key: str,
    task_id: str,
    payload_diff: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
) -> AuditEvent:
    """
    Appends an immutable audit event to the hash-chained audit ledger.
    Strict Non-negotiable Privacy Rule for POSH:
    The ledger and n8n payloads carry ONLY case ID, duty key, and action type, NEVER complaint text.
    """
    sanitized_diff = (payload_diff or {}).copy()
    if duty_key == "posh":
        # Ensure zero complaint content or narrative text is stored in audit ledger
        sanitized_diff.pop("complaint_text", None)
        sanitized_diff.pop("narrative", None)
        sanitized_diff.pop("description", None)
        sanitized_diff.pop("evidence_notes", None)

    event = AuditEvent(
        organization_id=settings.ORGANIZATION_ID,
        actor_id=actor_id,
        actor_role=actor_role,
        action_type=action_type,
        target_entity="duty_tasks",
        target_id=task_id,
        payload_diff={
            "duty_key": duty_key,
            "task_id": task_id,
            "run_id": run_id,
            "actor_type": "bot" if (actor_id.startswith("bot:") or actor_role == "system") else "human",
            **sanitized_diff,
        },
    )
    db.add(event)
    db.flush()
    return event


# ---------------------------------------------------------------------------
# Generic Task Engine
# ---------------------------------------------------------------------------

class DutyEngineService:
    @staticmethod
    def create_task(
        db: Session,
        duty_key: str,
        title: str,
        category: Optional[str] = None,
        employee_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        prepared_by: str = "bot",
        due_date: Optional[date] = None,
        status_val: str = "awaiting_approval",
    ) -> DutyTask:
        """Creates a new duty task and logs creation to the audit ledger."""
        config = get_duty_config(duty_key)
        task = DutyTask(
            duty_key=duty_key,
            title=title,
            category=category or config["category"],
            employee_id=employee_id,
            payload=payload or {},
            status=status_val,
            prepared_by=prepared_by,
            due_date=due_date or (date.today() + timedelta(days=7)),
            version=1,
        )
        db.add(task)
        db.flush()

        record_duty_audit_event(
            db=db,
            actor_id=prepared_by,
            actor_role="system" if prepared_by.startswith("bot") else "employee",
            action_type=f"DUTY_{duty_key.upper()}_TASK_PREPARED",
            duty_key=duty_key,
            task_id=task.id,
            payload_diff={"title": title, "status": status_val},
        )
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def decide_task(
        db: Session,
        task_id: str,
        decision: str,  # approved, rejected, returned
        actor_id: str,
        actor_role: str,
        note: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> DutyTask:
        """
        Enforces human approval gates, role permissions, maker-checker, and optimistic locking.
        """
        task = db.query(DutyTask).filter(DutyTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        config = get_duty_config(task.duty_key)

        # 1. Optimistic Locking Check
        if expected_version is not None and task.version != expected_version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflict: Task was modified by another transaction. Expected version {expected_version}, current is {task.version}.",
            )

        # 2. Bot Finalization Check
        # The bot is NEVER allowed to approve human gates, EXCEPT Duty 7 under strict policy boundaries.
        is_bot = actor_id.startswith("bot:") or actor_role in ("system", "service")
        if is_bot:
            if not config.get("bot_may_finalize", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: The bot is not permitted to finalize decisions for duty '{task.duty_key}'. A human approver is required.",
                )

        # 3. Maker-Checker Rule
        # The person who prepared or submitted an item CANNOT approve it.
        if not is_bot and task.prepared_by and task.prepared_by == actor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Maker-checker violation: The person who prepared or submitted an item cannot approve it.",
            )

        # 4. Approver Role Validation
        if not is_bot:
            if task.duty_key == "posh":
                if actor_role != "ic_member":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden: Only designated Internal Committee (IC) Members can review or decide POSH cases.",
                    )
            else:
                allowed_roles = config.get("approver_roles", ["hr_admin"])
                if actor_role not in allowed_roles and actor_role != "hr_admin":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Forbidden: Role '{actor_role}' is not authorized to decide tasks for '{task.duty_key}'. Required: {allowed_roles}",
                    )

        # 5. Apply Decision
        valid_decisions = ("approved", "rejected", "returned")
        if decision not in valid_decisions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid decision '{decision}'. Must be one of {valid_decisions}.",
            )

        task.status = decision
        task.approver_id = actor_id
        task.approver_role = actor_role
        task.decision_note = note or f"Marked {decision} by {actor_id}"
        task.decided_at = datetime.now(timezone.utc)
        task.version += 1

        # 6. Append Immutable Audit Event
        record_duty_audit_event(
            db=db,
            actor_id=actor_id,
            actor_role=actor_role,
            action_type=f"DUTY_{task.duty_key.upper()}_DECIDED_{decision.upper()}",
            duty_key=task.duty_key,
            task_id=task.id,
            payload_diff={
                "decision": decision,
                "note": note,
                "version": task.version,
                "actor_type": "bot" if is_bot else "human",
            },
        )
        db.commit()
        db.refresh(task)
        return task


# ---------------------------------------------------------------------------
# Duty 7: Attendance & Leave Engine (Auto-Approval Implementation)
# ---------------------------------------------------------------------------

class AttendanceLeaveEngine:
    @staticmethod
    def process_leave_request(
        db: Session,
        employee_id: str,
        leave_type: str,
        start_date: date,
        end_date: date,
        days_requested: float,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Evaluates leave request against the 4 policy auto-approval rules:
        1. Balance is sufficient (remaining >= requested)
        2. No date overlap with existing approved leaves
        3. Within policy limit (casual leave <= 2 days)
        4. Team minimum coverage >= 70%
        """
        emp = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found.")

        balance = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type == leave_type,
        ).first()

        if not balance:
            # Default fallback initial balance if not yet seeded
            balance = LeaveBalance(
                employee_id=employee_id,
                leave_type=leave_type,
                accrued=Decimal("12.0"),
                taken=Decimal("0.0"),
                remaining=Decimal("12.0"),
            )
            db.add(balance)
            db.flush()

        rules_evaluated = {
            "sufficient_balance": False,
            "no_date_overlap": False,
            "within_policy_limit": False,
            "team_coverage_maintained": False,
        }
        exception_reasons = []

        # Rule 1: Balance check
        remaining = float(balance.remaining)
        if remaining >= days_requested:
            rules_evaluated["sufficient_balance"] = True
        else:
            exception_reasons.append(f"Insufficient balance: requested {days_requested} days, remaining {remaining} days.")

        # Rule 2: Overlap check
        overlap = db.query(Leave).filter(
            Leave.employee_id == employee_id,
            Leave.approval_state == "approved",
            Leave.start_date <= end_date,
            Leave.end_date >= start_date,
        ).first()
        if not overlap:
            rules_evaluated["no_date_overlap"] = True
        else:
            exception_reasons.append(f"Overlapping leave exists from {overlap.start_date} to {overlap.end_date}.")

        # Rule 3: Policy limit (e.g. casual leave max 2 consecutive days for auto-approval)
        if leave_type == "casual" and days_requested > 2.0:
            exception_reasons.append(f"Casual leave duration ({days_requested} days) exceeds auto-approval limit (2.0 days).")
        else:
            rules_evaluated["within_policy_limit"] = True

        # Rule 4: Team Minimum Coverage (>= 70% present)
        team_size = db.query(Employee).filter(
            Employee.manager_id == emp.manager_id,
            Employee.is_active == True,
        ).count() if emp.manager_id else 10

        overlapping_team_leaves = db.query(Leave).join(
            Employee, Leave.employee_id == Employee.employee_id
        ).filter(
            Employee.manager_id == emp.manager_id,
            Leave.approval_state == "approved",
            Leave.start_date <= end_date,
            Leave.end_date >= start_date,
        ).count() if emp.manager_id else 0

        if overlapping_team_leaves == 0:
            coverage_pct = 100.0
        else:
            effective_size = max(team_size, 5)
            team_available = max(0, effective_size - (overlapping_team_leaves + 1))
            coverage_pct = round((team_available / effective_size) * 100.0, 1)

        if coverage_pct >= 70.0:
            rules_evaluated["team_coverage_maintained"] = True
        else:
            exception_reasons.append(f"Team minimum coverage warning: projected coverage is {coverage_pct}% (minimum required: 70%).")

        can_auto_approve = all(rules_evaluated.values())

        payload = {
            "leave_type": leave_type,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days_requested": days_requested,
            "reason": reason,
            "rules_evaluated": rules_evaluated,
            "coverage_pct": coverage_pct,
            "auto_approved": can_auto_approve,
            "exception_reasons": exception_reasons,
        }

        if can_auto_approve:
            # Bot auto-approves and updates balance
            task = DutyTask(
                duty_key="attendance_leave",
                title=f"Leave Request ({leave_type.capitalize()}): {emp.full_name} ({days_requested}d)",
                category="Time & Attendance",
                employee_id=employee_id,
                payload=payload,
                status="approved",
                prepared_by="bot:auto_approval",
                approver_id="bot:auto_approval",
                approver_role="system",
                decision_note="AUTO-APPROVED: Satisfies all 4 policy rules (balance, no overlap, duration limit, team coverage).",
                decided_at=datetime.now(timezone.utc),
                due_date=start_date,
                version=2,
            )
            db.add(task)
            db.flush()

            # Deduct balance
            balance.taken = Decimal(str(float(balance.taken) + days_requested))
            balance.remaining = Decimal(str(float(balance.remaining) - days_requested))

            # Record leave record
            new_leave = Leave(
                employee_id=employee_id,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                days_taken=Decimal(str(days_requested)),
                approval_state="approved",
                source_system="hr_duties_bot",
                source_record_id=task.id,
                import_id="IMP_DUTY_LEAVE_01",
                organization_id=settings.ORGANIZATION_ID,
            )
            db.add(new_leave)

            record_duty_audit_event(
                db=db,
                actor_id="bot:auto_approval",
                actor_role="system",
                action_type="DUTY_LEAVE_AUTO_APPROVED",
                duty_key="attendance_leave",
                task_id=task.id,
                payload_diff=payload,
            )
            db.commit()
            return {"task": task, "auto_approved": True, "message": "Leave request auto-approved by policy engine."}
        else:
            # Routes to human manager queue as an exception
            task = DutyTask(
                duty_key="attendance_leave",
                title=f"Leave Exception ({leave_type.capitalize()}): {emp.full_name} ({days_requested}d)",
                category="Time & Attendance",
                employee_id=employee_id,
                payload=payload,
                status="awaiting_approval",
                prepared_by="bot",
                decision_note=None,
                due_date=start_date,
                version=1,
            )
            db.add(task)
            db.flush()

            record_duty_audit_event(
                db=db,
                actor_id="bot",
                actor_role="system",
                action_type="DUTY_LEAVE_ROUTED_TO_MANAGER",
                duty_key="attendance_leave",
                task_id=task.id,
                payload_diff={"exceptions": exception_reasons},
            )
            db.commit()
            return {"task": task, "auto_approved": False, "message": f"Leave requires manager approval: {'; '.join(exception_reasons)}"}


# ---------------------------------------------------------------------------
# Duty 1: Payroll & Statutory Calculations
# ---------------------------------------------------------------------------

class PayrollEngine:
    @staticmethod
    def calculate_monthly_payroll(db: Session, period: str = "2026-10") -> Dict[str, Any]:
        """Calculates monthly payroll from employee salaries & attendance records."""
        config = db.query(PayrollConfig).first()
        if not config:
            config = PayrollConfig()
            db.add(config)
            db.flush()

        salaries = db.query(EmployeeSalary).all()
        if not salaries:
            # Create sample salary for active employees
            employees = db.query(Employee).filter(Employee.is_active == True).all()
            for emp in employees:
                base_ctc = 600000.00 if emp.employee_id.startswith("EMP") else 1200000.00
                monthly_g = base_ctc / 12.0
                sal = EmployeeSalary(
                    employee_id=emp.employee_id,
                    ctc_annual=Decimal(str(base_ctc)),
                    monthly_gross=Decimal(str(monthly_g)),
                    basic_pay=Decimal(str(round(monthly_g * 0.40, 2))),
                    hra=Decimal(str(round(monthly_g * 0.20, 2))),
                    special_allowance=Decimal(str(round(monthly_g * 0.40, 2))),
                    state="Karnataka",
                )
                db.add(sal)
            db.flush()
            salaries = db.query(EmployeeSalary).all()

        total_gross = Decimal("0.0")
        total_pf = Decimal("0.0")
        total_esi = Decimal("0.0")
        total_pt = Decimal("0.0")
        total_tds = Decimal("0.0")
        total_net = Decimal("0.0")
        records = []

        total_days_in_month = 31  # October
        for sal in salaries:
            emp = db.query(Employee).filter(Employee.employee_id == sal.employee_id).first()
            if not emp:
                continue

            # Count unpaid leaves in month
            unpaid_leaves = db.query(func.coalesce(func.sum(Leave.days_taken), 0)).filter(
                Leave.employee_id == sal.employee_id,
                Leave.leave_type == "unpaid",
                Leave.approval_state == "approved",
            ).scalar() or 0.0

            loss_of_pay_days = float(unpaid_leaves)
            paid_days = max(0.0, total_days_in_month - loss_of_pay_days)
            proration_factor = Decimal(str(round(paid_days / total_days_in_month, 4)))

            earned_gross = round(sal.monthly_gross * proration_factor, 2)
            earned_basic = round(sal.basic_pay * proration_factor, 2)
            earned_hra = round(sal.hra * proration_factor, 2)
            earned_special = round(sal.special_allowance * proration_factor, 2)

            # PF: 12% on min(basic, 15000)
            pf_wage = min(earned_basic, config.pf_wage_ceiling)
            pf_deduction = round(pf_wage * (config.pf_rate_pct / Decimal("100.0")), 2)

            # ESI: 0.75% if gross <= 21000
            if earned_gross <= config.esi_wage_ceiling:
                esi_deduction = round(earned_gross * (config.esi_rate_pct / Decimal("100.0")), 2)
            else:
                esi_deduction = Decimal("0.0")

            # Professional Tax: Karnataka slab
            if sal.state == "Karnataka":
                pt_deduction = Decimal("200.00") if earned_gross >= Decimal("15000.00") else Decimal("0.0")
            elif sal.state == "Maharashtra":
                pt_deduction = Decimal("200.00") if earned_gross >= Decimal("10000.00") else Decimal("0.0")
            else:
                pt_deduction = Decimal("200.00")

            # Estimated TDS (approx ~5% above 50k standard exemption)
            annualized_est = earned_gross * Decimal("12.0")
            if annualized_est > Decimal("500000.00"):
                tds_deduction = round((annualized_est - Decimal("500000.00")) * Decimal("0.05") / Decimal("12.0"), 2)
            else:
                tds_deduction = Decimal("0.0")

            total_deductions = pf_deduction + esi_deduction + pt_deduction + tds_deduction
            net_pay = earned_gross - total_deductions

            total_gross += earned_gross
            total_pf += pf_deduction
            total_esi += esi_deduction
            total_pt += pt_deduction
            total_tds += tds_deduction
            total_net += net_pay

            records.append({
                "employee_id": sal.employee_id,
                "name": emp.full_name,
                "department": getattr(emp, "timezone", "Engineering"),
                "paid_days": paid_days,
                "loss_of_pay_days": loss_of_pay_days,
                "gross": float(earned_gross),
                "basic": float(earned_basic),
                "hra": float(earned_hra),
                "special_allowance": float(earned_special),
                "pf": float(pf_deduction),
                "esi": float(esi_deduction),
                "pt": float(pt_deduction),
                "tds": float(tds_deduction),
                "total_deductions": float(total_deductions),
                "net_pay": float(net_pay),
            })

        # Check existing run or create new
        existing_run = db.query(PayrollRun).filter(PayrollRun.period == period).first()
        if existing_run:
            payroll_run = existing_run
            payroll_run.total_employees = len(records)
            payroll_run.total_gross = total_gross
            payroll_run.total_pf = total_pf
            payroll_run.total_esi = total_esi
            payroll_run.total_pt = total_pt
            payroll_run.total_tds = total_tds
            payroll_run.total_net = total_net
            payroll_run.records_json = records
            payroll_run.status = "calculated"
        else:
            payroll_run = PayrollRun(
                period=period,
                total_employees=len(records),
                total_gross=total_gross,
                total_pf=total_pf,
                total_esi=total_esi,
                total_pt=total_pt,
                total_tds=total_tds,
                total_net=total_net,
                status="calculated",
                records_json=records,
            )
            db.add(payroll_run)

        db.flush()

        # Create or update DutyTask awaiting approval
        task_title = f"Payroll Run & Statutory Deductions ({period})"
        task = db.query(DutyTask).filter(
            DutyTask.duty_key == "payroll_statutory",
            DutyTask.title == task_title,
        ).first()

        summary_payload = {
            "period": period,
            "total_employees": len(records),
            "total_gross": float(total_gross),
            "total_pf": float(total_pf),
            "total_esi": float(total_esi),
            "total_pt": float(total_pt),
            "total_tds": float(total_tds),
            "total_net": float(total_net),
            "payroll_run_id": payroll_run.run_id,
            "disclaimer": config.disclaimer,
        }

        if not task:
            task = DutyTask(
                duty_key="payroll_statutory",
                title=task_title,
                category="Compensation & Payroll",
                payload=summary_payload,
                status="awaiting_approval",
                prepared_by="bot:payroll",
                due_date=date.today() + timedelta(days=5),
                version=1,
            )
            db.add(task)
        else:
            task.payload = summary_payload
            task.status = "awaiting_approval"

        db.flush()
        record_duty_audit_event(
            db=db,
            actor_id="bot:payroll",
            actor_role="system",
            action_type="DUTY_PAYROLL_CALCULATED",
            duty_key="payroll_statutory",
            task_id=task.id,
            payload_diff=summary_payload,
            run_id=payroll_run.run_id,
        )
        db.commit()
        return {
            "payroll_run_id": payroll_run.run_id,
            "task_id": task.id,
            "summary": summary_payload,
            "records_count": len(records),
        }


# ---------------------------------------------------------------------------
# AI Drafting Hook (Stub with TODO)
# ---------------------------------------------------------------------------

def draft_duty_content_ai(duty_key: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clearly marked hook for AI generative drafting.
    TODO: Connect to Gemini / LLM API when production keys are enabled.
    Currently returns high-quality deterministic template drafts in DEV mode.
    """
    templates = {
        "discipline_grievance": {
            "show_cause": "WHEREAS it has been reported that on {date}, {employee_name} engaged in conduct violating policy ({reason}). YOU ARE HEREBY REQUIRED to submit an explanation within 48 hours.",
            "warning": "FORMAL WARNING: Following review of incident ({reason}), you are advised that recurrence will lead to severe disciplinary escalation under company standards.",
            "outcome": "INQUIRY OUTCOME: The Internal Grievance Committee has concluded its review regarding ({reason}). Action decided: {action}.",
        },
        "recruitment": {
            "offer_letter": "Dear {candidate_name},\n\nWe are pleased to offer you the position of {position} at our Bangalore office with an annual CTC of INR {salary}. Your anticipated joining date is {join_date}.",
        },
        "offboarding_fnf": {
            "relieving_letter": "TO WHOM IT MAY CONCERN:\n\nThis is to certify that {employee_name} was employed with us from {hire_date} to {exit_date}. They are relieved from services in good standing.",
        },
    }

    category_tpls = templates.get(duty_key, {})
    draft_type = context.get("type", list(category_tpls.keys())[0] if category_tpls else "generic")
    template_str = category_tpls.get(draft_type, "Draft generated for {duty_key}: context={context}")

    # Deterministic string interpolation
    formatted = template_str.format(
        duty_key=duty_key,
        date=context.get("date", str(date.today())),
        employee_name=context.get("employee_name", "Employee"),
        candidate_name=context.get("candidate_name", "Candidate"),
        position=context.get("position", "Software Engineer"),
        salary=context.get("salary", "12,00,000"),
        join_date=context.get("join_date", str(date.today() + timedelta(days=14))),
        hire_date=context.get("hire_date", "2024-01-01"),
        exit_date=context.get("exit_date", str(date.today())),
        reason=context.get("reason", "unauthorized absence"),
        action=context.get("action", "Counselling and record notation"),
        context=str(context),
    )

    return {
        "status": "success",
        "mode": "DEV_MODE_DETERMINISTIC_HOOK",
        "todo_note": "TODO: Wire to Gemini API once enterprise credentials are provided.",
        "draft_text": formatted,
    }
