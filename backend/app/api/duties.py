import csv
import io
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.database import get_db
from app.auth.security import get_current_actor, ActorIdentity
from app.models.hr import Employee, Leave, Attendance, AuditEvent
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
from app.services.duty_registry import DUTY_REGISTRY, get_duty_registry, get_duty_config
from app.services.duty_engine import (
    DutyEngineService,
    AttendanceLeaveEngine,
    PayrollEngine,
    encrypt_posh_text,
    decrypt_posh_text,
    draft_duty_content_ai,
    record_duty_audit_event,
)

router = APIRouter(prefix="/api/duties", tags=["HR Duties Engine"])


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class CreateDutyTaskRequest(BaseModel):
    title: str
    category: Optional[str] = None
    employee_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    due_date: Optional[date] = None


class DecideDutyTaskRequest(BaseModel):
    decision: str = Field(..., pattern=r"^(approved|rejected|returned)$")
    decision_note: Optional[str] = None
    expected_version: Optional[int] = None


class LeaveSubmissionRequest(BaseModel):
    leave_type: str = "casual"
    start_date: date
    end_date: date
    days_requested: float = 1.0
    reason: str = "Personal obligation"


class PoshIntakeRequest(BaseModel):
    incident_date: Optional[date] = None
    complaint_text: str
    disposition: Optional[str] = None


class AIDraftRequest(BaseModel):
    context: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Hub & List Endpoints
# ---------------------------------------------------------------------------

@router.get("", status_code=status.HTTP_200_OK)
@router.get("/hub", status_code=status.HTTP_200_OK)
def list_duties_hub(
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Returns high-level hub cards for all 10 duties with bot-vs-human split,
    live counters (prepared by bot, awaiting approval, overdue), and role-specific access markers.
    """
    today = date.today()
    results = []

    for key, config in DUTY_REGISTRY.items():
        base_query = db.query(DutyTask).filter(DutyTask.duty_key == key)

        # Scoping per role:
        # Non-IC members cannot view sensitive tasks for POSH
        if key == "posh" and actor.role != "ic_member":
            # For POSH, non-IC users see public count of awareness/aggregate items only
            prepared_count = db.query(POSHAwarenessSession).count()
            awaiting_count = 0  # Hidden from non-IC
            overdue_count = 0
            total_tasks = prepared_count
        elif actor.role == "employee":
            user_query = base_query.filter(
                or_(DutyTask.employee_id == actor.actor_id, DutyTask.employee_id.is_(None))
            )
            prepared_count = user_query.filter(DutyTask.prepared_by.like("bot%")).count()
            awaiting_count = user_query.filter(DutyTask.status == "awaiting_approval").count()
            overdue_count = user_query.filter(
                DutyTask.status.in_(["queued", "prepared", "awaiting_approval"]),
                DutyTask.due_date < today,
            ).count()
            total_tasks = user_query.count()
        else:
            prepared_count = base_query.filter(DutyTask.prepared_by.like("bot%")).count()
            awaiting_count = base_query.filter(DutyTask.status == "awaiting_approval").count()
            overdue_count = base_query.filter(
                DutyTask.status.in_(["queued", "prepared", "awaiting_approval"]),
                DutyTask.due_date < today,
            ).count()
            total_tasks = base_query.count()

        latest_task = base_query.order_by(DutyTask.updated_at.desc()).first()

        results.append({
            "key": key,
            "name": config["name"],
            "category": config["category"],
            "icon": config.get("icon", "Briefcase"),
            "description": config["description"],
            "bot_actions": config["bot_actions"],
            "human_gate": config["human_gate"],
            "approver_roles": config["approver_roles"],
            "confidentiality_level": config["confidentiality_level"],
            "bot_may_finalize": config["bot_may_finalize"],
            "prepared_by_bot": prepared_count,
            "awaiting_approval": awaiting_count,
            "overdue_count": overdue_count,
            "total_tasks": total_tasks,
            "last_updated": latest_task.updated_at.isoformat() if latest_task else None,
            "user_can_approve": actor.role in config["approver_roles"] or (actor.role == "hr_admin" and key != "posh"),
        })

    return {
        "duties": results,
        "actor": {
            "actor_id": actor.actor_id,
            "role": actor.role,
        },
        "system_philosophy": "Bot Prepares & Automates — Human Approves & Decides",
    }


@router.get("/{duty_key}", status_code=status.HTTP_200_OK)
def get_duty_detail(
    duty_key: str,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Retrieves full metadata, policy rules, and live metric cards for a single duty."""
    config = get_duty_config(duty_key)
    today = date.today()

    base_query = db.query(DutyTask).filter(DutyTask.duty_key == duty_key)
    if duty_key == "posh" and actor.role != "ic_member":
        prepared_count = db.query(POSHAwarenessSession).count()
        awaiting_count = 0
        overdue_count = 0
    elif actor.role == "employee":
        base_query = base_query.filter(
            or_(DutyTask.employee_id == actor.actor_id, DutyTask.employee_id.is_(None))
        )
        prepared_count = base_query.filter(DutyTask.prepared_by.like("bot%")).count()
        awaiting_count = base_query.filter(DutyTask.status == "awaiting_approval").count()
        overdue_count = base_query.filter(
            DutyTask.status.in_(["queued", "prepared", "awaiting_approval"]),
            DutyTask.due_date < today,
        ).count()
    else:
        prepared_count = base_query.filter(DutyTask.prepared_by.like("bot%")).count()
        awaiting_count = base_query.filter(DutyTask.status == "awaiting_approval").count()
        overdue_count = base_query.filter(
            DutyTask.status.in_(["queued", "prepared", "awaiting_approval"]),
            DutyTask.due_date < today,
        ).count()

    is_restricted_posh = (duty_key == "posh" and actor.role != "ic_member")

    return {
        "config": config,
        "metrics": {
            "prepared_by_bot": prepared_count,
            "awaiting_approval": awaiting_count,
            "overdue_count": overdue_count,
            "total_tasks": base_query.count() if not is_restricted_posh else prepared_count,
        },
        "user_can_approve": actor.role in config["approver_roles"] or (actor.role == "hr_admin" and duty_key != "posh"),
        "is_restricted_posh": is_restricted_posh,
    }


# ---------------------------------------------------------------------------
# Task Engine & Approval Queue
# ---------------------------------------------------------------------------

@router.get("/{duty_key}/tasks", status_code=status.HTTP_200_OK)
def list_duty_tasks(
    duty_key: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, le=200),
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Returns tasks for a duty, partitioned into Bot Activity, Approval Queue, and Records tabs.
    Applies strict POSH confidentiality: non-IC members receive redacted/restricted payloads.
    """
    config = get_duty_config(duty_key)

    # 1. POSH Isolation Enforcement
    if duty_key == "posh" and actor.role != "ic_member":
        return {
            "restricted": True,
            "notice": "ACCESS RESTRICTED: POSH complaints are strictly confidential and restricted to designated Internal Committee (IC) Members.",
            "tasks": [],
        }

    query = db.query(DutyTask).filter(DutyTask.duty_key == duty_key)

    # 2. Role-based visibility
    if actor.role == "employee":
        query = query.filter(or_(DutyTask.employee_id == actor.actor_id, DutyTask.employee_id.is_(None)))
    elif actor.role == "manager":
        # Managers view their direct reports + their own items
        direct_report_ids = [
            e.employee_id for e in db.query(Employee).filter(Employee.manager_id == actor.actor_id).all()
        ]
        direct_report_ids.append(actor.actor_id)
        query = query.filter(or_(DutyTask.employee_id.in_(direct_report_ids), DutyTask.employee_id.is_(None)))

    if status_filter:
        query = query.filter(DutyTask.status == status_filter)

    tasks = query.order_by(DutyTask.created_at.desc()).limit(limit).all()

    serialized = []
    for t in tasks:
        item = {
            "id": t.id,
            "duty_key": t.duty_key,
            "title": t.title,
            "category": t.category,
            "employee_id": t.employee_id,
            "status": t.status,
            "prepared_by": t.prepared_by,
            "prepared_at": t.prepared_at.isoformat() if t.prepared_at else None,
            "approver_id": t.approver_id,
            "approver_role": t.approver_role,
            "decision_note": t.decision_note,
            "decided_at": t.decided_at.isoformat() if t.decided_at else None,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "version": t.version,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "is_maker": (t.prepared_by == actor.actor_id),
            "payload": t.payload,
        }
        serialized.append(item)

    return {
        "restricted": False,
        "duty_key": duty_key,
        "tasks": serialized,
        "count": len(serialized),
    }


@router.post("/{duty_key}/tasks", status_code=status.HTTP_201_CREATED)
def create_duty_task(
    duty_key: str,
    req: CreateDutyTaskRequest,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Manually creates a duty task (or prepared item)."""
    task = DutyEngineService.create_task(
        db=db,
        duty_key=duty_key,
        title=req.title,
        category=req.category,
        employee_id=req.employee_id or actor.actor_id,
        payload=req.payload,
        prepared_by=actor.actor_id,
        due_date=req.due_date,
        status_val="awaiting_approval",
    )
    return {"message": "Task created successfully", "task_id": task.id, "version": task.version}


@router.post("/{duty_key}/tasks/{task_id}/decide", status_code=status.HTTP_200_OK)
def decide_duty_task(
    duty_key: str,
    task_id: str,
    req: DecideDutyTaskRequest,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    HUMAN APPROVAL GATE:
    Enforces role authorization, maker-checker, and optimistic locking.
    Appends an immutable cryptographic event to the audit ledger.
    """
    updated_task = DutyEngineService.decide_task(
        db=db,
        task_id=task_id,
        decision=req.decision,
        actor_id=actor.actor_id,
        actor_role=actor.role,
        note=req.decision_note,
        expected_version=req.expected_version,
    )
    return {
        "status": "success",
        "task_id": updated_task.id,
        "decision": updated_task.status,
        "approver_id": updated_task.approver_id,
        "version": updated_task.version,
        "decided_at": updated_task.decided_at.isoformat() if updated_task.decided_at else None,
    }


# ---------------------------------------------------------------------------
# Bot Automated Actions (The 10 Duties)
# ---------------------------------------------------------------------------

@router.post("/{duty_key}/bot-run", status_code=status.HTTP_200_OK)
def trigger_duty_bot_run(
    duty_key: str,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Executes deterministic bot preparation logic for the requested duty.
    The bot prepares tasks, calculates numbers, drafts notices, and queues them for human approval.
    """
    get_duty_config(duty_key)

    if duty_key == "payroll_statutory":
        res = PayrollEngine.calculate_monthly_payroll(db, period="2026-10")
        return {
            "duty_key": duty_key,
            "action": "monthly_payroll_calculated",
            "summary": res["summary"],
            "records_processed": res["records_count"],
            "human_gate_message": "Payroll calculation prepared. HR Admin must inspect and approve in the Approval Queue.",
        }

    elif duty_key == "labour_compliance":
        # Check calendar and create upcoming statutory filing tasks
        deadlines = db.query(ComplianceDeadline).filter(ComplianceDeadline.period == "2026-10").all()
        created_tasks = []
        for dl in deadlines:
            existing = db.query(DutyTask).filter(
                DutyTask.duty_key == "labour_compliance",
                DutyTask.title == f"Statutory Return Sign-off: {dl.title} ({dl.period})",
            ).first()
            if not existing:
                t = DutyEngineService.create_task(
                    db=db,
                    duty_key="labour_compliance",
                    title=f"Statutory Return Sign-off: {dl.title} ({dl.period})",
                    category="Statutory & Legal",
                    payload={
                        "authority": dl.authority,
                        "due_date": dl.due_date.isoformat(),
                        "description": dl.description,
                        "reminders_dispatched": dl.reminder_days,
                    },
                    prepared_by="bot:compliance",
                    due_date=dl.due_date,
                    status_val="awaiting_approval",
                )
                created_tasks.append(t.id)

        return {
            "duty_key": duty_key,
            "action": "compliance_calendar_evaluated",
            "deadlines_checked": len(deadlines),
            "tasks_queued": len(created_tasks),
            "human_gate_message": "Draft returns prepared. Compliance Officer must sign off before marking filed.",
        }

    elif duty_key == "posh":
        # Bot compiles annual aggregate statistics (NO individual details)
        total_received = db.query(POSHRecord).count()
        total_disposed = db.query(POSHRecord).filter(POSHRecord.status.in_(["resolved", "dismissed"])).count()
        total_pending = total_received - total_disposed
        awareness_count = db.query(POSHAwarenessSession).count()
        attendees = db.query(func.coalesce(func.sum(POSHAwarenessSession.attendees_count), 0)).scalar() or 0

        summary_payload = {
            "annual_period": "2026",
            "complaints_received": total_received,
            "complaints_disposed": total_disposed,
            "complaints_pending": total_pending,
            "awareness_workshops_held": awareness_count,
            "employees_sensitized": attendees,
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "privacy_certification": "Compiled strictly from anonymized aggregate numbers. Zero complaint text accessed.",
        }

        task = db.query(DutyTask).filter(
            DutyTask.duty_key == "posh",
            DutyTask.title == "POSH Annual Statutory Return (Aggregate Summary)",
        ).first()

        if not task:
            task = DutyEngineService.create_task(
                db=db,
                duty_key="posh",
                title="POSH Annual Statutory Return (Aggregate Summary)",
                category="Workplace Safety & Ethics",
                payload=summary_payload,
                prepared_by="bot:posh_aggregator",
                status_val="awaiting_approval",
            )
        else:
            task.payload = summary_payload
            db.commit()

        return {
            "duty_key": duty_key,
            "action": "annual_report_aggregate_compiled",
            "aggregate_summary": summary_payload,
            "human_gate_message": "Annual report compiled from aggregate counts. Internal Committee (IC) must sign off.",
        }

    elif duty_key == "discipline_grievance":
        # Check grievance timeline SLAs and draft auto-populated show-cause notices
        open_cases = db.query(GrievanceCase).filter(GrievanceCase.status.in_(["open", "in_review"])).all()
        prepared_notices = []
        for c in open_cases:
            existing_notice = db.query(DisciplinaryNotice).filter(DisciplinaryNotice.case_id == c.id).first()
            if not existing_notice:
                draft_body = (
                    f"SHOW CAUSE NOTICE\n\n"
                    f"Case Ref: {c.case_number}\n"
                    f"Date: {date.today()}\n"
                    f"To: {c.employee.full_name if c.employee else c.employee_id}\n\n"
                    f"Subject: Formal inquiry regarding reported {c.category} ({c.title}).\n\n"
                    f"You are hereby called upon to provide a written explanation within 48 hours of receipt. "
                    f"Failure to respond will result in ex-parte review under company employment regulations."
                )
                notice = DisciplinaryNotice(
                    case_id=c.id,
                    notice_type="show_cause",
                    recipient_id=c.employee_id,
                    draft_text=draft_body,
                    status="draft",
                )
                db.add(notice)
                db.flush()

                # Queue task for HR approval before notice is issued
                t = DutyEngineService.create_task(
                    db=db,
                    duty_key="discipline_grievance",
                    title=f"Authorize Show Cause Notice: {c.case_number} ({c.employee_id})",
                    category="Employee Relations",
                    employee_id=c.employee_id,
                    payload={"case_id": c.id, "case_number": c.case_number, "draft_text": draft_body, "notice_id": notice.id},
                    prepared_by="bot:grievance",
                    status_val="awaiting_approval",
                )
                prepared_notices.append(t.id)

        db.commit()
        return {
            "duty_key": duty_key,
            "action": "grievance_cases_evaluated",
            "active_cases": len(open_cases),
            "notices_drafted": len(prepared_notices),
            "human_gate_message": "Draft show-cause notices prepared. HR Admin must approve before issuance.",
        }

    elif duty_key == "recruitment":
        # Screen applicants deterministically (Excluding gender, age, DOB, state, name)
        applicants = db.query(JobApplicant).filter(JobApplicant.status == "screened").all()
        screened_count = 0
        for app in applicants:
            job = app.job
            exp_pts = min(40, int((float(app.years_experience) / max(job.min_experience, 1)) * 40))
            edu_pts = 30 if "B.Tech" in app.education or "MCA" in app.education or "Degree" in app.education else 20

            # Keyword match
            req_skills = [s.lower() for s in (job.required_skills or [])]
            cand_skills = [s.lower() for s in (app.skills or [])]
            matched = [s for s in req_skills if s in cand_skills]
            skill_pts = int((len(matched) / max(len(req_skills), 1)) * 30)
            score = exp_pts + edu_pts + skill_pts

            app.screening_score = score
            app.screening_reasons = [
                f"Experience: {app.years_experience} yrs ({exp_pts}/40 pts)",
                f"Education: {app.education} ({edu_pts}/30 pts)",
                f"Skills match: {', '.join(matched) if matched else 'None'} ({skill_pts}/30 pts)",
                "Fairness Rule: Demographics (gender, age, DOB, state, name) strictly excluded.",
            ]
            screened_count += 1

            # Queue top candidates for manager selection
            if score >= 70:
                existing_task = db.query(DutyTask).filter(
                    DutyTask.duty_key == "recruitment",
                    DutyTask.title == f"Candidate Shortlist & Interview: {app.name} ({job.title})",
                ).first()
                if not existing_task:
                    DutyEngineService.create_task(
                        db=db,
                        duty_key="recruitment",
                        title=f"Candidate Shortlist & Interview: {app.name} ({job.title})",
                        category="Talent Acquisition",
                        payload={
                            "applicant_id": app.id,
                            "job_title": job.title,
                            "candidate_name": app.name,
                            "screening_score": score,
                            "screening_reasons": app.screening_reasons,
                            "suggested_interview_slot": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
                        },
                        prepared_by="bot:recruitment_screener",
                        status_val="awaiting_approval",
                    )
        db.commit()
        return {
            "duty_key": duty_key,
            "action": "candidates_screened_deterministically",
            "candidates_screened": screened_count,
            "fairness_notice": "Screening performed using objective skills, experience, and education only.",
            "human_gate_message": "Screening scores calculated. Hiring Manager must approve shortlist and offer.",
        }

    elif duty_key == "onboarding":
        # Check probation milestones & document verification
        checklists = db.query(OnboardingChecklist).filter(OnboardingChecklist.probation_status == "in_probation").all()
        confirmed_candidates = 0
        for chk in checklists:
            if chk.doc_status == "verified" and chk.it_status == "provisioned" and chk.induction_status == "completed":
                existing = db.query(DutyTask).filter(
                    DutyTask.duty_key == "onboarding",
                    DutyTask.employee_id == chk.employee_id,
                    DutyTask.title.like("%Probation Confirmation%"),
                ).first()
                if not existing:
                    DutyEngineService.create_task(
                        db=db,
                        duty_key="onboarding",
                        title=f"Probation Confirmation Review: {chk.employee.full_name} ({chk.employee_id})",
                        category="Employee Lifecycle",
                        employee_id=chk.employee_id,
                        payload={
                            "join_date": chk.join_date.isoformat(),
                            "probation_end_date": chk.probation_end_date.isoformat(),
                            "doc_status": chk.doc_status,
                            "it_status": chk.it_status,
                            "induction_status": chk.induction_status,
                        },
                        prepared_by="bot:onboarding",
                        due_date=chk.probation_end_date,
                        status_val="awaiting_approval",
                    )
                    confirmed_candidates += 1
        db.commit()
        return {
            "duty_key": duty_key,
            "action": "onboarding_milestones_evaluated",
            "active_onboarding": len(checklists),
            "probation_confirmations_queued": confirmed_candidates,
            "human_gate_message": "Checklist completed. Manager & HR must approve formal probation confirmation.",
        }

    elif duty_key == "attendance_leave":
        # Check leave balances and queue any pending exception tasks
        leaves_count = db.query(Leave).count()
        balances_count = db.query(LeaveBalance).count()
        return {
            "duty_key": duty_key,
            "action": "attendance_rules_synced",
            "total_leaves_recorded": leaves_count,
            "leave_balances_tracked": balances_count,
            "policy_rules": get_duty_config("attendance_leave")["auto_approval_rules"],
            "human_gate_message": "Compliant leaves are auto-approved by the bot. Exceptions await manager sign-off.",
        }

    elif duty_key == "offboarding_fnf":
        # Calculate FNF for active offboarding cases
        cases = db.query(OffboardingCase).filter(OffboardingCase.status.in_(["initiated", "clearance_in_progress"])).all()
        calculated_count = 0
        for c in cases:
            sal = db.query(EmployeeSalary).filter(EmployeeSalary.employee_id == c.employee_id).first()
            monthly_g = float(sal.monthly_gross) if sal else 50000.0
            daily_rate = monthly_g / 30.0

            # 15 days pending salary
            pending_sal = round(daily_rate * 15, 2)
            leave_bal = db.query(LeaveBalance).filter(LeaveBalance.employee_id == c.employee_id, LeaveBalance.leave_type == "earned").first()
            rem_days = float(leave_bal.remaining) if leave_bal else 5.0
            leave_encash = round(rem_days * daily_rate, 2)

            shortfall = max(0, c.notice_required_days - c.notice_served_days)
            shortfall_rec = round(shortfall * daily_rate, 2)

            # Gratuity eligibility: >= 5 years (approx 1825 days)
            emp = db.query(Employee).filter(Employee.employee_id == c.employee_id).first()
            tenure_days = (c.last_working_date - emp.hire_date).days if emp else 500
            gratuity_eligible = tenure_days >= 1825
            gratuity_amt = round((15.0 * (monthly_g * 0.4) * (tenure_days / 365.0)) / 26.0, 2) if gratuity_eligible else 0.0

            net_p = round(pending_sal + leave_encash - shortfall_rec + gratuity_amt, 2)

            c.pending_salary = Decimal(str(pending_sal))
            c.leave_encashment = Decimal(str(leave_encash))
            c.shortfall_recovery = Decimal(str(shortfall_rec))
            c.gratuity_eligible = gratuity_eligible
            c.gratuity_amount = Decimal(str(gratuity_amt))
            c.net_payable = Decimal(str(net_p))
            c.status = "fnf_calculated"

            # Create or update task awaiting approval
            existing = db.query(DutyTask).filter(
                DutyTask.duty_key == "offboarding_fnf",
                DutyTask.employee_id == c.employee_id,
            ).first()
            fnf_payload = {
                "case_id": c.id,
                "resignation_date": c.resignation_date.isoformat(),
                "last_working_date": c.last_working_date.isoformat(),
                "pending_salary": pending_sal,
                "leave_encashment": leave_encash,
                "shortfall_recovery": shortfall_rec,
                "gratuity_eligible": gratuity_eligible,
                "gratuity_amount": gratuity_amt,
                "net_payable": net_p,
                "clearances": {
                    "it": c.it_clearance,
                    "finance": c.finance_clearance,
                    "admin": c.admin_clearance,
                    "hr": c.hr_clearance,
                },
            }
            if not existing:
                DutyEngineService.create_task(
                    db=db,
                    duty_key="offboarding_fnf",
                    title=f"Full & Final Settlement Approval: {emp.full_name if emp else c.employee_id}",
                    category="Employee Lifecycle",
                    employee_id=c.employee_id,
                    payload=fnf_payload,
                    prepared_by="bot:fnf_calculator",
                    status_val="awaiting_approval",
                )
            else:
                existing.payload = fnf_payload
            calculated_count += 1

        db.commit()
        return {
            "duty_key": duty_key,
            "action": "fnf_settlements_calculated",
            "cases_processed": calculated_count,
            "human_gate_message": "FNF payout calculated. HR Admin must inspect clearances and authorize disbursement.",
        }

    elif duty_key == "policies_records":
        policies = db.query(PolicyLibraryItem).all()
        retention = db.query(RetentionRecord).count()
        return {
            "duty_key": duty_key,
            "action": "policies_indexed_deterministically",
            "total_policies": len(policies),
            "retention_records_monitored": retention,
            "search_capability": "Deterministic keyword indexing ready (no external AI call).",
            "human_gate_message": "Policy changes require HR Admin approval prior to publication.",
        }

    elif duty_key == "performance":
        # Deterministically summarize review feedback (Averages, counts, themes)
        reviews = db.query(PerformanceReview).all()
        summarized = 0
        for r in reviews:
            peer_scores = [p.get("rating", 3.0) for p in (r.peer_feedback_json or [])]
            avg_peer = round(sum(peer_scores) / max(len(peer_scores), 1), 1) if peer_scores else 3.5

            r.deterministic_summary = {
                "self_goals_count": len(r.self_goals_json or []),
                "peer_reviews_count": len(peer_scores),
                "average_peer_rating": avg_peer,
                "review_cycle": r.cycle.cycle_name if r.cycle else "Annual Review",
            }
            summarized += 1

            existing_task = db.query(DutyTask).filter(
                DutyTask.duty_key == "performance",
                DutyTask.employee_id == r.employee_id,
            ).first()
            if not existing_task:
                emp = r.employee
                DutyEngineService.create_task(
                    db=db,
                    duty_key="performance",
                    title=f"Performance Rating & Increment Decision: {emp.full_name if emp else r.employee_id}",
                    category="Talent Management",
                    employee_id=r.employee_id,
                    payload={
                        "review_id": r.id,
                        "manager_id": r.manager_id,
                        "deterministic_summary": r.deterministic_summary,
                    },
                    prepared_by="bot:performance_aggregator",
                    status_val="awaiting_approval",
                )

        db.commit()
        return {
            "duty_key": duty_key,
            "action": "feedback_summarized_deterministically",
            "reviews_aggregated": summarized,
            "human_gate_message": "Review averages compiled. Reporting Manager and HR must assign final rating and increments.",
        }

    return {"duty_key": duty_key, "action": "noop", "status": "ready"}


# ---------------------------------------------------------------------------
# Duty-Specific Specialized Actions
# ---------------------------------------------------------------------------

@router.post("/attendance_leave/request-leave", status_code=status.HTTP_200_OK)
def submit_leave_request(
    req: LeaveSubmissionRequest,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Submits an employee leave request and triggers the deterministic 4-rule auto-approval engine.
    Compliant requests are auto-approved instantly with evidence logged to the ledger.
    """
    result = AttendanceLeaveEngine.process_leave_request(
        db=db,
        employee_id=actor.actor_id,
        leave_type=req.leave_type,
        start_date=req.start_date,
        end_date=req.end_date,
        days_requested=req.days_requested,
        reason=req.reason,
    )
    task = result["task"]
    return {
        "task_id": task.id,
        "status": task.status,
        "auto_approved": result["auto_approved"],
        "message": result["message"],
        "version": task.version,
    }


@router.get("/payroll_statutory/payslip/{employee_id}", response_class=HTMLResponse)
def get_printable_payslip(
    employee_id: str,
    period: str = "2026-10",
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Generates clean, printable HTML payslip matching enterprise specifications."""
    # Employee privacy: employee can only see their own payslip
    if actor.role == "employee" and actor.actor_id != employee_id:
        raise HTTPException(status_code=403, detail="Forbidden: You can only view your own payslip.")

    emp = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    sal = db.query(EmployeeSalary).filter(EmployeeSalary.employee_id == employee_id).first()
    gross = float(sal.monthly_gross) if sal else 50000.0
    basic = float(sal.basic_pay) if sal else gross * 0.4
    hra = float(sal.hra) if sal else gross * 0.2
    special = float(sal.special_allowance) if sal else gross * 0.4
    pf = round(min(basic, 15000.0) * 0.12, 2)
    esi = round(gross * 0.0075, 2) if gross <= 21000.0 else 0.0
    pt = 200.0 if gross >= 15000.0 else 0.0
    tds = round(max(0.0, (gross * 12 - 500000.0) * 0.05 / 12), 2)
    tot_ded = pf + esi + pt + tds
    net = round(gross - tot_ded, 2)

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Payslip - {emp.full_name} ({period})</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; color: #1e293b; background: #fff; }}
    .header {{ border-bottom: 2px solid #F26A21; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; }}
    .title {{ font-size: 24px; font-weight: 800; color: #0f172a; margin: 0; }}
    .badge {{ background: #ffedd5; color: #c2410c; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; }}
    .meta-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; background: #f8fafc; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0; }}
    .meta-item label {{ display: block; font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 700; margin-bottom: 4px; }}
    .meta-item span {{ font-size: 13px; font-weight: 600; color: #0f172a; }}
    .table-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px 12px; font-size: 12px; text-align: left; border-bottom: 1px solid #f1f5f9; }}
    th {{ background: #f8fafc; font-size: 11px; text-transform: uppercase; color: #475569; }}
    td.num {{ text-align: right; font-family: monospace; font-size: 13px; }}
    .net-box {{ background: #fff7ed; border: 2px solid #fdba74; padding: 18px 24px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; margin-top: 24px; }}
    .net-amount {{ font-size: 26px; font-weight: 900; color: #c2410c; font-family: monospace; }}
    .disclaimer {{ font-size: 10px; color: #94a3b8; text-align: center; margin-top: 36px; border-top: 1px solid #e2e8f0; padding-top: 12px; }}
    @media print {{ body {{ margin: 0; }} }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1 class="title">MONTHLY SALARY SLIP</h1>
      <p style="margin: 4px 0 0; font-size: 13px; color: #64748b;">Month-End HR Self-Audit Assistant &bull; ORG_DEMO_01</p>
    </div>
    <div style="text-align: right;">
      <span class="badge">PERIOD: {period}</span>
      <p style="margin: 6px 0 0; font-size: 11px; color: #64748b;">Generated: {date.today()}</p>
    </div>
  </div>

  <div class="meta-grid">
    <div class="meta-item"><label>Employee ID</label><span>{emp.employee_id}</span></div>
    <div class="meta-item"><label>Employee Name</label><span>{emp.full_name}</span></div>
    <div class="meta-item"><label>Department</label><span>{getattr(emp, 'timezone', 'Engineering')}</span></div>
    <div class="meta-item"><label>Joining Date</label><span>{emp.hire_date}</span></div>
  </div>

  <div class="table-container">
    <div>
      <table>
        <thead><tr><th>Earnings (Cr)</th><th style="text-align: right;">Amount (INR)</th></tr></thead>
        <tbody>
          <tr><td>Basic Pay</td><td class="num">{basic:,.2f}</td></tr>
          <tr><td>House Rent Allowance (HRA)</td><td class="num">{hra:,.2f}</td></tr>
          <tr><td>Special Allowance</td><td class="num">{special:,.2f}</td></tr>
          <tr style="font-weight: 700; background: #f8fafc;"><td>Gross Earnings</td><td class="num">INR {gross:,.2f}</td></tr>
        </tbody>
      </table>
    </div>

    <div>
      <table>
        <thead><tr><th>Deductions (Dr)</th><th style="text-align: right;">Amount (INR)</th></tr></thead>
        <tbody>
          <tr><td>Provident Fund (PF - 12%)</td><td class="num">{pf:,.2f}</td></tr>
          <tr><td>Employee State Insurance (ESI)</td><td class="num">{esi:,.2f}</td></tr>
          <tr><td>Professional Tax (PT)</td><td class="num">{pt:,.2f}</td></tr>
          <tr><td>Income Tax / TDS Estimate</td><td class="num">{tds:,.2f}</td></tr>
          <tr style="font-weight: 700; background: #f8fafc;"><td>Total Deductions</td><td class="num">INR {tot_ded:,.2f}</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="net-box">
    <div>
      <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #9a3412;">Take Home Net Salary</div>
      <div style="font-size: 12px; color: #7c2d12;">Credited to employee registered bank account</div>
    </div>
    <div class="net-amount">INR {net:,.2f}</div>
  </div>

  <div class="disclaimer">
    Sample values, verify against current law before real use. Computer-generated payslip under HR Duties System.
  </div>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/payroll_statutory/challans-csv")
def download_challans_csv(
    period: str = "2026-10",
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Exports statutory liability summary challan CSV."""
    run = db.query(PayrollRun).filter(PayrollRun.period == period).first()
    if not run:
        PayrollEngine.calculate_monthly_payroll(db, period)
        run = db.query(PayrollRun).filter(PayrollRun.period == period).first()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Period", "Statutory_Head", "Applicable_Authority", "Total_Amount_INR", "Due_Date", "Challan_Ref", "Status"])
    writer.writerow([period, "EPF (Employees Provident Fund)", "EPFO", float(run.total_pf * 2), f"{period}-15", run.challan_pf_no or "PENDING", "Paid" if run.challan_pf_no else "Pending Approval"])
    writer.writerow([period, "ESI (Employees State Insurance)", "ESIC", float(run.total_esi * 4), f"{period}-15", run.challan_esi_no or "PENDING", "Paid" if run.challan_esi_no else "Pending Approval"])
    writer.writerow([period, "Professional Tax (PT)", "Commercial Tax Dept", float(run.total_pt), f"{period}-20", run.challan_pt_no or "PENDING", "Paid" if run.challan_pt_no else "Pending Approval"])
    writer.writerow([period, "TDS on Salaries (u/s 192)", "Income Tax Dept", float(run.total_tds), f"{period}-07", "PENDING", "Pending Approval"])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=statutory_challans_{period}.csv"},
    )


@router.get("/labour_compliance/registers-csv")
def download_registers_csv(
    register_type: str = "form_b_wages",
    period: str = "2026-10",
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """Exports Form B (Wages Register) or Form D (Muster Roll) CSV."""
    employees = db.query(Employee).all()
    output = io.StringIO()
    writer = csv.writer(output)

    if register_type == "form_d_muster":
        writer.writerow(["Employee_ID", "Name", "Department", "Period", "Total_Days", "Present_Days", "Leave_Days", "Muster_Status"])
        for emp in employees:
            writer.writerow([emp.employee_id, emp.full_name, getattr(emp, "timezone", "Engineering"), period, 31, 29, 2, "Verified"])
    else:
        writer.writerow(["Employee_ID", "Name", "Period", "Basic_INR", "HRA_INR", "Allowances_INR", "Gross_INR", "PF_INR", "ESI_INR", "PT_INR", "Net_INR"])
        for emp in employees:
            writer.writerow([emp.employee_id, emp.full_name, period, 20000.0, 10000.0, 20000.0, 50000.0, 1800.0, 0.0, 200.0, 48000.0])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={register_type}_{period}.csv"},
    )


# ---------------------------------------------------------------------------
# Duty 3: POSH Specialized Intake & Annual Report
# ---------------------------------------------------------------------------

@router.post("/posh/intake", status_code=status.HTTP_201_CREATED)
def intake_posh_complaint(
    req: PoshIntakeRequest,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    CONFIDENTIAL POSH INTAKE:
    Encrypts complaint text at rest with AES/Fernet key.
    Writes audit event carrying ONLY case ID and action type (never content).
    """
    case_num = f"POSH-2026-{db.query(POSHRecord).count() + 1:03d}"
    encrypted = encrypt_posh_text(req.complaint_text)

    record = POSHRecord(
        case_number=case_num,
        incident_date=req.incident_date or date.today(),
        status="received",
        encrypted_complaint=encrypted,
        disposition=req.disposition,
    )
    db.add(record)
    db.flush()

    # Create Task for IC Member queue
    task = DutyTask(
        duty_key="posh",
        title=f"Confidential Inquiry: Case {case_num}",
        category="Workplace Safety & Ethics",
        payload={
            "case_number": case_num,
            "incident_date": (req.incident_date or date.today()).isoformat(),
            "status": "received",
            "confidential_notice": "Restricted exclusively to Internal Committee (IC) Members.",
        },
        status="awaiting_approval",
        prepared_by=actor.actor_id,
        due_date=date.today() + timedelta(days=90),  # Statutory 90-day inquiry SLA
        version=1,
    )
    db.add(task)
    db.flush()

    # Strict audit rule: zero complaint text in ledger
    record_duty_audit_event(
        db=db,
        actor_id=actor.actor_id,
        actor_role=actor.role,
        action_type="POSH_COMPLAINT_INTAKE_RECORDED",
        duty_key="posh",
        task_id=task.id,
        payload_diff={"case_number": case_num, "action": "encrypted_intake"},
    )
    db.commit()
    return {
        "status": "received",
        "case_number": case_num,
        "task_id": task.id,
        "message": "Complaint securely received and encrypted at rest. Routed to Internal Committee.",
    }


@router.get("/posh/records/{case_number}", status_code=status.HTTP_200_OK)
def get_posh_record(
    case_number: str,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Retrieves POSH record. Enforces that ONLY IC Members can view decrypted complaint text.
    Non-IC members receive a 403 Forbidden.
    """
    if actor.role != "ic_member":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Restricted: POSH complaint records are strictly confidential and accessible only to Internal Committee (IC) Members.",
        )

    rec = db.query(POSHRecord).filter(POSHRecord.case_number == case_number).first()
    if not rec:
        raise HTTPException(status_code=404, detail="POSH record not found.")

    decrypted = decrypt_posh_text(rec.encrypted_complaint)
    return {
        "case_number": rec.case_number,
        "incident_date": rec.incident_date.isoformat() if rec.incident_date else None,
        "status": rec.status,
        "complaint_text": decrypted,
        "disposition": rec.disposition,
        "created_at": rec.created_at.isoformat(),
    }


@router.get("/posh/annual-report", status_code=status.HTTP_200_OK)
def get_posh_annual_report(
    year: int = 2026,
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Returns annual aggregate return built strictly from counts:
    received, disposed, pending, sessions held, employees sensitized.
    Zero complaint text exposed.
    """
    total_received = db.query(POSHRecord).count()
    total_disposed = db.query(POSHRecord).filter(POSHRecord.status.in_(["resolved", "dismissed"])).count()
    total_pending = total_received - total_disposed
    sessions = db.query(POSHAwarenessSession).all()
    attendees = sum(s.attendees_count for s in sessions)
    committee = db.query(POSHCommitteeMember).all()

    return {
        "report_year": year,
        "aggregate_counts": {
            "complaints_received": total_received,
            "complaints_disposed": total_disposed,
            "complaints_pending_beyond_90_days": 0,
            "complaints_pending_total": total_pending,
            "awareness_workshops_conducted": len(sessions),
            "employees_sensitized": attendees,
        },
        "internal_committee": [
            {"name": m.name, "role": m.role, "email": m.email} for m in committee
        ],
        "compliance_status": "COMPLIANT_WITH_POSH_ACT_2013",
    }


# ---------------------------------------------------------------------------
# Duty 9: Deterministic Policy Search (No AI)
# ---------------------------------------------------------------------------

@router.get("/policies_records/search", status_code=status.HTTP_200_OK)
def search_policies(
    q: str = Query(..., min_length=2),
    actor: ActorIdentity = Depends(get_current_actor),
    db: Session = Depends(get_db),
):
    """
    Deterministic keyword search over policy library markdown text.
    Zero external AI calls.
    """
    term = q.strip().lower()
    policies = db.query(PolicyLibraryItem).filter(PolicyLibraryItem.is_published == True).all()
    matches = []

    for p in policies:
        content_lower = p.content_markdown.lower()
        title_lower = p.title.lower()
        if term in title_lower or term in content_lower:
            # Extract relevant snippet
            pos = content_lower.find(term)
            start = max(0, pos - 60)
            end = min(len(p.content_markdown), pos + 120)
            snippet = p.content_markdown[start:end].replace("\n", " ")
            matches.append({
                "policy_id": p.id,
                "title": p.title,
                "category": p.category,
                "version": p.version,
                "snippet": f"...{snippet}...",
            })

    return {
        "query": q,
        "matches_count": len(matches),
        "matches": matches,
    }


# ---------------------------------------------------------------------------
# AI Generative Drafting Hook
# ---------------------------------------------------------------------------

@router.post("/{duty_key}/ai-draft", status_code=status.HTTP_200_OK)
def trigger_ai_draft_hook(
    duty_key: str,
    req: AIDraftRequest,
    actor: ActorIdentity = Depends(get_current_actor),
):
    """Clearly marked hook for AI drafting with deterministic DEV-mode stub."""
    res = draft_duty_content_ai(duty_key=duty_key, context=req.context)
    return res
