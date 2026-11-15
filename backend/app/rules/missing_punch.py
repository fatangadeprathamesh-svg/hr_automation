from datetime import datetime
from typing import Dict, Any, List
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity


class MissingPunchRule(BaseRule):
    rule_id = "MISSING_PUNCH"
    rule_version = "1.0"

    def evaluate(self, context: Dict[str, Any], policy_config: Dict[str, Any], policy_version: str) -> List[RuleResult]:
        results: List[RuleResult] = []
        attendance_records = context.get("attendance", [])
        is_feed_complete = context.get("attendance_feed_complete", True)

        # Non-negotiable Rule 3: Missing/incomplete feed data is "unknown", NEVER employee fault
        if not is_feed_complete:
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    status=RuleOutcome.UNKNOWN,
                    severity=RuleSeverity.WARNING,
                    evidence={
                        "data_health_issue": "INCOMPLETE_FEED",
                        "message": "Attendance feed for this period is marked incomplete or truncated. This is a system feed issue, not employee fault."
                    },
                    policy_version=policy_version,
                    suggested_action="Escalate to HR IT/Operations to re-sync complete attendance source records.",
                    is_data_health_issue=True,
                )
            )
            return results

        if not attendance_records:
            # No attendance logs recorded
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    status=RuleOutcome.NOT_APPLICABLE,
                    severity=RuleSeverity.INFO,
                    evidence={"message": "No attendance records found for this period."},
                    policy_version=policy_version,
                    suggested_action=None,
                )
            )
            return results

        for att in attendance_records:
            clock_in = att.clock_in
            clock_out = att.clock_out
            work_date_str = str(att.work_date)
            record_id = att.source_record_id

            if clock_in and not clock_out:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": record_id,
                            "entity_id": att.id,
                            "work_date": work_date_str,
                            "missing": "clock_out",
                            "clock_in": clock_in.isoformat(),
                        },
                        policy_version=policy_version,
                        suggested_action="Request manager-reviewed clock-out correction.",
                    )
                )
            elif clock_out and not clock_in:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": record_id,
                            "entity_id": att.id,
                            "work_date": work_date_str,
                            "missing": "clock_in",
                            "clock_out": clock_out.isoformat(),
                        },
                        policy_version=policy_version,
                        suggested_action="Request manager-reviewed clock-in correction.",
                    )
                )
            elif not clock_in and not clock_out:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": record_id,
                            "work_date": work_date_str,
                            "missing": "both_punches",
                        },
                        policy_version=policy_version,
                        suggested_action="Investigate hardware/biometric terminal feed gap.",
                        is_data_health_issue=True,
                    )
                )
            else:
                # Both present
                duration_hrs = round((clock_out - clock_in).total_seconds() / 3600.0, 2)
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.PASS,
                        severity=RuleSeverity.INFO,
                        evidence={
                            "record_id": record_id,
                            "work_date": work_date_str,
                            "duration_hours": duration_hrs,
                        },
                        policy_version=policy_version,
                        suggested_action=None,
                    )
                )

        return results
