from typing import Dict, Any, List
from collections import defaultdict
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
        """
        DUPLICATE_CLAIM:
        1. Identical receipt_reference across multiple claims.
        2. Same employee, event_date, expense_category, and amount.
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

        # Group claims by receipt_reference (if present)
        receipt_groups = defaultdict(list)
        # Group claims by (claim_date, category.lower(), amount)
        content_groups = defaultdict(list)

        for claim in claims:
            c_date = getattr(claim, "claim_date", None)
            c_amt = round(float(getattr(claim, "amount", 0.0) or 0.0), 2)
            c_cat = (getattr(claim, "category", "") or "").strip().lower()
            rec_ref = (getattr(claim, "receipt_reference", "") or "").strip()

            content_key = (str(c_date), c_cat, c_amt)
            content_groups[content_key].append(claim)

            if rec_ref:
                receipt_groups[rec_ref].append(claim)

        has_duplicate = False

        for claim in claims:
            claim_id = getattr(claim, "source_record_id", None) or getattr(claim, "id", "UNKNOWN")
            c_date = getattr(claim, "claim_date", None)
            try:
                c_amt = float(getattr(claim, "amount", 0.0) or 0.0)
            except (ValueError, TypeError):
                c_amt = -1.0

            # Data health check: negative amount or missing date
            if c_amt < 0 or c_date is None:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": claim_id,
                            "claim_date": str(c_date) if c_date else None,
                            "amount": c_amt,
                            "message": "Corrupted expense claim: negative amount or missing claim date.",
                        },
                        is_data_health_issue=True,
                        policy_version=policy_version,
                        suggested_action="Data health issue: upstream expense system record is corrupted.",
                    )
                )
                continue

            c_amt = round(c_amt, 2)
            c_cat = (getattr(claim, "category", "") or "").strip().lower()
            rec_ref = (getattr(claim, "receipt_reference", "") or "").strip()
            content_key = (str(c_date), c_cat, c_amt)

            is_dup = False
            dup_reason = ""
            matched_ids = []

            # Check receipt reference collision (flag subsequent duplicates after original)
            if rec_ref and len(receipt_groups[rec_ref]) > 1:
                if claim != receipt_groups[rec_ref][0]:
                    is_dup = True
                    matched_ids = [getattr(c, "source_record_id", c.id) for c in receipt_groups[rec_ref] if getattr(c, "source_record_id", c.id) != claim_id]
                    dup_reason = f"Duplicate receipt reference '{rec_ref}' attached to multiple claims: {matched_ids}."
            # Check content collision (flag subsequent duplicates after original)
            elif len(content_groups[content_key]) > 1:
                if claim != content_groups[content_key][0]:
                    is_dup = True
                    matched_ids = [getattr(c, "source_record_id", c.id) for c in content_groups[content_key] if getattr(c, "source_record_id", c.id) != claim_id]
                    dup_reason = f"Identical claim details (date: {c_date}, category: {c_cat}, amount: {c_amt}) matched claim {matched_ids}."

            if is_dup:
                has_duplicate = True
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": claim_id,
                            "claim_date": str(c_date) if c_date else None,
                            "amount": c_amt,
                            "category": c_cat,
                            "receipt_reference": rec_ref,
                            "duplicate_with": matched_ids,
                            "reason": dup_reason,
                        },
                        policy_version=policy_version,
                        suggested_action=f"Resolve duplicate expense claim: {dup_reason}",
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
                            "claim_date": str(c_date) if c_date else None,
                            "amount": c_amt,
                        },
                        policy_version=policy_version,
                    )
                )

        return results
