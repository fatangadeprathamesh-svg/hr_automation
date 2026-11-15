from typing import Dict, Any, List
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity


class MissingReceiptRule(BaseRule):
    rule_id = "MISSING_RECEIPT"
    rule_version = "1.0"

    def evaluate(self, context: Dict[str, Any], policy_config: Dict[str, Any], policy_version: str) -> List[RuleResult]:
        results: List[RuleResult] = []
        claims = context.get("expense_claims", [])

        # Policy threshold (default $25.00)
        threshold = float(policy_config.get("missing_receipt", {}).get("receipt_required_threshold", 25.0))

        if not claims:
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    status=RuleOutcome.NOT_APPLICABLE,
                    severity=RuleSeverity.INFO,
                    evidence={"message": "No expense claims found for this period."},
                    policy_version=policy_version,
                    suggested_action=None,
                )
            )
            return results

        for claim in claims:
            amount = float(claim.amount or 0.0)
            receipt_ref = claim.receipt_reference
            claim_id = claim.source_record_id

            if amount < 0:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": claim_id,
                            "amount": amount,
                            "data_health_issue": "NEGATIVE_EXPENSE_AMOUNT",
                        },
                        policy_version=policy_version,
                        suggested_action="Investigate corrupted negative expense claim.",
                        is_data_health_issue=True,
                    )
                )
                continue

            if amount >= threshold:
                if receipt_ref and str(receipt_ref).strip():
                    results.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            status=RuleOutcome.PASS,
                            severity=RuleSeverity.INFO,
                            evidence={
                                "record_id": claim_id,
                                "amount": amount,
                                "currency": claim.currency,
                                "category": claim.category,
                                "receipt_reference": str(receipt_ref),
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
                                "record_id": claim_id,
                                "entity_id": claim.id,
                                "amount": amount,
                                "currency": claim.currency,
                                "category": claim.category,
                                "threshold": threshold,
                                "missing": "receipt_reference",
                            },
                            policy_version=policy_version,
                            suggested_action=f"Claim of {claim.currency} {amount:.2f} requires a receipt (threshold: {threshold:.2f}). Upload receipt document.",
                        )
                    )
            else:
                # Under receipt threshold
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.NOT_APPLICABLE,
                        severity=RuleSeverity.INFO,
                        evidence={
                            "record_id": claim_id,
                            "amount": amount,
                            "threshold": threshold,
                            "message": f"Receipt not required for claims under {threshold:.2f}.",
                        },
                        policy_version=policy_version,
                    )
                )

        return results
