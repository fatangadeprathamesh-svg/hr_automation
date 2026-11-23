from datetime import date, timedelta
from typing import Dict, Any, List
from collections import defaultdict
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity


class LeaveConflictRule(BaseRule):
    rule_id = "LEAVE_CONFLICT"
    rule_version = "1.0"

    def evaluate(
        self,
        context: Dict[str, Any],
        policy_config: Dict[str, Any],
        policy_version: str,
    ) -> List[RuleResult]:
        """
        LEAVE_CONFLICT:
        1. Approved leave day where employee also has attendance Present/Late or punches (blocking).
        2. Half-day leave where timesheet hours exceed 4.5h (warning).
        """
        results: List[RuleResult] = []
        leaves = context.get("leave", [])
        attendance = context.get("attendance", [])
        timesheets = context.get("timesheets", [])

        if not leaves:
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    status=RuleOutcome.NOT_APPLICABLE,
                    severity=RuleSeverity.INFO,
                    evidence={"message": "No leave records found for this period."},
                    policy_version=policy_version,
                    suggested_action=None,
                )
            )
            return results

        # Index attendance by work_date
        attendance_by_date = {}
        for att in attendance:
            if hasattr(att, "work_date") and att.work_date:
                attendance_by_date[att.work_date] = att

        # Index timesheets by work_date
        timesheets_by_date = {}
        for ts in timesheets:
            if hasattr(ts, "work_date") and ts.work_date:
                timesheets_by_date[ts.work_date] = ts

        for lv in leaves:
            leave_id = getattr(lv, "source_record_id", None) or getattr(lv, "id", "UNKNOWN")
            approval = (getattr(lv, "approval_state", "") or "").strip().lower()

            start_d = getattr(lv, "start_date", None)
            end_d = getattr(lv, "end_date", None)
            try:
                days_taken = float(getattr(lv, "days_taken", 1.0) or 0.0)
            except (ValueError, TypeError):
                days_taken = -1.0

            # Data health check: missing dates, inverted range, or negative days
            if not start_d or not end_d or start_d > end_d or days_taken < 0:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": leave_id,
                            "start_date": str(start_d) if start_d else None,
                            "end_date": str(end_d) if end_d else None,
                            "days_taken": days_taken,
                            "message": "Corrupted leave record: invalid date range or negative days.",
                        },
                        is_data_health_issue=True,
                        policy_version=policy_version,
                        suggested_action="Data health issue: contact HRIS admin to correct leave dates.",
                    )
                )
                continue

            if approval != "approved":
                continue

            cur = start_d
            conflict_found = False
            while cur <= end_d:
                # 1. Check Attendance
                att = attendance_by_date.get(cur)
                if att:
                    att_status = (getattr(att, "status", "") or "").strip().lower()
                    att_hours = float(getattr(att, "hours_total", 0.0) or 0.0)
                    has_punch = att.clock_in is not None

                    if att_status in ("present", "late") or att_hours > 0 or has_punch:
                        conflict_found = True
                        results.append(
                            RuleResult(
                                rule_id=self.rule_id,
                                rule_version=self.rule_version,
                                status=RuleOutcome.FAIL,
                                severity=RuleSeverity.BLOCKING,
                                evidence={
                                    "record_id": leave_id,
                                    "leave_record_id": leave_id,
                                    "attendance_record_id": getattr(att, "source_record_id", att.id),
                                    "conflict_date": str(cur),
                                    "attendance_status": att_status or "Present",
                                    "leave_type": getattr(lv, "leave_type", "leave"),
                                },
                                policy_version=policy_version,
                                suggested_action=f"Approved leave on {cur} conflicts with attendance ({att_status or 'Present'}).",
                            )
                        )

                # 2. Check Timesheets
                ts = timesheets_by_date.get(cur)
                if ts:
                    ts_hours = float(getattr(ts, "regular_hours", 0.0) or 0.0) + float(getattr(ts, "overtime_hours", 0.0) or 0.0)
                    if days_taken <= 0.5 and ts_hours > 4.5:
                        conflict_found = True
                        results.append(
                            RuleResult(
                                rule_id=self.rule_id,
                                rule_version=self.rule_version,
                                status=RuleOutcome.FAIL,
                                severity=RuleSeverity.WARNING,
                                evidence={
                                    "record_id": leave_id,
                                    "leave_record_id": leave_id,
                                    "timesheet_record_id": getattr(ts, "source_record_id", ts.id),
                                    "conflict_date": str(cur),
                                    "timesheet_hours": ts_hours,
                                    "leave_days": days_taken,
                                    "message": f"Half-day leave with {ts_hours}h exceeds 4.5h threshold.",
                                },
                                policy_version=policy_version,
                                suggested_action="Half-day leave cannot exceed 4.5h logged work.",
                            )
                        )
                    elif days_taken > 0.5 and ts_hours > 0:
                        conflict_found = True
                        results.append(
                            RuleResult(
                                rule_id=self.rule_id,
                                rule_version=self.rule_version,
                                status=RuleOutcome.FAIL,
                                severity=RuleSeverity.BLOCKING,
                                evidence={
                                    "record_id": leave_id,
                                    "leave_record_id": leave_id,
                                    "timesheet_record_id": getattr(ts, "source_record_id", ts.id),
                                    "conflict_date": str(cur),
                                    "timesheet_hours": ts_hours,
                                    "leave_days": days_taken,
                                },
                                policy_version=policy_version,
                                suggested_action=f"Full-day leave on {cur} conflicts with logged timesheet hours.",
                            )
                        )

                cur += timedelta(days=1)

            if not conflict_found:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.PASS,
                        severity=RuleSeverity.INFO,
                        evidence={
                            "record_id": leave_id,
                            "start_date": str(start_d),
                            "end_date": str(end_d),
                        },
                        policy_version=policy_version,
                    )
                )

        return results
