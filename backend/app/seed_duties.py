import os
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
from app.models.hr import Employee
from app.models.auth import UserAuth
from app.auth.service import hash_password
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
from app.services.duty_engine import (
    DutyEngineService,
    PayrollEngine,
    encrypt_posh_text,
    record_duty_audit_event,
)

logger = logging.getLogger(__name__)


def seed_ic_member(db: Session):
    """Seeds dedicated IC Member (Irene IC Member - IC001) for POSH confidential inquiry gate."""
    existing_emp = db.query(Employee).filter(Employee.employee_id == "IC001").first()
    if not existing_emp:
        emp = Employee(
            employee_id="IC001",
            organization_id="ORG_DEMO_01",
            email="irene.ic@company.com",
            full_name="Irene IC Member",
            manager_id=None,
            timezone="Internal Committee",
            hire_date=date(2023, 1, 1),
            is_active=True,
        )
        db.add(emp)
        db.flush()

    existing_auth = db.query(UserAuth).filter(UserAuth.employee_id == "IC001").first()
    if not existing_auth:
        auth = UserAuth(
            employee_id="IC001",
            organization_id="ORG_DEMO_01",
            email="irene.ic@company.com",
            password_hash=hash_password("Password123!"),
            role="ic_member",
            is_verified=True,
        )
        db.add(auth)
        db.commit()


def seed_all_duties(db: Session):
    """Seeds complete, realistic dataset across all 10 HR Duties for the 30 employees."""
    seed_ic_member(db)
    employees = db.query(Employee).all()
    if not employees:
        logger.warning("No employees found. Seed employees first.")
        return

    # -----------------------------------------------------------------------
    # Duty 1: Payroll & Statutory
    # -----------------------------------------------------------------------
    config = db.query(PayrollConfig).first()
    if not config:
        config = PayrollConfig(
            effective_from=date(2026, 1, 1),
            basic_pct=Decimal("40.0"),
            hra_pct=Decimal("20.0"),
            pf_rate_pct=Decimal("12.0"),
            pf_wage_ceiling=Decimal("15000.00"),
            esi_rate_pct=Decimal("0.75"),
            esi_wage_ceiling=Decimal("21000.00"),
            pt_slabs={"Karnataka": 200, "Maharashtra": 200, "Tamil Nadu": 200},
            standard_deduction=Decimal("50000.00"),
            disclaimer="Sample values, verify against current law before real use",
        )
        db.add(config)
        db.flush()

    for emp in employees:
        sal = db.query(EmployeeSalary).filter(EmployeeSalary.employee_id == emp.employee_id).first()
        if not sal:
            is_mgr = emp.employee_id.startswith("MGR") or emp.employee_id.startswith("HR")
            ctc = 1500000.00 if is_mgr else 720000.00
            monthly_g = ctc / 12.0
            sal = EmployeeSalary(
                employee_id=emp.employee_id,
                ctc_annual=Decimal(str(ctc)),
                monthly_gross=Decimal(str(monthly_g)),
                basic_pay=Decimal(str(round(monthly_g * 0.40, 2))),
                hra=Decimal(str(round(monthly_g * 0.20, 2))),
                special_allowance=Decimal(str(round(monthly_g * 0.40, 2))),
                state="Karnataka",
            )
            db.add(sal)
    db.commit()

    # Pre-calculate 2026-10 payroll run
    if not db.query(PayrollRun).filter(PayrollRun.period == "2026-10").first():
        PayrollEngine.calculate_monthly_payroll(db, period="2026-10")

    # -----------------------------------------------------------------------
    # Duty 2: Labour Law Compliance
    # -----------------------------------------------------------------------
    if db.query(ComplianceDeadline).count() == 0:
        deadlines = [
            ComplianceDeadline(authority="TDS", period="2026-10", due_date=date(2026, 11, 7), title="TDS Deposit (u/s 192)", description="Monthly tax deducted at source deposit with challan ITNS-281.", reminder_days=[7, 3, 1]),
            ComplianceDeadline(authority="PF", period="2026-10", due_date=date(2026, 11, 15), title="EPF Monthly Remittance (ECR)", description="Electronic Challan cum Return filing for employee & employer contribution.", reminder_days=[7, 3, 1]),
            ComplianceDeadline(authority="ESI", period="2026-10", due_date=date(2026, 11, 15), title="ESIC Monthly Contribution", description="Payment of health insurance contribution for eligible wage ceiling staff.", reminder_days=[7, 3, 1]),
            ComplianceDeadline(authority="PT", period="2026-10", due_date=date(2026, 11, 20), title="Professional Tax Return (Form 5A)", description="Karnataka commercial taxes department monthly payment & return.", reminder_days=[7, 3, 1]),
        ]
        db.add_all(deadlines)
        db.commit()

        for dl in deadlines:
            DutyEngineService.create_task(
                db=db,
                duty_key="labour_compliance",
                title=f"Statutory Return Sign-off: {dl.title} ({dl.period})",
                category="Statutory & Legal",
                payload={"authority": dl.authority, "due_date": dl.due_date.isoformat(), "description": dl.description},
                prepared_by="bot:compliance_calendar",
                due_date=dl.due_date,
                status_val="awaiting_approval",
            )

    # -----------------------------------------------------------------------
    # Duty 3: POSH (Confidential)
    # -----------------------------------------------------------------------
    if db.query(POSHCommitteeMember).count() == 0:
        members = [
            POSHCommitteeMember(name="Dr. Aruna Rao", role="Presiding Officer", email="aruna.ic@company.com", contact="+91-9845012345"),
            POSHCommitteeMember(name="Adv. Sunita Nair", role="External Member (Legal / NGO)", email="sunita.external@lawngo.org", contact="+91-9845098765"),
            POSHCommitteeMember(name="Carol HR Admin", role="Internal Member (HR)", email="carol.hr@company.com", contact="+91-9845055555"),
            POSHCommitteeMember(name="Irene IC Member", role="Internal Member (Senior Faculty)", email="irene.ic@company.com", contact="+91-9845077777"),
        ]
        db.add_all(members)

        sessions = [
            POSHAwarenessSession(topic="Workplace Respect, Boundaries, and POSH Act 2013", session_date=date(2026, 6, 15), attendees_count=30, mode="Hybrid Virtual & Townhall"),
            POSHAwarenessSession(topic="Managerial Responsibilities & Prompt Reporting Protocol", session_date=date(2026, 9, 20), attendees_count=12, mode="In-Person Interactive Workshop"),
        ]
        db.add_all(sessions)
        db.commit()

        # Seed 1 encrypted confidential complaint
        raw_complaint = (
            "During the quarterly team offsite on 2026-10-14, inappropriate verbal comments and persistent "
            "unwanted personal overtures were directed at the complainant by a colleague despite explicit objections. "
            "Witnesses present at the dinner table can corroborate the conversation."
        )
        encrypted_body = encrypt_posh_text(raw_complaint)
        posh_rec = POSHRecord(
            case_number="POSH-2026-001",
            incident_date=date(2026, 10, 14),
            status="inquiry_ongoing",
            encrypted_complaint=encrypted_body,
            disposition="Notice issued to respondent; inquiry committee hearing scheduled.",
        )
        db.add(posh_rec)
        db.commit()

        DutyEngineService.create_task(
            db=db,
            duty_key="posh",
            title="Confidential Inquiry Hearing: Case POSH-2026-001",
            category="Workplace Safety & Ethics",
            payload={
                "case_number": "POSH-2026-001",
                "incident_date": "2026-10-14",
                "status": "inquiry_ongoing",
                "confidential_notice": "Restricted exclusively to Internal Committee (IC) Members.",
            },
            prepared_by="bot:posh_engine",
            due_date=date(2026, 11, 28),
            status_val="awaiting_approval",
        )

    # -----------------------------------------------------------------------
    # Duty 4: Discipline & Grievance
    # -----------------------------------------------------------------------
    if db.query(GrievanceCase).count() == 0:
        c1 = GrievanceCase(
            case_number="GRV-2026-012",
            employee_id="EMP001",
            category="misconduct",
            title="Unauthorized absence and timesheet record mismatch",
            description="Repeated discrepancy between access badge swipe logs and manual timesheet claims in October cycle.",
            sla_due_date=date.today() + timedelta(days=5),
            status="in_review",
        )
        db.add(c1)
        db.flush()

        n1 = DisciplinaryNotice(
            case_id=c1.id,
            notice_type="show_cause",
            recipient_id="EMP001",
            draft_text="FORMAL SHOW CAUSE NOTICE: You are requested to clarify punch discrepancies noted between 2026-10-12 and 2026-10-16 within 48 hours.",
            status="draft",
        )
        db.add(n1)
        db.commit()

        DutyEngineService.create_task(
            db=db,
            duty_key="discipline_grievance",
            title=f"Authorize Show Cause Notice: {c1.case_number} (EMP001)",
            category="Employee Relations",
            employee_id="EMP001",
            payload={"case_id": c1.id, "case_number": c1.case_number, "draft_text": n1.draft_text},
            prepared_by="bot:grievance",
            status_val="awaiting_approval",
        )

    # -----------------------------------------------------------------------
    # Duty 5: Recruitment
    # -----------------------------------------------------------------------
    if db.query(JobOpening).count() == 0:
        job = JobOpening(
            title="Senior Full-Stack Engineer",
            department="Engineering",
            min_experience=3,
            required_skills=["React", "Python", "FastAPI", "SQL", "Tailwind"],
            template_text="We are looking for a Senior Full-Stack Engineer with strong Python and modern web framework expertise.",
            status="open",
        )
        db.add(job)
        db.flush()

        # Seed 3 applicants with transparent score calculation (Excluding demographics)
        apps = [
            JobApplicant(
                job_id=job.id,
                name="Siddharth Rao",
                email="siddharth.rao@talentdemo.com",
                education="B.Tech Computer Science",
                years_experience=Decimal("4.5"),
                skills=["React", "Python", "FastAPI", "SQL", "Docker"],
                screening_score=88,
                screening_reasons=[
                    "Experience: 4.5 yrs vs 3 req (40/40 pts)",
                    "Education: B.Tech CS (30/30 pts)",
                    "Skill Match: 4 of 5 keywords matched (18/30 pts)",
                    "Fairness Rule: Objective screening criteria only.",
                ],
                status="shortlisted",
            ),
            JobApplicant(
                job_id=job.id,
                name="Deepa Raman",
                email="deepa.raman@talentdemo.com",
                education="BCA / MCA",
                years_experience=Decimal("3.0"),
                skills=["Python", "Django", "SQL"],
                screening_score=72,
                screening_reasons=[
                    "Experience: 3.0 yrs vs 3 req (35/40 pts)",
                    "Education: MCA (30/30 pts)",
                    "Skill Match: 2 of 5 keywords matched (7/30 pts)",
                ],
                status="screened",
            ),
        ]
        db.add_all(apps)
        db.commit()

        DutyEngineService.create_task(
            db=db,
            duty_key="recruitment",
            title=f"Candidate Shortlist & Interview: Siddharth Rao ({job.title})",
            category="Talent Acquisition",
            payload={
                "applicant_id": apps[0].id,
                "candidate_name": "Siddharth Rao",
                "job_title": job.title,
                "screening_score": 88,
                "suggested_interview_slot": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            },
            prepared_by="bot:recruitment_screener",
            status_val="awaiting_approval",
        )

    # -----------------------------------------------------------------------
    # Duty 6: Onboarding
    # -----------------------------------------------------------------------
    if db.query(OnboardingChecklist).count() == 0:
        emp_new = employees[0]
        chk = OnboardingChecklist(
            employee_id=emp_new.employee_id,
            join_date=date(2026, 8, 1),
            probation_end_date=date(2026, 11, 1),
            doc_status="verified",
            it_status="provisioned",
            induction_status="completed",
            probation_status="in_probation",
        )
        db.add(chk)
        db.commit()

        DutyEngineService.create_task(
            db=db,
            duty_key="onboarding",
            title=f"Probation Confirmation Review: {emp_new.full_name} ({emp_new.employee_id})",
            category="Employee Lifecycle",
            employee_id=emp_new.employee_id,
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

    # -----------------------------------------------------------------------
    # Duty 7: Attendance & Leave Balances & Pre-Seeded Decisions
    # -----------------------------------------------------------------------
    if db.query(LeaveBalance).count() == 0:
        for emp in employees:
            b1 = LeaveBalance(employee_id=emp.employee_id, leave_type="casual", accrued=Decimal("12.0"), taken=Decimal("2.0"), remaining=Decimal("10.0"))
            b2 = LeaveBalance(employee_id=emp.employee_id, leave_type="sick", accrued=Decimal("10.0"), taken=Decimal("1.0"), remaining=Decimal("9.0"))
            b3 = LeaveBalance(employee_id=emp.employee_id, leave_type="earned", accrued=Decimal("15.0"), taken=Decimal("3.0"), remaining=Decimal("12.0"))
            db.add_all([b1, b2, b3])
        db.commit()

        # Seed 1 Auto-Approved Leave task with evidence
        DutyTask(
            duty_key="attendance_leave",
            title=f"Leave Request (Casual): Alice Employee (1.0d)",
            category="Time & Attendance",
            employee_id="EMP001",
            payload={
                "leave_type": "casual",
                "days_requested": 1.0,
                "rules_evaluated": {
                    "sufficient_balance": True,
                    "no_date_overlap": True,
                    "within_policy_limit": True,
                    "team_coverage_maintained": True,
                },
                "coverage_pct": 85.0,
                "auto_approved": True,
            },
            status="approved",
            prepared_by="bot:auto_approval",
            approver_id="bot:auto_approval",
            approver_role="system",
            decision_note="AUTO-APPROVED: Satisfies all 4 policy rules (balance, no overlap, duration limit, team coverage).",
            decided_at=datetime.now(timezone.utc) - timedelta(days=2),
            due_date=date.today(),
            version=2,
        )

        # Seed 1 Leave Exception awaiting human manager review (3 days > 2 day policy limit)
        DutyEngineService.create_task(
            db=db,
            duty_key="attendance_leave",
            title=f"Leave Exception (Casual): Bob Manager (3.0d)",
            category="Time & Attendance",
            employee_id="MGR001",
            payload={
                "leave_type": "casual",
                "days_requested": 3.0,
                "rules_evaluated": {
                    "sufficient_balance": True,
                    "no_date_overlap": True,
                    "within_policy_limit": False,
                    "team_coverage_maintained": True,
                },
                "exception_reasons": ["Casual leave duration (3.0 days) exceeds auto-approval limit (2.0 days)."],
            },
            prepared_by="bot",
            status_val="awaiting_approval",
        )

    # -----------------------------------------------------------------------
    # Duty 8: Offboarding & FNF
    # -----------------------------------------------------------------------
    if db.query(OffboardingCase).count() == 0:
        emp_exit = employees[-1]  # Last employee
        off = OffboardingCase(
            employee_id=emp_exit.employee_id,
            resignation_date=date(2026, 10, 1),
            last_working_date=date(2026, 10, 31),
            notice_required_days=30,
            notice_served_days=30,
            it_clearance=True,
            finance_clearance=True,
            admin_clearance=True,
            hr_clearance=False,
            pending_salary=Decimal("25000.00"),
            leave_encashment=Decimal("12000.00"),
            shortfall_recovery=Decimal("0.00"),
            gratuity_eligible=False,
            gratuity_amount=Decimal("0.00"),
            net_payable=Decimal("37000.00"),
            status="fnf_calculated",
        )
        db.add(off)
        db.commit()

        DutyEngineService.create_task(
            db=db,
            duty_key="offboarding_fnf",
            title=f"Full & Final Settlement Approval: {emp_exit.full_name} ({emp_exit.employee_id})",
            category="Employee Lifecycle",
            employee_id=emp_exit.employee_id,
            payload={
                "case_id": off.id,
                "pending_salary": 25000.00,
                "leave_encashment": 12000.00,
                "net_payable": 37000.00,
                "clearances_complete": ["IT", "Finance", "Admin"],
                "clearances_pending": ["HR"],
            },
            prepared_by="bot:fnf_calculator",
            status_val="awaiting_approval",
        )

    # -----------------------------------------------------------------------
    # Duty 9: Policies & Records
    # -----------------------------------------------------------------------
    if db.query(PolicyLibraryItem).count() == 0:
        p1 = PolicyLibraryItem(
            title="Leave & Attendance Policy 2026",
            category="leave",
            version="v2.1",
            content_markdown="""# Leave and Attendance Policy 2026

## 1. Casual Leave
Employees are entitled to 12 days of Casual Leave annually. Casual leave requests up to 2 days are evaluated automatically by the system.

## 2. Sick Leave
Sick leave accrues at 10 days per calendar year. Medical certification is required for absences exceeding 2 consecutive days.

## 3. Team Coverage Minimum
Every department must maintain at least 70% operational presence during normal business cycles.""",
            is_published=True,
            published_at=datetime.now(timezone.utc) - timedelta(days=60),
            approved_by="HR001",
        )
        p2 = PolicyLibraryItem(
            title="Code of Conduct & Business Ethics",
            category="code_of_conduct",
            version="v1.0",
            content_markdown="""# Code of Conduct and Ethics

All employees are required to adhere to zero-tolerance policies regarding bribery, workplace harassment, and data leaks. Conflicts of interest must be disclosed annually.""",
            is_published=True,
            published_at=datetime.now(timezone.utc) - timedelta(days=90),
            approved_by="HR001",
        )
        p3 = PolicyLibraryItem(
            title="Proposed Remote Work & Equipment Reimbursement Policy",
            category="compensation",
            version="v1.0-draft",
            content_markdown="""# Proposed Remote Work Policy (Draft)
High-speed internet stipend up to INR 1,500/month upon submission of validated ISP invoice.""",
            is_published=False,  # Unapproved draft!
            approved_by=None,
        )
        db.add_all([p1, p2, p3])

        # Retention records
        for emp in employees[:5]:
            r1 = RetentionRecord(record_type="tax", employee_id=emp.employee_id, retention_tag="Tax Records: 8 Years", expires_at=date(2034, 3, 31))
            r2 = RetentionRecord(record_type="personnel", employee_id=emp.employee_id, retention_tag="Personnel Dossier: 10 Years", expires_at=date(2036, 12, 31))
            db.add_all([r1, r2])
        db.commit()

        # Task for draft policy approval
        DutyEngineService.create_task(
            db=db,
            duty_key="policies_records",
            title="Policy Publication Sign-off: Remote Work & Equipment Reimbursement",
            category="Governance & Compliance",
            payload={"policy_id": p3.id, "version": "v1.0-draft"},
            prepared_by="bot:policy_manager",
            status_val="awaiting_approval",
        )

    # -----------------------------------------------------------------------
    # Duty 10: Performance Reviews & Feedback
    # -----------------------------------------------------------------------
    if db.query(PerformanceCycle).count() == 0:
        cycle = PerformanceCycle(cycle_name="2026 Annual Performance Cycle", period="2026-H2", status="active")
        db.add(cycle)
        db.flush()

        for emp in employees[:3]:
            rev = PerformanceReview(
                cycle_id=cycle.id,
                employee_id=emp.employee_id,
                manager_id=emp.manager_id or "MGR001",
                self_goals_json=[
                    {"goal": "Deliver compliance ledger automation", "weight": 40, "self_rating": 4.5},
                    {"goal": "Reduce month-end audit exception rate", "weight": 60, "self_rating": 4.0},
                ],
                peer_feedback_json=[
                    {"peer": "EMP002", "rating": 4.0, "comment": "Great teamwork and prompt support."},
                    {"peer": "EMP003", "rating": 4.5, "comment": "Excellent technical execution."},
                ],
                deterministic_summary={
                    "average_peer_rating": 4.25,
                    "self_rating": 4.2,
                    "reviews_completed": 2,
                },
            )
            db.add(rev)
            db.flush()

            DutyEngineService.create_task(
                db=db,
                duty_key="performance",
                title=f"Performance Rating & Increment Decision: {emp.full_name} ({emp.employee_id})",
                category="Talent Management",
                employee_id=emp.employee_id,
                payload={
                    "review_id": rev.id,
                    "manager_id": rev.manager_id,
                    "average_peer_rating": 4.25,
                    "self_rating": 4.2,
                },
                prepared_by="bot:performance_aggregator",
                status_val="awaiting_approval",
            )
        db.commit()

    logger.info("Successfully seeded all 10 HR Duties with realistic data for 30 employees.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_all_duties(db)
    finally:
        db.close()
