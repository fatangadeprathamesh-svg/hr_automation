from typing import Dict, Any, List
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity


class UnapprovedOvertimeRule(BaseRule):
    rule_id = "UNAPPROVED_OVERTIME"
    rule_version = "1.0"

    def evaluate(
        self,
        context: Dict[str, Any],
        policy_config: Dict[str, Any],
        policy_version: str,
    ) -> List[RuleResult]:
        results: List[RuleResult] = []
        timesheets = context.get("timesheets", [])

        if not timesheets:
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    status=RuleOutcome.NOT_APPLICABLE,
                    severity=RuleSeverity.INFO,
                    evidence={"message": "No timesheet records found for this period."},
                    policy_version=policy_version,
                    suggested_action=None,
                )
            )
            return results

        config = policy_config.get("unapproved_overtime", {})
        standard_daily_hours = float(config.get("standard_daily_hours", 8.0))
        blocking_threshold = float(config.get("overtime_blocking_threshold", 12.0))

        for ts in timesheets:
            record_id = getattr(ts, "source_record_id", None) or getattr(ts, "id", "UNKNOWN")
            work_date = getattr(ts, "work_date", None)
            approval = getattr(ts, "approval_state", "pending")

            # Data health checks
            if work_date is None:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": record_id,
                            "error": "MISSING_WORK_DATE",
                        },
                        policy_version=policy_version,
                        suggested_action="Investigate timesheet with missing work date.",
                        is_data_health_issue=True,
                    )
                )
                continue

            reg_raw = getattr(ts, "regular_hours", 0.0)
            ot_raw = getattr(ts, "overtime_hours", 0.0)

            if reg_raw is None or ot_raw is None:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": record_id,
                            "error": "NULL_HOURS_VALUE",
                            "work_date": str(work_date),
                        },
                        policy_version=policy_version,
                        suggested_action="Investigate timesheet with null regular or overtime hours.",
                        is_data_health_issue=True,
                    )
                )
                continue

            reg = float(reg_raw)
            ot = float(ot_raw)

            if reg < 0 or ot < 0:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": record_id,
                            "error": "NEGATIVE_HOURS",
                            "work_date": str(work_date),
                            "regular_hours": reg,
                            "overtime_hours": ot,
                        },
                        policy_version=policy_version,
                        suggested_action="Investigate corrupted negative timesheet hours.",
                        is_data_health_issue=True,
                    )
                )
                continue

            total_hours = round(reg + ot, 2)

            if total_hours > 24.0:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": record_id,
                            "error": "HOURS_EXCEED_24_IN_A_DAY",
                            "work_date": str(work_date),
                            "total_hours": total_hours,
                        },
                        policy_version=policy_version,
                        suggested_action="Investigate corrupted timesheet exceeding 24 hours in a single calendar day.",
                        is_data_health_issue=True,
                    )
                )
                continue

            # Case 1: Extreme hours exceeding blocking threshold (e.g. > 12h)
            if total_hours > blocking_threshold:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": record_id,
                            "entity_id": getattr(ts, "id", None),
                            "work_date": str(work_date),
                            "regular_hours": reg,
                            "overtime_hours": ot,
                            "total_hours": total_hours,
                            "blocking_threshold": blocking_threshold,
                            "approval_state": approval,
                        },
                        policy_version=policy_version,
                        suggested_action=(
                            f"Total hours ({total_hours:.1f}h) on {work_date} exceed excessive work threshold "
                            f"({blocking_threshold:.1f}h). Mandatory manager and HR compliance sign-off required."
                        ),
                    )
                )
            # Case 2: Overtime logged or total > standard daily hours without approved state
            elif (ot > 0 or total_hours > standard_daily_hours) and approval != "approved":
                unapproved_ot = round(ot if ot > 0 else (total_hours - standard_daily_hours), 2)
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": record_id,
                            "entity_id": getattr(ts, "id", None),
                            "work_date": str(work_date),
                            "regular_hours": reg,
                            "overtime_hours": ot,
                            "total_hours": total_hours,
                            "unapproved_overtime_hours": unapproved_ot,
                            "approval_state": approval,
                        },
                        policy_version=policy_version,
                        suggested_action=(
                            f"Overtime of {unapproved_ot:.1f}h on {work_date} is currently '{approval}'. "
                            f"Obtain manager overtime approval before month-end signoff."
                        ),
                    )
                )
            # Case 3: Compliant regular hours or approved overtime <= blocking threshold
            else:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.PASS,
                        severity=RuleSeverity.INFO,
                        evidence={
                            "record_id": record_id,
                            "work_date": str(work_date),
                            "regular_hours": reg,
                            "overtime_hours": ot,
                            "total_hours": total_hours,
                            "approval_state": approval,
                        },
                        policy_version=policy_version,
                    )
                )

        return results
