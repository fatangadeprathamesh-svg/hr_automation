from typing import Dict, Any, List
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity

PENDING_STATES = {"pending", "pending_review", "submitted", "in_review"}
FINAL_STATES = {"approved", "rejected", "withdrawn", "cancelled", "waived"}


class PendingApprovalsRule(BaseRule):
    rule_id = "PENDING_APPROVALS"
    rule_version = "1.0"

    def evaluate(
        self,
        context: Dict[str, Any],
        policy_config: Dict[str, Any],
        policy_version: str,
    ) -> List[RuleResult]:
        results: List[RuleResult] = []

        timesheets = context.get("timesheets", [])
        expenses = context.get("expense_claims", [])
        leaves = context.get("leave", [])
        corrections = context.get("corrections", [])

        total_records = len(timesheets) + len(expenses) + len(leaves) + len(corrections)
        if total_records == 0:
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    status=RuleOutcome.NOT_APPLICABLE,
                    severity=RuleSeverity.INFO,
                    evidence={"message": "No items subject to manager approval found for this period."},
                    policy_version=policy_version,
                    suggested_action=None,
                )
            )
            return results

        # Process each category
        items_to_check = [
            ("timesheet", timesheets, "approval_state"),
            ("expense_claim", expenses, "approval_state"),
            ("leave", leaves, "approval_state"),
            ("correction", corrections, "status"),
        ]

        pending_items_count = 0
        final_items_count = 0

        for item_type, records, state_field in items_to_check:
            for rec in records:
                record_id = getattr(rec, "source_record_id", None) or getattr(rec, "id", None) or getattr(rec, "correction_id", "UNKNOWN")
                raw_state = getattr(rec, state_field, None)

                # Data health check for missing state
                if raw_state is None or not str(raw_state).strip():
                    results.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            status=RuleOutcome.UNKNOWN,
                            severity=RuleSeverity.WARNING,
                            evidence={
                                "record_id": record_id,
                                "entity_type": item_type,
                                "error": "MISSING_APPROVAL_STATE",
                            },
                            policy_version=policy_version,
                            suggested_action=f"Investigate {item_type} record with undefined approval state.",
                            is_data_health_issue=True,
                        )
                    )
                    continue

                state_val = str(raw_state).strip().lower()

                if state_val in PENDING_STATES:
                    pending_items_count += 1
                    results.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            status=RuleOutcome.FAIL,
                            severity=RuleSeverity.BLOCKING,
                            evidence={
                                "record_id": record_id,
                                "entity_type": item_type,
                                "entity_id": getattr(rec, "id", None) or getattr(rec, "correction_id", None),
                                "status": state_val,
                            },
                            policy_version=policy_version,
                            suggested_action=(
                                f"Awaiting manager decision on {item_type} ({record_id}). "
                                f"All pending approvals must be decided before month-end submission."
                            ),
                        )
                    )
                else:
                    final_items_count += 1

        # If no pending items were found and no health errors were emitted, emit PASS
        if pending_items_count == 0 and len(results) == 0:
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    status=RuleOutcome.PASS,
                    severity=RuleSeverity.INFO,
                    evidence={
                        "message": "All timesheets, expenses, leave, and corrections have been resolved.",
                        "decided_records_count": final_items_count,
                    },
                    policy_version=policy_version,
                )
            )

        return results
