from typing import Dict, Any, List
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity


class MissingReceiptRule(BaseRule):
    rule_id = "MISSING_RECEIPT"
    rule_version = "1.0"

    def evaluate(self, context: Dict[str, Any], policy_config: Dict[str, Any], policy_version: str) -> List[RuleResult]:
        """
        MISSING_RECEIPT: expense amount >= threshold (default 25.0) and receipt_attached = N or missing receipt.
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

        cfg = policy_config.get("missing_receipt", {})
        threshold = float(cfg.get("receipt_required_threshold", 25.0))

        for claim in claims:
            amount = float(claim.amount or 0.0)
            claim_id = getattr(claim, "source_record_id", None) or getattr(claim, "id", "UNKNOWN")
            receipt_attached = (getattr(claim, "receipt_attached", "") or "").strip().upper()
            receipt_ref = (getattr(claim, "receipt_reference", "") or "").strip()

            # Corrupted negative amount indicates data health issue
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
                            "message": f"Negative claim amount (${amount:.2f}) indicates corrupted upstream data.",
                        },
                        is_data_health_issue=True,
                        policy_version=policy_version,
                        suggested_action="Data health issue: upstream expense system record is corrupted.",
                    )
                )
                continue

            has_receipt = (receipt_attached in ("Y", "YES", "1", "TRUE")) or (bool(receipt_ref) and receipt_attached not in ("N", "NO", "0", "FALSE"))

            if amount >= threshold:
                if not has_receipt or receipt_attached in ("N", "NO", "0", "FALSE"):
                    results.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            status=RuleOutcome.FAIL,
                            severity=RuleSeverity.BLOCKING,
                            evidence={
                                "record_id": claim_id,
                                "amount": amount,
                                "currency": getattr(claim, "currency", "USD"),
                                "category": getattr(claim, "category", ""),
                                "receipt_attached": receipt_attached or "N",
                            },
                            policy_version=policy_version,
                            suggested_action=f"Upload receipt document: Claim of USD {amount:.2f} requires a receipt (threshold: {threshold:.2f}).",
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
                                "receipt_attached": receipt_attached,
                            },
                            policy_version=policy_version,
                        )
                    )
            else:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.NOT_APPLICABLE,
                        severity=RuleSeverity.INFO,
                        evidence={
                            "record_id": claim_id,
                            "amount": amount,
                            "message": f"Amount {amount:.2f} below receipt threshold {threshold:.2f}.",
                        },
                        policy_version=policy_version,
                    )
                )

        return results
