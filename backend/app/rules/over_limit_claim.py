from typing import Dict, Any, List
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity

DEFAULT_CATEGORY_LIMITS = {
    "meals": 60.0,
    "travel": 300.0,
    "software": 150.0,
    "training": 400.0,
    "fuel": 80.0,
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
        """
        OVER_LIMIT_CLAIM: amount above the per-category policy limit from the policy table.
        """
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

        normalized_limits = {k.lower().strip(): float(v) for k, v in category_limits.items()}

        for claim in claims:
            claim_id = getattr(claim, "source_record_id", None) or getattr(claim, "id", "UNKNOWN")
            amount = float(getattr(claim, "amount", 0.0) or 0.0)
            category = (getattr(claim, "category", "") or "general").strip()
            currency = getattr(claim, "currency", "USD")

            limit = normalized_limits.get(category.lower().strip(), fallback_limit)

            if amount > limit:
                excess = round(amount - limit, 2)
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": claim_id,
                            "amount": amount,
                            "category": category,
                            "policy_limit": limit,
                            "excess_amount": excess,
                            "currency": currency,
                        },
                        policy_version=policy_version,
                        suggested_action=(
                            f"Claim of {currency} {amount:.2f} exceeds {category} limit of {currency} {limit:.2f} "
                            f"(excess {currency} {excess:.2f})."
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
                            "amount": amount,
                            "category": category,
                            "policy_limit": limit,
                        },
                        policy_version=policy_version,
                    )
                )

        return results
