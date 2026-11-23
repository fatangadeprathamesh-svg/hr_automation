from datetime import date, datetime
from typing import Dict, Any, List
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity

MANDATORY_EXPIRY_TYPES = {"passport", "visa", "work_permit", "driver_license"}


class ExpiringDocumentsRule(BaseRule):
    rule_id = "EXPIRING_DOCUMENTS"
    rule_version = "1.0"

    def evaluate(
        self,
        context: Dict[str, Any],
        policy_config: Dict[str, Any],
        policy_version: str,
    ) -> List[RuleResult]:
        results: List[RuleResult] = []
        documents = context.get("documents", [])

        if not documents:
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    status=RuleOutcome.UNKNOWN,
                    severity=RuleSeverity.INFO,
                    evidence={
                        "message": "No compliance documents on file in import / not enough data.",
                        "data_health_issue": "NO_DOCUMENT_DATA",
                    },
                    policy_version=policy_version,
                    suggested_action="Upload statutory identity or compliance documents.",
                    is_data_health_issue=True,
                )
            )
            return results

        config = policy_config.get("expiring_documents", {})
        warning_days = int(config.get("warning_days", 60))
        blocking_days = int(config.get("blocking_days", 30))

        # Determine reference date: context override -> period end -> current date
        ref_date = context.get("reference_date")
        if not ref_date:
            period = context.get("period")
            if period and isinstance(period, str) and "-" in period:
                try:
                    parts = period.split("-")
                    year, month = int(parts[0]), int(parts[1])
                    if month == 12:
                        ref_date = date(year, 12, 31)
                    else:
                        import calendar
                        _, last_day = calendar.monthrange(year, month)
                        ref_date = date(year, month, last_day)
                except Exception:
                    ref_date = date.today()
            else:
                ref_date = date.today()

        for doc in documents:
            doc_id = getattr(doc, "source_record_id", None) or getattr(doc, "id", "UNKNOWN")
            doc_type = getattr(doc, "document_type", "unknown")
            doc_ref = getattr(doc, "document_reference", None)
            issue_d = getattr(doc, "issue_date", None)
            expiry_d = getattr(doc, "expiry_date", None)

            # Data health checks
            if not doc_ref or not str(doc_ref).strip():
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": doc_id,
                            "document_type": doc_type,
                            "error": "MISSING_DOCUMENT_REFERENCE",
                        },
                        policy_version=policy_version,
                        suggested_action="Investigate document record missing document reference identifier.",
                        is_data_health_issue=True,
                    )
                )
                continue

            if expiry_d is None:
                # If document is of a type that requires expiry date
                if doc_type.lower() in MANDATORY_EXPIRY_TYPES:
                    results.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            status=RuleOutcome.UNKNOWN,
                            severity=RuleSeverity.WARNING,
                            evidence={
                                "record_id": doc_id,
                                "document_type": doc_type,
                                "error": "MISSING_MANDATORY_EXPIRY_DATE",
                            },
                            policy_version=policy_version,
                            suggested_action=f"Compliance document {doc_type} ({doc_ref}) is missing its expiration date.",
                            is_data_health_issue=True,
                        )
                    )
                else:
                    # Non-expiring document (e.g. diploma/certificate)
                    results.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            status=RuleOutcome.NOT_APPLICABLE,
                            severity=RuleSeverity.INFO,
                            evidence={
                                "record_id": doc_id,
                                "document_type": doc_type,
                                "message": f"{doc_type} does not carry an expiration requirement.",
                            },
                            policy_version=policy_version,
                        )
                    )
                continue

            if issue_d and issue_d > expiry_d:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.UNKNOWN,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": doc_id,
                            "document_type": doc_type,
                            "error": "ISSUE_DATE_AFTER_EXPIRY_DATE",
                            "issue_date": str(issue_d),
                            "expiry_date": str(expiry_d),
                        },
                        policy_version=policy_version,
                        suggested_action=f"Correct corrupted document record where issue date ({issue_d}) is after expiry date ({expiry_d}).",
                        is_data_health_issue=True,
                    )
                )
                continue

            # Calculate days remaining
            days_remaining = (expiry_d - ref_date).days

            if days_remaining < 0:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": doc_id,
                            "entity_id": getattr(doc, "id", None),
                            "document_type": doc_type,
                            "document_reference": doc_ref,
                            "expiry_date": str(expiry_d),
                            "reference_date": str(ref_date),
                            "days_expired": abs(days_remaining),
                        },
                        policy_version=policy_version,
                        suggested_action=(
                            f"{doc_type.replace('_', ' ').title()} expired {abs(days_remaining)} days ago on {expiry_d}. "
                            f"Upload a valid renewal document before month-end submission."
                        ),
                    )
                )
            elif days_remaining <= blocking_days:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.BLOCKING,
                        evidence={
                            "record_id": doc_id,
                            "entity_id": getattr(doc, "id", None),
                            "document_type": doc_type,
                            "document_reference": doc_ref,
                            "expiry_date": str(expiry_d),
                            "reference_date": str(ref_date),
                            "days_remaining": days_remaining,
                            "blocking_threshold": blocking_days,
                        },
                        policy_version=policy_version,
                        suggested_action=(
                            f"{doc_type.replace('_', ' ').title()} expires in {days_remaining} days on {expiry_d} "
                            f"(critical threshold {blocking_days} days). Renew document immediately."
                        ),
                    )
                )
            elif days_remaining <= warning_days:
                results.append(
                    RuleResult(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        status=RuleOutcome.FAIL,
                        severity=RuleSeverity.WARNING,
                        evidence={
                            "record_id": doc_id,
                            "entity_id": getattr(doc, "id", None),
                            "document_type": doc_type,
                            "document_reference": doc_ref,
                            "expiry_date": str(expiry_d),
                            "reference_date": str(ref_date),
                            "days_remaining": days_remaining,
                            "warning_threshold": warning_days,
                        },
                        policy_version=policy_version,
                        suggested_action=(
                            f"{doc_type.replace('_', ' ').title()} expires in {days_remaining} days on {expiry_d}. "
                            f"Initiate renewal process soon."
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
                            "record_id": doc_id,
                            "document_type": doc_type,
                            "document_reference": doc_ref,
                            "expiry_date": str(expiry_d),
                            "days_remaining": days_remaining,
                        },
                        policy_version=policy_version,
                    )
                )

        return results
