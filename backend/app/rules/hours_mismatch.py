from datetime import datetime, date
from typing import Dict, Any, List
from collections import defaultdict
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity


class HoursMismatchRule(BaseRule):
    rule_id = "HOURS_MISMATCH"
    rule_version = "1.0"

    def evaluate(self, context: Dict[str, Any], policy_config: Dict[str, Any], policy_version: str) -> List[RuleResult]:
        """
        HOURS_MISMATCH: same employee and day, absolute difference between
        timesheet hours_total and attendance hours_total is greater than 0.5 hours.
        """
        results: List[RuleResult] = []
        timesheets = context.get("timesheets", [])
        attendance = context.get("attendance", [])

        if not timesheets:
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    status=RuleOutcome.NOT_APPLICABLE,
                    severity=RuleSeverity.INFO,
                    evidence={"message": "No timesheet records for this period."},
                    policy_version=policy_version,
                    suggested_action=None,
                )
            )
            return results

        # Group attendance by work_date
        attendance_by_date = defaultdict(list)
        for att in attendance:
            if hasattr(att, "work_date") and att.work_date:
                attendance_by_date[att.work_date].append(att)

        for ts in timesheets:
            work_date = getattr(ts, "work_date", None)
            record_id = getattr(ts, "source_record_id", None) or getattr(ts, "id", "UNKNOWN")
            date_str = str(work_date) if work_date else None

            # Get timesheet hours_total
            if getattr(ts, "hours_total", None) is not None:
                ts_hours = float(ts.hours_total)
            else:
                ts_hours = float(getattr(ts, "regular_hours", 0.0) or 0.0) + float(getattr(ts, "overtime_hours", 0.0) or 0.0)

            # Corrupted negative hours indicates data health issue
            if ts_hours < 0:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": record_id,
                            "work_date": date_str,
                            "timesheet_hours": ts_hours,
                            "message": f"Negative timesheet hours ({ts_hours}h) indicates corrupted upstream data.",
                        },
                        is_data_health_issue=True,
                        policy_version=policy_version,
                        suggested_action="Data health issue: contact payroll support to correct upstream time feed.",
                    )
                )
                continue

            day_punches = attendance_by_date.get(work_date, [])
            if not day_punches:
                continue

            att = day_punches[0]
            if getattr(att, "hours_total", None) is not None:
                att_hours = float(att.hours_total)
            elif att.clock_in and att.clock_out:
                att_hours = (att.clock_out - att.clock_in).total_seconds() / 3600.0
            elif att.clock_in and not att.clock_out:
                # Incomplete punch: cannot reliably compare hours -> UNKNOWN data health issue
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.INFO,
                        evidence={
                            "record_id": record_id,
                            "work_date": date_str,
                            "message": "Incomplete punch prevents hour comparison.",
                        },
                        is_data_health_issue=True,
                        policy_version=policy_version,
                        suggested_action="Resolve missing punch before auditing hours.",
                    )
                )
                continue
            else:
                att_hours = 0.0

            ot_appr = (getattr(att, "overtime_approved", "") or "").strip().upper()
            expected_att_hours = att_hours if (att_hours <= 8.0 or ot_appr == "Y") else 8.0

            diff = abs(ts_hours - expected_att_hours)
            delta_mins = round(diff * 60.0, 1)

            # Tolerance from policy config (default 30 mins / 0.5 hours)
            cfg = policy_config.get("hours_mismatch", {})
            tol_mins = float(cfg.get("tolerance_minutes", 30))
            tol_hours = tol_mins / 60.0

            if diff > tol_hours:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": record_id,
                            "work_date": date_str,
                            "timesheet_hours": ts_hours,
                            "attendance_hours": att_hours,
                            "diff": round(diff, 2),
                            "delta_minutes": delta_mins,
                        },
                        policy_version=policy_version,
                        suggested_action=f"Discrepancy of {round(diff, 2)}h ({delta_mins}m) exceeds {tol_mins}m tolerance on {date_str}.",
                    )
                )
            else:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.PASS,
                        severity=RuleSeverity.INFO,
                        evidence={
                            "record_id": record_id,
                            "work_date": date_str,
                            "diff": round(diff, 2),
                            "delta_minutes": delta_mins,
                        },
                        policy_version=policy_version,
                    )
                )

        return results
