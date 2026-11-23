from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.hr import (
    Employee,
    SourceImport,
    Attendance,
    Leave,
    Timesheet,
    ExpenseClaim,
    Document,
    Correction,
    PolicyVersion,
    AuditRun,
    AuditFlag,
    AuditEvent,
)
from app.models.base import generate_uuid
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity
from app.rules.missing_punch import MissingPunchRule
from app.rules.hours_mismatch import HoursMismatchRule
from app.rules.missing_receipt import MissingReceiptRule
from app.rules.leave_conflict import LeaveConflictRule
from app.rules.duplicate_claim import DuplicateClaimRule
from app.rules.over_limit_claim import OverLimitClaimRule
from app.rules.unapproved_overtime import UnapprovedOvertimeRule
from app.rules.pending_approvals import PendingApprovalsRule
from app.rules.expiring_documents import ExpiringDocumentsRule

DEFAULT_POLICY_VERSION = "POLICY-2026.1"
DEFAULT_POLICY_CONFIG = {
    "missing_punch": {
        "grace_period_minutes": 60,
    },
    "hours_mismatch": {
        "tolerance_minutes": 30,
    },
    "missing_receipt": {
        "receipt_required_threshold": 25.0,
    },
    "leave_conflict": {
        "half_day_tolerance_hours": 4.5,
    },
    "duplicate_claim": {
        "match_receipt_reference": True,
        "match_date_amount_merchant": True,
    },
    "over_limit_claim": {
        "category_limits": {
            "meals": 60.0,
            "travel": 300.0,
            "software": 150.0,
            "training": 400.0,
            "fuel": 80.0,
        },
        "default_limit": 300.0,
    },
    "unapproved_overtime": {
        "standard_daily_hours": 8.0,
        "overtime_blocking_threshold": 12.0,
    },
    "pending_approvals": {},
    "expiring_documents": {
        "warning_days": 60,
        "blocking_days": 30,
    },
}


def get_period_date_range(period: str) -> tuple[date, date]:
    parts = period.split("-")
    year = int(parts[0])
    month = int(parts[1])
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    return start_date, end_date


class AuditEngine:
    def __init__(self, rules: Optional[List[BaseRule]] = None):
        if rules is None:
            self.rules: List[BaseRule] = [
                MissingPunchRule(),
                HoursMismatchRule(),
                MissingReceiptRule(),
                LeaveConflictRule(),
                DuplicateClaimRule(),
                OverLimitClaimRule(),
                UnapprovedOvertimeRule(),
                PendingApprovalsRule(),
                ExpiringDocumentsRule(),
            ]
        else:
            self.rules = rules

    def get_or_create_policy(self, db: Session, policy_version_id: Optional[str] = None) -> PolicyVersion:
        p_id = policy_version_id or DEFAULT_POLICY_VERSION
        policy = db.query(PolicyVersion).filter(PolicyVersion.policy_version == p_id).first()
        if not policy:
            policy = PolicyVersion(
                policy_version=p_id,
                effective_from=date(2026, 1, 1),
                effective_to=None,
                rule_configurations=DEFAULT_POLICY_CONFIG,
                is_active=True,
            )
            db.add(policy)
            db.commit()
            db.refresh(policy)
        else:
            # Ensure any new default rule configuration sections exist
            merged_config = dict(DEFAULT_POLICY_CONFIG)
            if policy.rule_configurations:
                merged_config.update(policy.rule_configurations)
            policy.rule_configurations = merged_config
            db.commit()
            db.refresh(policy)
        return policy

    def run_audit(
        self,
        db: Session,
        employee_id: str,
        period: str,
        trigger_source: str = "manual",
        policy_version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes deterministic rules against an employee's month-end data.
        Persists AuditRun and AuditFlags.
        """
        policy = self.get_or_create_policy(db, policy_version_id)
        start_d, end_d = get_period_date_range(period)

        # 1. Gather context using clean date boundary filtering
        attendance_records = db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.work_date >= start_d,
            Attendance.work_date < end_d,
        ).all()

        leave_records = db.query(Leave).filter(
            Leave.employee_id == employee_id,
            Leave.start_date < end_d,
            Leave.end_date >= start_d,
        ).all()

        timesheet_records = db.query(Timesheet).filter(
            Timesheet.employee_id == employee_id,
            Timesheet.work_date >= start_d,
            Timesheet.work_date < end_d,
        ).all()

        expense_records = db.query(ExpenseClaim).filter(
            ExpenseClaim.employee_id == employee_id,
            ExpenseClaim.claim_date >= start_d,
            ExpenseClaim.claim_date < end_d,
        ).all()

        document_records = db.query(Document).filter(
            Document.employee_id == employee_id,
        ).all()

        correction_records = db.query(Correction).filter(
            Correction.employee_id == employee_id,
        ).all()

        # Check source feed completeness for this period
        imports = db.query(SourceImport).filter(
            SourceImport.covered_period == period
        ).all()
        is_attendance_feed_complete = True
        if imports:
            for imp in imports:
                if imp.source_system == "attendance" and not imp.completeness_flag:
                    is_attendance_feed_complete = False

        context = {
            "employee_id": employee_id,
            "period": period,
            "attendance": attendance_records,
            "leave": leave_records,
            "timesheets": timesheet_records,
            "expense_claims": expense_records,
            "documents": document_records,
            "corrections": correction_records,
            "attendance_feed_complete": is_attendance_feed_complete,
        }

        # 2. Evaluate all rules
        all_results: List[RuleResult] = []
        for rule in self.rules:
            rule_flags = rule.evaluate(context, policy.rule_configurations, policy.policy_version)
            all_results.extend(rule_flags)

        # 3. Aggregate metrics
        blocking_count = sum(
            1 for r in all_results
            if r.status == RuleOutcome.FAIL and r.severity == RuleSeverity.BLOCKING
        )
        warning_count = sum(
            1 for r in all_results
            if r.severity == RuleSeverity.WARNING and r.status in (RuleOutcome.FAIL, RuleOutcome.UNKNOWN)
        )
        has_data_health_issue = any(r.is_data_health_issue for r in all_results) or not is_attendance_feed_complete
        data_health = "incomplete" if has_data_health_issue else "complete"

        # Submission gate pre-check: zero blockers AND complete data health
        submission_allowed = (blocking_count == 0 and data_health == "complete")

        # De-duplicate: clean up previous runs and flags for this employee & period
        old_runs = db.query(AuditRun).filter(
            AuditRun.employee_id == employee_id,
            AuditRun.period == period,
        ).all()
        for old_r in old_runs:
            db.query(AuditFlag).filter(AuditFlag.audit_run_id == old_r.audit_run_id).delete(synchronize_session=False)
            db.delete(old_r)
        db.flush()

        # 4. Persist AuditRun
        audit_run = AuditRun(
            audit_run_id=generate_uuid(),
            employee_id=employee_id,
            period=period,
            policy_version=policy.policy_version,
            trigger_source=trigger_source,
            blocking_count=blocking_count,
            warning_count=warning_count,
            data_health=data_health,
            submission_allowed=submission_allowed,
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit_run)
        db.flush()

        # 5. Persist Flags keyed by rule + record_id
        persisted_flags = []
        for r in all_results:
            rec_id = r.evidence.get("record_id")
            flag = AuditFlag(
                flag_id=generate_uuid(),
                audit_run_id=audit_run.audit_run_id,
                rule_id=r.rule_id,
                record_id=str(rec_id) if rec_id else None,
                rule_version=r.rule_version,
                outcome=r.status.value,
                severity=r.severity.value,
                evidence=r.evidence,
                policy_version=r.policy_version,
                suggested_action=r.suggested_action,
                resolution_status="unresolved" if r.status in (RuleOutcome.FAIL, RuleOutcome.UNKNOWN) else "resolved",
            )
            db.add(flag)
            persisted_flags.append(flag)

        db.commit()

        return {
            "audit_run_id": audit_run.audit_run_id,
            "employee_id": audit_run.employee_id,
            "period": audit_run.period,
            "policy_version": audit_run.policy_version,
            "blocking_count": audit_run.blocking_count,
            "warning_count": audit_run.warning_count,
            "data_health": audit_run.data_health,
            "submission_allowed": audit_run.submission_allowed,
            "flags": [
                {
                    "flag_id": f.flag_id,
                    "rule_id": f.rule_id,
                    "record_id": f.record_id,
                    "rule_version": f.rule_version,
                    "status": f.outcome,
                    "severity": f.severity,
                    "evidence": f.evidence,
                    "policy_version": f.policy_version,
                    "suggested_action": f.suggested_action,
                    "resolution_status": f.resolution_status,
                }
                for f in persisted_flags
            ],
        }

    def evaluate_all_employees(
        self,
        db: Session,
        period: Optional[str] = None,
        trigger_source: str = "batch_evaluation",
    ) -> Dict[str, Any]:
        """
        Executes audit evaluation across all employees for specified or detected periods.
        Logs an immutable hash-chained audit event into the ledger.
        """
        from sqlalchemy import distinct, func
        # 1. Determine target periods
        periods = set()
        if period:
            periods.add(period)
        else:
            # Detect periods from operational tables
            for row in db.query(distinct(func.strftime("%Y-%m", Attendance.work_date))).all():
                if row[0]:
                    periods.add(row[0])
            for row in db.query(distinct(func.strftime("%Y-%m", Timesheet.work_date))).all():
                if row[0]:
                    periods.add(row[0])
            for row in db.query(distinct(func.strftime("%Y-%m", ExpenseClaim.claim_date))).all():
                if row[0]:
                    periods.add(row[0])
            if not periods:
                periods.add("2026-10")

        # 2. Find all employees
        employees = db.query(Employee).all()
        total_blocking = 0
        total_warning = 0
        total_runs = 0
        sorted_periods = sorted(list(periods))

        for p in sorted_periods:
            for emp in employees:
                res = self.run_audit(
                    db=db,
                    employee_id=emp.employee_id,
                    period=p,
                    trigger_source=trigger_source,
                )
                total_blocking += res.get("blocking_count", 0)
                total_warning += res.get("warning_count", 0)
                total_runs += 1

        # 3. Write immutable audit ledger event
        run_batch_id = generate_uuid()
        try:
            db.add(AuditEvent(
                organization_id="ORG_DEMO_01",
                actor_id="system",
                actor_role="system",
                action_type="EVALUATION_RUN",
                target_entity="audit_runs",
                target_id=run_batch_id,
                payload_diff={
                    "run_batch_id": run_batch_id,
                    "periods": sorted_periods,
                    "total_employees": len(employees),
                    "total_runs": total_runs,
                    "total_blocking": total_blocking,
                    "total_warning": total_warning,
                    "trigger_source": trigger_source,
                }
            ))
            db.commit()
        except Exception as audit_err:
            db.rollback()

        return {
            "run_batch_id": run_batch_id,
            "periods": sorted_periods,
            "total_employees": len(employees),
            "total_runs": total_runs,
            "total_blocking": total_blocking,
            "total_warning": total_warning,
        }
