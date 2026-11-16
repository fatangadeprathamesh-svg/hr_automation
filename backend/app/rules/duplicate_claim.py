from decimal import Decimal
from typing import Dict, Any, List, Set
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity


class DuplicateClaimRule(BaseRule):
    rule_id = "DUPLICATE_CLAIM"
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

        config = policy_config.get("duplicate_claim", {})
        match_receipt_ref = config.get("match_receipt_reference", True)
        match_date_amount_merchant = config.get("match_date_amount_merchant", True)

        valid_claims = []
        for claim in claims:
            claim_id = getattr(claim, "source_record_id", None) or getattr(claim, "id", "UNKNOWN")
            amount = getattr(claim, "amount", None)
            claim_date = getattr(claim, "claim_date", None)

            # Data health checks
            if claim_date is None:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": claim_id,
                            "error": "MISSING_CLAIM_DATE",
                        },
                        policy_version=policy_version,
                        suggested_action="Investigate claim with missing claim date.",
                        is_data_health_issue=True,
                    )
                )
                continue

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

            valid_claims.append(claim)

        # Detect duplicates among valid claims
        # A claim is duplicate if another claim shares receipt_reference (non-empty)
        # OR shares (claim_date, amount, category/merchant)
        duplicate_ids: Dict[str, List[str]] = {}
        duplicate_reasons: Dict[str, List[str]] = {}

        for i, c1 in enumerate(valid_claims):
            id1 = getattr(c1, "source_record_id", None) or getattr(c1, "id", str(i))
            amt1 = float(c1.amount)
            date1 = c1.claim_date
            cat1 = getattr(c1, "category", "") or ""
            merch1 = (getattr(c1, "merchant_name", "") or "").strip().lower()
            rec1 = (getattr(c1, "receipt_reference", "") or "").strip()

            for j, c2 in enumerate(valid_claims):
                if i == j:
                    continue
                id2 = getattr(c2, "source_record_id", None) or getattr(c2, "id", str(j))
                amt2 = float(c2.amount)
                date2 = c2.claim_date
                cat2 = getattr(c2, "category", "") or ""
                merch2 = (getattr(c2, "merchant_name", "") or "").strip().lower()
                rec2 = (getattr(c2, "receipt_reference", "") or "").strip()

                is_dup = False
                reason = ""

                # Check duplicate receipt reference
                if match_receipt_ref and rec1 and rec2 and rec1.lower() == rec2.lower():
                    is_dup = True
                    reason = f"Duplicate receipt reference '{rec1}' matches claim {id2}"

                # Check duplicate date + amount + (merchant or category)
                if match_date_amount_merchant and not is_dup:
                    if date1 == date2 and amt1 == amt2:
                        if merch1 and merch2 and merch1 == merch2:
                            is_dup = True
                            reason = f"Duplicate claim on {date1} for {amt1:.2f} at '{merch1}' matches claim {id2}"
                        elif cat1 and cat2 and cat1.lower() == cat2.lower():
                            is_dup = True
                            reason = f"Duplicate claim on {date1} for {amt1:.2f} in category '{cat1}' matches claim {id2}"

                if is_dup:
                    duplicate_ids.setdefault(id1, []).append(id2)
                    duplicate_reasons.setdefault(id1, []).append(reason)

        for claim in valid_claims:
            claim_id = getattr(claim, "source_record_id", None) or getattr(claim, "id", "UNKNOWN")
            if claim_id in duplicate_ids:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": claim_id,
                            "entity_id": getattr(claim, "id", None),
                            "amount": float(claim.amount),
                            "currency": getattr(claim, "currency", "USD"),
                            "claim_date": str(claim.claim_date),
                            "category": claim.category,
                            "merchant_name": getattr(claim, "merchant_name", None),
                            "receipt_reference": getattr(claim, "receipt_reference", None),
                            "duplicate_with": duplicate_ids[claim_id],
                            "reasons": duplicate_reasons[claim_id],
                        },
                        policy_version=policy_version,
                        suggested_action=f"Duplicate claim detected with {duplicate_ids[claim_id]}. Withdraw duplicate or submit correction with distinct documentation.",
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
                            "amount": float(claim.amount),
                            "claim_date": str(claim.claim_date),
                            "category": claim.category,
                        },
                        policy_version=policy_version,
                    )
                )

        return results
