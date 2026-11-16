from datetime import date
from typing import Dict, Any, List
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
            if att.work_date:
                attendance_by_date[att.work_date] = att

        # Index timesheets by work_date
        timesheets_by_date = {}
        for ts in timesheets:
            if ts.work_date:
                timesheets_by_date[ts.work_date] = ts

        half_day_limit = float(
            policy_config.get("leave_conflict", {}).get("half_day_tolerance_hours", 4.5)
        )

        for lv in leaves:
            leave_id = getattr(lv, "source_record_id", None) or getattr(lv, "id", "UNKNOWN")
            approval = getattr(lv, "approval_state", "approved")

            # Missing or corrupted dates -> Data health issue (UNKNOWN)
            if not lv.start_date or not lv.end_date:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": leave_id,
                            "error": "MISSING_LEAVE_DATES",
                            "start_date": str(lv.start_date) if lv.start_date else None,
                            "end_date": str(lv.end_date) if lv.end_date else None,
                        },
                        policy_version=policy_version,
                        suggested_action="Investigate leave record with missing start/end date.",
                        is_data_health_issue=True,
                    )
                )
                continue

            if lv.start_date > lv.end_date:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": leave_id,
                            "error": "INVALID_DATE_RANGE",
                            "start_date": str(lv.start_date),
                            "end_date": str(lv.end_date),
                        },
                        policy_version=policy_version,
                        suggested_action="Correct corrupted leave record where start date exceeds end date.",
                        is_data_health_issue=True,
                    )
                )
                continue

            days_taken = float(getattr(lv, "days_taken", 1.0) or 0.0)
            if days_taken < 0:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": leave_id,
                            "error": "NEGATIVE_DAYS_TAKEN",
                            "days_taken": days_taken,
                        },
                        policy_version=policy_version,
                        suggested_action="Investigate corrupted negative leave days.",
                        is_data_health_issue=True,
                    )
                )
                continue

            # Only approved leave creates compliance conflicts
            if approval != "approved":
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.NOT_APPLICABLE,
                        severity=RuleSeverity.INFO,
                        evidence={
                            "record_id": leave_id,
                            "approval_state": approval,
                            "message": f"Leave is {approval}, not approved; conflict check skipped.",
                        },
                        policy_version=policy_version,
                        suggested_action=None,
                    )
                )
                continue

            # Iterate through days covered by leave
            cur = lv.start_date
            conflict_found = False

            while cur <= lv.end_date:
                att_on_date = attendance_by_date.get(cur)
                ts_on_date = timesheets_by_date.get(cur)

                has_att_work = att_on_date and (att_on_date.clock_in is not None)
                ts_hours = float(getattr(ts_on_date, "regular_hours", 0) or 0) if ts_on_date else 0.0

                if days_taken >= 1.0:
                    # Full day leave: any attendance or timesheet hours is a conflict
                    if has_att_work or ts_hours > 0:
                        conflict_found = True
                        results.append(
                            RuleResult(
                                rule_id=self.rule_id,
                                rule_version=self.rule_version,
                                status=RuleOutcome.FAIL,
                                severity=RuleSeverity.BLOCKING,
                                evidence={
                                    "record_id": leave_id,
                                    "leave_type": lv.leave_type,
                                    "conflict_date": str(cur),
                                    "days_taken": days_taken,
                                    "attendance_clock_in": str(att_on_date.clock_in) if att_on_date else None,
                                    "timesheet_hours": ts_hours,
                                },
                                policy_version=policy_version,
                                suggested_action=f"Attendance or timesheet hours logged on {cur} during approved full-day {lv.leave_type} leave. Submit timesheet correction or cancel leave.",
                            )
                        )
                else:
                    # Partial / Half-day leave
                    if ts_hours > half_day_limit:
                        conflict_found = True
                        results.append(
                            RuleResult(
                                rule_id=self.rule_id,
                                rule_version=self.rule_version,
                                status=RuleOutcome.FAIL,
                                severity=RuleSeverity.WARNING,
                                evidence={
                                    "record_id": leave_id,
                                    "leave_type": lv.leave_type,
                                    "conflict_date": str(cur),
                                    "days_taken": days_taken,
                                    "timesheet_hours": ts_hours,
                                    "half_day_limit": half_day_limit,
                                },
                                policy_version=policy_version,
                                suggested_action=f"Timesheet hours ({ts_hours}h) exceed half-day leave allowance ({half_day_limit}h) on {cur}.",
                            )
                        )

                # Advance to next day
                import datetime as dt
                cur = cur + dt.timedelta(days=1)

            if not conflict_found:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.PASS,
                        severity=RuleSeverity.INFO,
                        evidence={
                            "record_id": leave_id,
                            "leave_type": lv.leave_type,
                            "start_date": str(lv.start_date),
                            "end_date": str(lv.end_date),
                            "days_taken": days_taken,
                        },
                        policy_version=policy_version,
                    )
                )

        return results
