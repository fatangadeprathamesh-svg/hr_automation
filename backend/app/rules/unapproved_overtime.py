from typing import Dict, Any, List
from app.rules.base import BaseRule, RuleResult, RuleOutcome, RuleSeverity


class UnapprovedOvertimeRule(BaseRule):
    rule_id = "OVERTIME_NO_APPROVAL"
    rule_version = "1.0"

    def evaluate(
        self,
        context: Dict[str, Any],
        policy_config: Dict[str, Any],
        policy_version: str,
    ) -> List[RuleResult]:
        """
        OVERTIME_NO_APPROVAL:
        1. Attendance: hours_total > 9.5 and overtime_approved = N (blocking).
        2. Timesheets: total_hours > 12.0 (blocking) or overtime_hours > 0 with pending approval (warning).
        """
        results: List[RuleResult] = []
        attendance_records = context.get("attendance", [])
        timesheets = context.get("timesheets", [])

        if not attendance_records and not timesheets:
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    status=RuleOutcome.NOT_APPLICABLE,
                    severity=RuleSeverity.INFO,
                    evidence={"message": "No attendance or timesheet records found for this period."},
                    policy_version=policy_version,
                    suggested_action=None,
                )
            )
            return results

        # 1. Evaluate Attendance (if present)
        for att in attendance_records:
            record_id = getattr(att, "source_record_id", None) or getattr(att, "id", "UNKNOWN")
            work_date = getattr(att, "work_date", None)
            hours_raw = getattr(att, "hours_total", None)
            ot_approved = (getattr(att, "overtime_approved", "") or "").strip().upper()

            if hours_raw is not None:
                try:
                    hrs = float(hours_raw)
                except (ValueError, TypeError):
                    hrs = 0.0
            elif getattr(att, "clock_in", None) and getattr(att, "clock_out", None):
                hrs = (att.clock_out - att.clock_in).total_seconds() / 3600.0
            else:
                hrs = 0.0

            if hrs > 9.5:
                if ot_approved in ("N", "NO", "0", "FALSE", ""):
                    results.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            status=RuleOutcome.FAIL,
                            severity=RuleSeverity.BLOCKING,
                            evidence={
                                "record_id": record_id,
                                "work_date": str(work_date) if work_date else None,
                                "hours_total": hrs,
                                "overtime_approved": ot_approved or "N",
                            },
                            policy_version=policy_version,
                            suggested_action="Request manager overtime approval for hours exceeding 9.5 hours.",
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
                                "record_id": record_id,
                                "work_date": str(work_date) if work_date else None,
                                "hours_total": hrs,
                                "overtime_approved": ot_approved,
                            },
                            policy_version=policy_version,
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
                            "record_id": record_id,
                            "work_date": str(work_date) if work_date else None,
                            "hours_total": hrs,
                            "message": f"Hours ({hrs}h) within standard limit (<= 9.5h).",
                        },
                        policy_version=policy_version,
                    )
                )

        # 2. Evaluate Timesheets (if present)
        if timesheets:
            for ts in timesheets:
                record_id = getattr(ts, "source_record_id", None) or getattr(ts, "id", "UNKNOWN")
                work_date = getattr(ts, "work_date", None)
                reg_h = float(getattr(ts, "regular_hours", 0.0) or 0.0)
                ot_h = float(getattr(ts, "overtime_hours", 0.0) or 0.0)
                total_h = reg_h + ot_h
                appr = (getattr(ts, "approval_state", "") or "").strip().lower()

                # Data health check: corrupted hours (>24h or negative)
                if total_h > 24.0 or reg_h < 0.0 or ot_h < 0.0:
                    results.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            status=RuleOutcome.UNKNOWN,
                            severity=RuleSeverity.WARNING,
                            evidence={
                                "record_id": record_id,
                                "work_date": str(work_date) if work_date else None,
                                "total_hours": total_h,
                                "message": f"Corrupted timesheet hours (regular: {reg_h}, ot: {ot_h}).",
                            },
                            is_data_health_issue=True,
                            policy_version=policy_version,
                            suggested_action="Data health issue: contact payroll admin to correct negative or impossible hours.",
                        )
                    )
                    continue

                if total_h > 12.0:
                    results.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            status=RuleOutcome.FAIL,
                            severity=RuleSeverity.BLOCKING,
                            evidence={
                                "record_id": record_id,
                                "work_date": str(work_date) if work_date else None,
                                "total_hours": total_h,
                                "overtime_hours": ot_h,
                                "unapproved_overtime_hours": ot_h,
                                "message": f"Excessive work hours ({total_h}h) exceeds 12.0h maximum limit.",
                            },
                            policy_version=policy_version,
                            suggested_action="Exceeds 12.0h statutory maximum shift length.",
                        )
                    )
                elif ot_h > 0 and appr in ("pending", "unapproved", "pending_review"):
                    results.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            status=RuleOutcome.FAIL,
                            severity=RuleSeverity.WARNING,
                            evidence={
                                "record_id": record_id,
                                "work_date": str(work_date) if work_date else None,
                                "overtime_hours": ot_h,
                                "unapproved_overtime_hours": ot_h,
                                "approval_state": appr,
                            },
                            policy_version=policy_version,
                            suggested_action="Manager approval required for overtime hours.",
                        )
                    )
                elif not attendance_records:
                    results.append(
                        RuleResult(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            status=RuleOutcome.PASS,
                            severity=RuleSeverity.INFO,
                            evidence={
                                "record_id": record_id,
                                "total_hours": total_h,
                            },
                            policy_version=policy_version,
                        )
                    )

        return results
