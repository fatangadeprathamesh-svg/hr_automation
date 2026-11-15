from datetime import datetime, date
from typing import Dict, Any, List
from collections import defaultdict
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity


class HoursMismatchRule(BaseRule):
    rule_id = "HOURS_MISMATCH"
    rule_version = "1.0"

    def evaluate(self, context: Dict[str, Any], policy_config: Dict[str, Any], policy_version: str) -> List[RuleResult]:
        results: List[RuleResult] = []
        timesheets = context.get("timesheets", [])
        attendance = context.get("attendance", [])
        leave_records = context.get("leave", [])

        # Policy threshold (default 30 minutes)
        tolerance_minutes = float(policy_config.get("hours_mismatch", {}).get("tolerance_minutes", 30))

        if not timesheets and not attendance:
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    status=RuleOutcome.NOT_APPLICABLE,
                    severity=RuleSeverity.INFO,
                    evidence={"message": "No timesheet or attendance records for this period."},
                    policy_version=policy_version,
                    suggested_action=None,
                )
            )
            return results

        # Group attendance by work_date
        attendance_by_date = defaultdict(list)
        for att in attendance:
            attendance_by_date[att.work_date].append(att)

        # Collect leave dates
        approved_leave_dates = set()
        for lv in leave_records:
            if lv.approval_state == "approved":
                # Add dates in range
                approved_leave_dates.add(lv.start_date)

        for ts in timesheets:
            work_date = ts.work_date
            ts_hours = float(ts.regular_hours or 0.0) + float(ts.overtime_hours or 0.0)
            date_str = str(work_date)

            day_punches = attendance_by_date.get(work_date, [])

            if not day_punches:
                if work_date in approved_leave_dates:
                    results.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            status=RuleOutcome.PASS,
                            severity=RuleSeverity.INFO,
                            evidence={
                                "work_date": date_str,
                                "timesheet_hours": ts_hours,
                                "status": "Covered by approved leave.",
                            },
                            policy_version=policy_version,
                        )
                    )
                else:
                    results.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            status=RuleOutcome.UNKNOWN,
                            severity=RuleSeverity.WARNING,
                            evidence={
                                "work_date": date_str,
                                "timesheet_hours": ts_hours,
                                "attendance_hours": 0.0,
                                "data_health_issue": "MISSING_PUNCH_RECORDS_FOR_TIMESHEET",
                            },
                            policy_version=policy_version,
                            suggested_action="Verify if attendance punches are missing or unimported.",
                            is_data_health_issue=True,
                        )
                    )
                continue

            # Check if any punch on that day has missing clock_in or clock_out
            has_incomplete_punch = any(not p.clock_in or not p.clock_out for p in day_punches)
            if has_incomplete_punch:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "work_date": date_str,
                            "timesheet_hours": ts_hours,
                            "data_health_issue": "INCOMPLETE_PUNCHES_ON_DATE",
                            "message": "Cannot compare hours because attendance punches for this date are incomplete.",
                        },
                        policy_version=policy_version,
                        suggested_action="Resolve missing punch first before re-evaluating hours mismatch.",
                        is_data_health_issue=True,
                    )
                )
                continue

            # Calculate total punch hours for the day
            total_punch_seconds = sum(
                (p.clock_out - p.clock_in).total_seconds() for p in day_punches if p.clock_in and p.clock_out
            )
            punch_hours = total_punch_seconds / 3600.0

            delta_minutes = abs(ts_hours - punch_hours) * 60.0

            if delta_minutes <= tolerance_minutes:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.PASS,
                        severity=RuleSeverity.INFO,
                        evidence={
                            "record_id": ts.source_record_id,
                            "entity_id": ts.id,
                            "work_date": date_str,
                            "timesheet_hours": ts_hours,
                            "punch_hours": round(punch_hours, 2),
                            "delta_minutes": round(delta_minutes, 1),
                            "tolerance_minutes": tolerance_minutes,
                        },
                        policy_version=policy_version,
                    )
                )
            else:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": ts.source_record_id,
                            "entity_id": ts.id,
                            "work_date": date_str,
                            "timesheet_hours": ts_hours,
                            "punch_hours": round(punch_hours, 2),
                            "delta_minutes": round(delta_minutes, 1),
                            "tolerance_minutes": tolerance_minutes,
                        },
                        policy_version=policy_version,
                        suggested_action=f"Discrepancy of {round(delta_minutes, 1)}m exceeds {tolerance_minutes}m tolerance. Adjust timesheet or request punch correction.",
                    )
                )

        return results
