from typing import Dict, Any, List
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity


class PendingApprovalsRule(BaseRule):
    rule_id = "PENDING_APPROVAL"
    rule_version = "1.0"

    def evaluate(
        self,
        context: Dict[str, Any],
        policy_config: Dict[str, Any],
        policy_version: str,
    ) -> List[RuleResult]:
        """
        PENDING_APPROVAL:
        1. Timesheet with status Unapproved or pending.
        2. Corrections in pending_review.
        3. Expense claims in pending.
        4. Missing approval state -> UNKNOWN data health issue.
        """
        results: List[RuleResult] = []
        timesheets = context.get("timesheets", [])
        corrections = context.get("corrections", [])
        expense_claims = context.get("expense_claims", [])

        if not timesheets and not corrections and not expense_claims:
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    status=RuleOutcome.NOT_APPLICABLE,
                    severity=RuleSeverity.INFO,
                    evidence={"message": "No pending approval records found for this period."},
                    policy_version=policy_version,
                    suggested_action=None,
                )
            )
            return results

        has_flag = False
        decided_count = 0

        for ts in timesheets:
            record_id = getattr(ts, "source_record_id", None) or getattr(ts, "id", "UNKNOWN")
            raw_status = getattr(ts, "status", None)
            raw_appr = getattr(ts, "approval_state", None)

            # Data health check: completely missing approval state
            if raw_status is None and raw_appr is None:
                has_flag = True
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": record_id,
                            "message": "Missing approval state on timesheet record.",
                        },
                        is_data_health_issue=True,
                        policy_version=policy_version,
                        suggested_action="Data health issue: timesheet record lacks approval status.",
                    )
                )
                continue

            status_val = (raw_status or raw_appr or "").strip()

            if status_val.lower() in ("unapproved", "pending", "pending_review"):
                has_flag = True
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": record_id,
                            "work_date": str(ts.work_date) if hasattr(ts, "work_date") else None,
                            "status": status_val,
                            "type": "timesheet",
                        },
                        policy_version=policy_version,
                        suggested_action=f"Timesheet {record_id} is Unapproved; manager sign-off required.",
                    )
                )
            else:
                decided_count += 1

        for corr in corrections:
            corr_id = getattr(corr, "correction_id", None) or getattr(corr, "id", "UNKNOWN")
            c_status = (getattr(corr, "status", "") or "").strip()
            if c_status.lower() in ("pending", "pending_review"):
                has_flag = True
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": corr_id,
                            "status": c_status,
                            "type": "correction",
                        },
                        policy_version=policy_version,
                        suggested_action=f"Correction {corr_id} is pending review.",
                    )
                )
            elif c_status:
                decided_count += 1

        for exp in expense_claims:
            exp_id = getattr(exp, "source_record_id", None) or getattr(exp, "id", "UNKNOWN")
            e_status = (getattr(exp, "approval_state", "") or "").strip()
            if e_status.lower() in ("pending", "pending_review", "unapproved"):
                has_flag = True
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": exp_id,
                            "status": e_status,
                            "type": "expense",
                        },
                        policy_version=policy_version,
                        suggested_action=f"Expense {exp_id} is pending approval.",
                    )
                )
            elif e_status:
                decided_count += 1

        if not has_flag:
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    status=RuleOutcome.PASS,
                    severity=RuleSeverity.INFO,
                    evidence={
                        "message": "All timesheets, expenses, and corrections are approved.",
                        "decided_records_count": decided_count,
                    },
                    policy_version=policy_version,
                )
            )

        return results
