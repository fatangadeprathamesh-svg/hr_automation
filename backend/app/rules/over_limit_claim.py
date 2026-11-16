from typing import Dict, Any, List
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity

DEFAULT_CATEGORY_LIMITS = {
    "meals": 75.0,
    "travel": 500.0,
    "supplies": 200.0,
    "training": 1000.0,
    "lodging": 350.0,
    "transport": 100.0,
}
DEFAULT_FALLBACK_LIMIT = 300.0


class OverLimitClaimRule(BaseRule):
    rule_id = "OVER_LIMIT_CLAIM"
    rule_version = "1.0"

    def evaluate(
        self,
        context: Dict[str, Any],
        policy_config: Dict[str, Any],
        policy_version: str,
    ) -> List[RuleResult]:
        results: List[RuleResult] = []
        claims = context.get("expense_claims", [])

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

        config = policy_config.get("over_limit_claim", {})
        category_limits = config.get("category_limits", DEFAULT_CATEGORY_LIMITS)
        fallback_limit = float(config.get("default_limit", DEFAULT_FALLBACK_LIMIT))

        # Normalize dictionary keys for robust matching
        normalized_limits = {k.lower().strip(): float(v) for k, v in category_limits.items()}

        for claim in claims:
            claim_id = getattr(claim, "source_record_id", None) or getattr(claim, "id", "UNKNOWN")
            amount = getattr(claim, "amount", None)
            category = getattr(claim, "category", "") or "general"
            currency = getattr(claim, "currency", "USD")

            if amount is None or float(amount) < 0:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": claim_id,
                            "error": "INVALID_OR_NEGATIVE_AMOUNT",
                            "amount": float(amount) if amount is not None else None,
                        },
                        policy_version=policy_version,
                        suggested_action="Investigate corrupted negative or null expense claim amount.",
                        is_data_health_issue=True,
                    )
                )
                continue

            amt = float(amount)
            limit = normalized_limits.get(category.lower().strip(), fallback_limit)

            if amt > limit:
                excess = round(amt - limit, 2)
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": claim_id,
                            "entity_id": getattr(claim, "id", None),
                            "amount": amt,
                            "category": category,
                            "policy_limit": limit,
                            "excess_amount": excess,
                            "currency": currency,
                        },
                        policy_version=policy_version,
                        suggested_action=(
                            f"Claim of {currency} {amt:.2f} exceeds {category} policy limit of {currency} {limit:.2f} "
                            f"(excess {currency} {excess:.2f}). Submit manager-approved exception or adjust claim."
                        ),
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
                            "record_id": claim_id,
                            "amount": amt,
                            "category": category,
                            "policy_limit": limit,
                            "currency": currency,
                        },
                        policy_version=policy_version,
                    )
                )

        return results
