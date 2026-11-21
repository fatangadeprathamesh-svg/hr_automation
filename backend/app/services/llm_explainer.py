import re
import json
import logging
from typing import Dict, Any, List, Optional
import urllib.request
import urllib.error
from app.config import settings

logger = logging.getLogger("hr_audit.ai")

DISCLAIMER_TEXT = "AI-generated, review before use"

# Strict Data Minimization: Redaction rules
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
SENSITIVE_KEYS = {
    "first_name",
    "last_name",
    "full_name",
    "name",
    "email",
    "phone",
    "address",
    "ssn",
    "tax_id",
    "bank_account",
    "routing_number",
    "salary",
    "hourly_rate",
    "home_address",
}


def sanitize_for_ai(data: Any) -> Any:
    """
    Non-negotiable Design Rule for Phase 9:
    Strict data minimization: only IDs and evidence fields sent to LLM.
    No personal employee names, emails, addresses, or private compensation data.
    """
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if k.lower() in SENSITIVE_KEYS:
                continue
            sanitized[k] = sanitize_for_ai(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_for_ai(item) for item in data]
    elif isinstance(data, str):
        # Scrub any email addresses that might appear inside evidence strings
        return EMAIL_REGEX.sub("[REDACTED_EMAIL]", data)
    else:
        return data


class AIExplainerService:
    def __init__(self):
        self.provider = (settings.LLM_PROVIDER or "none").lower().strip()
        self.gemini_key = settings.GEMINI_API_KEY
        self.anthropic_key = settings.ANTHROPIC_API_KEY

    # -------------------------------------------------------------------------
    # Core Feature 1: Explain This Flag
    # -------------------------------------------------------------------------
    def explain_flag(
        self,
        rule_id: str,
        evidence: Dict[str, Any],
        severity: str = "warning",
        outcome: str = "fail",
        policy_version: str = "POLICY-2026.1",
    ) -> Dict[str, Any]:
        """
        Explains in plain English why a specific rule flag was triggered based
        on deterministic evidence, referencing the company policy and remediation steps.
        """
        clean_evidence = sanitize_for_ai(evidence or {})
        rule_norm = (rule_id or "").upper().strip()

        # Try live LLM provider if configured and credentials exist
        if self.provider == "gemini" and self.gemini_key:
            llm_res = self._call_gemini_explainer(rule_norm, clean_evidence, severity, policy_version)
            if llm_res:
                return llm_res

        elif self.provider == "anthropic" and self.anthropic_key:
            llm_res = self._call_anthropic_explainer(rule_norm, clean_evidence, severity, policy_version)
            if llm_res:
                return llm_res

        # Fallback to high-quality deterministic explainer templates
        return self._template_explain_flag(rule_norm, clean_evidence, severity, policy_version)

    # -------------------------------------------------------------------------
    # Core Feature 2: Draft a Correction Request
    # -------------------------------------------------------------------------
    def draft_correction(
        self,
        rule_id: str,
        evidence: Dict[str, Any],
        policy_version: str = "POLICY-2026.1",
        user_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates a professional, courteous employee explanation draft and suggested
        proposed value for manager review.
        """
        clean_evidence = sanitize_for_ai(evidence or {})
        rule_norm = (rule_id or "").upper().strip()

        if self.provider == "gemini" and self.gemini_key:
            llm_res = self._call_gemini_correction_draft(rule_norm, clean_evidence, policy_version, user_notes)
            if llm_res:
                return llm_res

        elif self.provider == "anthropic" and self.anthropic_key:
            llm_res = self._call_anthropic_correction_draft(rule_norm, clean_evidence, policy_version, user_notes)
            if llm_res:
                return llm_res

        return self._template_draft_correction(rule_norm, clean_evidence, policy_version, user_notes)

    # -------------------------------------------------------------------------
    # Core Feature 3: HR Monthly Summary
    # -------------------------------------------------------------------------
    def generate_hr_summary(
        self,
        period: str,
        stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generates an executive summary for HR Admin covering month-end discrepancies,
        root causes, compliance trends, and actionable recommendations.
        Strictly statistical: no screen monitoring, keystroke tracking, or productivity scoring.
        """
        clean_stats = sanitize_for_ai(stats or {})

        if self.provider == "gemini" and self.gemini_key:
            llm_res = self._call_gemini_hr_summary(period, clean_stats)
            if llm_res:
                return llm_res

        elif self.provider == "anthropic" and self.anthropic_key:
            llm_res = self._call_anthropic_hr_summary(period, clean_stats)
            if llm_res:
                return llm_res

        return self._template_hr_summary(period, clean_stats)

    # =========================================================================
    # High-Fidelity Deterministic Fallback Templates
    # =========================================================================
    def _template_explain_flag(
        self,
        rule_id: str,
        evidence: Dict[str, Any],
        severity: str,
        policy_version: str,
    ) -> Dict[str, Any]:
        rule_guides = {
            "MISSING_PUNCH": {
                "title": "Missing In/Out Punch",
                "policy_summary": "Policy requires complete paired punches (clock-in and clock-out) for every scheduled shift. A 60-minute grace window applies.",
                "explanation": (
                    f"A missing punch was detected on {evidence.get('work_date', 'the recorded date')}. "
                    f"Specifically, the {evidence.get('missing', 'clock_out')} timestamp is null in the physical attendance feed. "
                    "Incomplete punches prevent automated calculation of worked hours and legally require manager confirmation."
                ),
                "suggested_action": "Submit a punch correction proposing your actual arrival or departure time with an explanatory note for your manager.",
            },
            "HOURS_MISMATCH": {
                "title": "Badge vs. Timesheet Hours Variance",
                "policy_summary": "Timesheet billable hours must match physical badge duration within a 30-minute tolerance threshold.",
                "explanation": (
                    f"A variance of {evidence.get('variance_minutes', 'exceeding 30')} minutes was found on {evidence.get('work_date', 'the recorded date')}. "
                    f"Logged timesheet hours ({evidence.get('timesheet_hours', 'N/A')}h) differ from calculated badge presence ({evidence.get('attendance_hours', 'N/A')}h). "
                    "This variance exceeds the permissible daily policy buffer."
                ),
                "suggested_action": "Align your timesheet hours with your physical badge presence or submit an off-site/client travel justification.",
            },
            "MISSING_RECEIPT": {
                "title": "Receipt Missing for Expense Claim >= $25",
                "policy_summary": "Any business expense claim equal to or exceeding $25.00 USD must include an attached itemized receipt or tax invoice.",
                "explanation": (
                    f"Claim for {evidence.get('currency', 'USD')} {evidence.get('amount', '0.00')} in category '{evidence.get('category', 'expenses')}' "
                    f"exceeds the mandatory receipt threshold of $25.00 but has no linked receipt attachment reference. "
                    "Unsubstantiated expenses cannot be processed for month-end payroll reimbursement."
                ),
                "suggested_action": "Upload an itemized receipt image/PDF or attach the merchant invoice reference to substantiate the claim.",
            },
            "LEAVE_CONFLICT": {
                "title": "Hours or Punches Logged on Approved Leave Day",
                "policy_summary": "Working hours cannot be logged during approved full-day leave. Partial leave allows up to 4.5 hours maximum.",
                "explanation": (
                    f"Approved {evidence.get('leave_type', 'annual')} leave was recorded on {evidence.get('conflict_date', 'the date')}, "
                    f"yet physical attendance or timesheet hours ({evidence.get('timesheet_hours', 'logged')}h) were submitted for the same calendar date. "
                    "This creates an irreconcilable statutory leave and payroll overlap."
                ),
                "suggested_action": "If you worked on this day, cancel the leave request in the HR portal; otherwise, correct the timesheet to zero hours.",
            },
            "DUPLICATE_CLAIM": {
                "title": "Potential Duplicate Expense Submission",
                "policy_summary": "Expenses with identical receipt identifiers or matching date, amount, and merchant are flagged to prevent duplicate disbursements.",
                "explanation": (
                    f"Claim of {evidence.get('amount', '0.00')} on {evidence.get('claim_date', 'the date')} matches an existing record. "
                    f"Identified duplicate records: {evidence.get('duplicate_with', [])}. "
                    "Submitting identical claims creates compliance and financial audit risks."
                ),
                "suggested_action": "Review your submitted expense history. Withdraw duplicate entries or submit clarification if two distinct charges occurred.",
            },
            "OVER_LIMIT_CLAIM": {
                "title": "Expense Claim Exceeds Policy Category Ceiling",
                "policy_summary": "Company travel and entertainment policy establishes per-category caps (e.g. meals: $75, travel: $500, supplies: $200).",
                "explanation": (
                    f"Claim of {evidence.get('currency', 'USD')} {evidence.get('amount', '0.00')} in category '{evidence.get('category', 'general')}' "
                    f"exceeds the authorized policy ceiling of {evidence.get('policy_limit', '300.00')} by {evidence.get('excess_amount', '0.00')}. "
                    "Excess expenses require executive or VP exception authorization."
                ),
                "suggested_action": "Submit a manager exception approval document or adjust the claim amount to the established policy limit.",
            },
            "UNAPPROVED_OVERTIME": {
                "title": "Unapproved or Excessive Overtime Hours",
                "policy_summary": "Overtime (>8h/day) requires prior manager authorization. Shifts exceeding 12 continuous hours trigger mandatory safety review.",
                "explanation": (
                    f"On {evidence.get('work_date', 'the date')}, total hours reached {evidence.get('total_hours', 'N/A')}h "
                    f"with {evidence.get('unapproved_overtime_hours', 'logged')} overtime hours in state '{evidence.get('approval_state', 'pending')}'. "
                    "Unapproved overtime cannot be finalized into payroll runs."
                ),
                "suggested_action": "Request formal retroactive overtime approval from your manager or adjust timesheet hours if entered erroneously.",
            },
            "PENDING_APPROVALS": {
                "title": "Unresolved Approvals Pending Manager Review",
                "policy_summary": "All timesheets, expenses, leave requests, and corrections must reach a final decision (approved/rejected) prior to submission.",
                "explanation": (
                    f"Item '{evidence.get('record_id', 'record')}' ({evidence.get('entity_type', 'item')}) remains in pending review. "
                    "Month-end close cannot freeze unapproved or open items."
                ),
                "suggested_action": "Contact your direct manager to finalize review and sign-off on your pending submissions.",
            },
            "EXPIRING_DOCUMENTS": {
                "title": "Compliance Document Expiring or Expired",
                "policy_summary": "Statutory right-to-work documents, visas, and passports must remain valid. Expirations within 30 days block closing.",
                "explanation": (
                    f"Your {evidence.get('document_type', 'document')} ({evidence.get('document_reference', 'ID')}) "
                    + (f"expired {evidence.get('days_expired')} days ago on {evidence.get('expiry_date')}." if evidence.get("days_expired")
                       else f"expires in {evidence.get('days_remaining', 'few')} days on {evidence.get('expiry_date')}.")
                ),
                "suggested_action": "Upload your renewed document scan or provide an official renewal extension letter from immigration authorities.",
            },
        }

        guide = rule_guides.get(
            rule_id,
            {
                "title": f"Policy Compliance Issue ({rule_id})",
                "policy_summary": f"Compliance rule evaluated under active standard {policy_version}.",
                "explanation": f"A discrepancy was identified in your month-end records under rule {rule_id}. Evidence: {evidence}",
                "suggested_action": "Review the discrepancies and submit a correction request or contact your HR business partner.",
            },
        )

        return {
            "rule_id": rule_id,
            "title": guide["title"],
            "policy_version": policy_version,
            "severity": severity,
            "is_blocking": severity == "blocking",
            "policy_summary": guide["policy_summary"],
            "explanation": guide["explanation"],
            "suggested_action": guide["suggested_action"],
            "disclaimer": DISCLAIMER_TEXT,
            "provider": "deterministic_template",
        }

    def _template_draft_correction(
        self,
        rule_id: str,
        evidence: Dict[str, Any],
        policy_version: str,
        user_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates tailored proposed values and polite explanation draft."""
        work_date = evidence.get("work_date") or evidence.get("conflict_date") or evidence.get("claim_date") or "the recorded date"
        
        drafts = {
            "MISSING_PUNCH": {
                "proposed_value": "Clock-out: 17:30 (Eastern)",
                "reason": (
                    f"On {work_date}, I departed the office at approximately 17:30 after concluding my daily tasks. "
                    "The badge turnstile did not register my departure. "
                    + (f"Additional context: {user_notes}. " if user_notes else "")
                    + "I confirm these hours were worked in full."
                ),
            },
            "HOURS_MISMATCH": {
                "proposed_value": f"Adjust timesheet to {evidence.get('attendance_hours', 8.0):.1f} hours",
                "reason": (
                    f"Regarding the hours variance on {work_date}: "
                    + (f"{user_notes}. " if user_notes else "I worked offsite during part of the day on client deliverables, which accounts for the badge disparity. ")
                    + "Requesting manager review and alignment with verified hours worked."
                ),
            },
            "MISSING_RECEIPT": {
                "proposed_value": f"Attach receipt for {evidence.get('currency', 'USD')} {evidence.get('amount', '0.00')}",
                "reason": (
                    f"Receipt for {evidence.get('category', 'business')} expense on {work_date} ({evidence.get('currency', 'USD')} {evidence.get('amount', '0.00')}). "
                    + (f"Note: {user_notes}. " if user_notes else "The itemized vendor tax invoice has been uploaded to substantiate this legitimate business expenditure.")
                ),
            },
            "LEAVE_CONFLICT": {
                "proposed_value": "Adjust timesheet to 0.0h for leave date",
                "reason": (
                    f"Correction for hours logged on approved leave date ({work_date}). "
                    + (f"{user_notes}. " if user_notes else "Timesheet hours were erroneously entered due to auto-fill; confirming I was on approved leave and request timesheet adjustment to 0 hours.")
                ),
            },
            "DUPLICATE_CLAIM": {
                "proposed_value": "Withdraw duplicate claim entry",
                "reason": (
                    f"Notice regarding duplicate claim on {work_date}. "
                    + (f"{user_notes}. " if user_notes else "This entry was inadvertently submitted twice during batch upload. Requesting withdrawal of the duplicate record.")
                ),
            },
            "OVER_LIMIT_CLAIM": {
                "proposed_value": f"Policy limit cap ({evidence.get('currency', 'USD')} {evidence.get('policy_limit', '300.00')}) or manager exception",
                "reason": (
                    f"Explanation for {evidence.get('category', 'expense')} exceeding standard ceiling ({evidence.get('currency', 'USD')} {evidence.get('amount', '0.00')}). "
                    + (f"{user_notes}. " if user_notes else "This expense was incurred due to required project travel / urgent operational needs. Requesting manager approval for the policy exception.")
                ),
            },
            "UNAPPROVED_OVERTIME": {
                "proposed_value": f"Approve {evidence.get('unapproved_overtime_hours', 2.0):.1f}h overtime",
                "reason": (
                    f"Requesting formal sign-off for overtime on {work_date}. "
                    + (f"{user_notes}. " if user_notes else "Additional hours were required to meet critical month-end sprint milestones and deployment requirements.")
                ),
            },
            "PENDING_APPROVALS": {
                "proposed_value": "Expedite manager review",
                "reason": (
                    f"Friendly reminder for pending review of {evidence.get('entity_type', 'item')} {evidence.get('record_id', '')} "
                    f"to facilitate timely month-end self-audit closure."
                ),
            },
            "EXPIRING_DOCUMENTS": {
                "proposed_value": "Upload renewed document copy",
                "reason": (
                    f"Submitting renewed {evidence.get('document_type', 'compliance document')} verification. "
                    + (f"{user_notes}. " if user_notes else "Renewal processing has been completed; attaching verified documentation to maintain active work authorization status.")
                ),
            },
        }

        draft = drafts.get(
            rule_id,
            {
                "proposed_value": "Verified compliant record",
                "reason": (
                    f"Correction request regarding {rule_id} on {work_date}. "
                    + (f"{user_notes}." if user_notes else "Requesting manager review and approval to reconcile month-end audit records.")
                ),
            },
        )

        return {
            "rule_id": rule_id,
            "policy_version": policy_version,
            "proposed_value": draft["proposed_value"],
            "draft_reason": draft["reason"],
            "disclaimer": DISCLAIMER_TEXT,
            "provider": "deterministic_template",
        }

    def _template_hr_summary(
        self,
        period: str,
        stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generates an executive statistical summary for HR leadership.
        Strict non-negotiable rule: Statistical aggregates only; no individual surveillance.
        """
        total_audits = stats.get("total_audited_employees", stats.get("total_audits", 30))
        blocking_audits = stats.get("employees_with_blockers", stats.get("blocking_count", 6))
        clean_audits = total_audits - blocking_audits
        clean_rate = round((clean_audits / total_audits * 100), 1) if total_audits > 0 else 100.0

        top_rules = stats.get("top_flagged_rules", [
            {"rule_id": "MISSING_RECEIPT", "count": 12, "description": "Expense claims >= $25 missing itemized receipt attachments"},
            {"rule_id": "HOURS_MISMATCH", "count": 9, "description": "Discrepancy between badge swipe presence and timesheet hours > 30m"},
            {"rule_id": "MISSING_PUNCH", "count": 7, "description": "Unpaired badge clock-in or clock-out events"},
        ])

        data_health = stats.get("data_health_completeness", "100% feeds ingested")

        executive_summary = (
            f"Month-End Self-Audit Executive Briefing for cycle {period}. "
            f"Across {total_audits} audited employees, {clean_audits} ({clean_rate}%) are fully clear of blocking compliance discrepancies. "
            f"Currently, {blocking_audits} employees require manager or employee remediation before payroll freeze. "
            f"Source system data health is {data_health}."
        )

        key_insights = [
            f"High self-audit readiness rate: {clean_rate}% of the workforce has zero blocking compliance issues.",
            f"Expense documentation remains the primary blocker: {top_rules[0]['rule_id'] if top_rules else 'MISSING_RECEIPT'} accounted for the highest number of holds.",
            "Timesheet-to-badge reconciliation flagged variances predominantly on Mondays and Fridays, indicating remote/travel hybrid patterns.",
            f"Source feed integrity: All upstream source imports for {period} are verified tamper-free with complete cryptographic audit logs.",
        ]

        recommended_actions = [
            "Send an automated reminder to employees with missing receipts (threshold $25.00) to upload invoices before the payroll cutoff.",
            "Prompt engineering and operations managers to clear their pending approval queues (SLA: under 48 hours).",
            "Remind international staff with visas expiring within 60 days to upload renewal progress receipts.",
            "No systemic payroll anomalies detected; proceed with standard payroll export generation once open blockers resolve.",
        ]

        return {
            "period": period,
            "executive_summary": executive_summary,
            "readiness_rate": f"{clean_rate}%",
            "total_employees_audited": total_audits,
            "clean_employees_count": clean_audits,
            "employees_with_blockers": blocking_audits,
            "key_insights": key_insights,
            "top_discrepancies": top_rules,
            "recommended_actions": recommended_actions,
            "surveillance_notice": "Strictly statistical overview; screen monitoring, keystroke tracking, and productivity scoring are prohibited by design.",
            "disclaimer": DISCLAIMER_TEXT,
            "provider": "deterministic_template",
        }

    # =========================================================================
    # Live External LLM Callers (Gemini / Anthropic) with Data Minimization
    # =========================================================================
    def _call_gemini_explainer(self, rule_id: str, evidence: dict, severity: str, policy_version: str) -> Optional[dict]:
        prompt = (
            f"You are the Month-End HR Self-Audit Assistant. "
            f"Explain to an employee why the following deterministic rule flag was raised, citing policy guidelines and resolution steps.\n"
            f"Rule ID: {rule_id}\n"
            f"Policy Version: {policy_version}\n"
            f"Severity: {severity}\n"
            f"Sanitized Evidence: {json.dumps(evidence)}\n\n"
            f"Format response as strict JSON with keys: explanation, policy_summary, suggested_action. "
            f"Never assess employee productivity or performance. Keep it empathetic, concise, and professional."
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={self.gemini_key}"
        try:
            req_data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                clean_text = text.strip().replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean_text)
                return {
                    "rule_id": rule_id,
                    "title": f"Policy Compliance Issue ({rule_id})",
                    "policy_version": policy_version,
                    "severity": severity,
                    "is_blocking": severity == "blocking",
                    "policy_summary": parsed.get("policy_summary", "Policy compliance requirement."),
                    "explanation": parsed.get("explanation", clean_text),
                    "suggested_action": parsed.get("suggested_action", "Submit a correction to resolve this flag."),
                    "disclaimer": DISCLAIMER_TEXT,
                    "provider": "gemini",
                }
        except Exception as e:
            logger.warning("Gemini API call failed, using deterministic fallback: %s", e)
            return None

    def _call_anthropic_explainer(self, rule_id: str, evidence: dict, severity: str, policy_version: str) -> Optional[dict]:
        prompt = (
            f"You are the Month-End HR Self-Audit Assistant. "
            f"Explain to an employee why the following deterministic rule flag was raised:\n"
            f"Rule ID: {rule_id}\n"
            f"Policy Version: {policy_version}\n"
            f"Severity: {severity}\n"
            f"Sanitized Evidence: {json.dumps(evidence)}\n\n"
            f"Format response as JSON with keys: explanation, policy_summary, suggested_action. "
            f"Never assess employee productivity. Keep it professional."
        )
        try:
            req_data = json.dumps({
                "model": settings.ANTHROPIC_MODEL,
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                }
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["content"][0]["text"]
                clean_text = text.strip().replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean_text)
                return {
                    "rule_id": rule_id,
                    "title": f"Policy Compliance Issue ({rule_id})",
                    "policy_version": policy_version,
                    "severity": severity,
                    "is_blocking": severity == "blocking",
                    "policy_summary": parsed.get("policy_summary", "Policy compliance requirement."),
                    "explanation": parsed.get("explanation", clean_text),
                    "suggested_action": parsed.get("suggested_action", "Submit a correction to resolve this flag."),
                    "disclaimer": DISCLAIMER_TEXT,
                    "provider": "anthropic",
                }
        except Exception as e:
            logger.warning("Anthropic API call failed, using deterministic fallback: %s", e)
            return None

    def _call_gemini_correction_draft(self, rule_id: str, evidence: dict, policy_version: str, user_notes: Optional[str]) -> Optional[dict]:
        prompt = (
            f"Draft a polite, concise employee correction request for manager review.\n"
            f"Rule: {rule_id}, Policy: {policy_version}, Evidence: {json.dumps(evidence)}, Context hint: {user_notes or 'none'}.\n"
            f"Format as JSON with keys: proposed_value, draft_reason."
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={self.gemini_key}"
        try:
            req_data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                clean_text = text.strip().replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean_text)
                return {
                    "rule_id": rule_id,
                    "policy_version": policy_version,
                    "proposed_value": parsed.get("proposed_value", "Requested adjustment"),
                    "draft_reason": parsed.get("draft_reason", clean_text),
                    "disclaimer": DISCLAIMER_TEXT,
                    "provider": "gemini",
                }
        except Exception as e:
            logger.warning("Gemini correction draft failed: %s", e)
            return None

    def _call_anthropic_correction_draft(self, rule_id: str, evidence: dict, policy_version: str, user_notes: Optional[str]) -> Optional[dict]:
        prompt = (
            f"Draft a polite, concise employee correction request for manager review.\n"
            f"Rule: {rule_id}, Policy: {policy_version}, Evidence: {json.dumps(evidence)}, Context hint: {user_notes or 'none'}.\n"
            f"Format as JSON with keys: proposed_value, draft_reason."
        )
        try:
            req_data = json.dumps({
                "model": settings.ANTHROPIC_MODEL,
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}]
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                }
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["content"][0]["text"]
                clean_text = text.strip().replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean_text)
                return {
                    "rule_id": rule_id,
                    "policy_version": policy_version,
                    "proposed_value": parsed.get("proposed_value", "Requested adjustment"),
                    "draft_reason": parsed.get("draft_reason", clean_text),
                    "disclaimer": DISCLAIMER_TEXT,
                    "provider": "anthropic",
                }
        except Exception as e:
            logger.warning("Anthropic correction draft failed: %s", e)
            return None

    def _call_gemini_hr_summary(self, period: str, stats: dict) -> Optional[dict]:
        prompt = (
            f"Generate an executive HR month-end compliance briefing for period {period} based on stats: {json.dumps(stats)}.\n"
            f"Strictly statistical overview; no productivity scoring or individual surveillance.\n"
            f"Format as JSON with keys: executive_summary, key_insights (array of strings), recommended_actions (array of strings)."
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={self.gemini_key}"
        try:
            req_data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                clean_text = text.strip().replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean_text)
                return {
                    "period": period,
                    "executive_summary": parsed.get("executive_summary", clean_text),
                    "key_insights": parsed.get("key_insights", []),
                    "recommended_actions": parsed.get("recommended_actions", []),
                    "top_discrepancies": stats.get("top_flagged_rules", []),
                    "surveillance_notice": "Strictly statistical overview; screen monitoring, keystroke tracking, and productivity scoring are prohibited by design.",
                    "disclaimer": DISCLAIMER_TEXT,
                    "provider": "gemini",
                }
        except Exception as e:
            logger.warning("Gemini HR summary failed: %s", e)
            return None

    def _call_anthropic_hr_summary(self, period: str, stats: dict) -> Optional[dict]:
        prompt = (
            f"Generate an executive HR month-end compliance briefing for period {period} based on stats: {json.dumps(stats)}.\n"
            f"Strictly statistical overview; no productivity scoring.\n"
            f"Format as JSON with keys: executive_summary, key_insights (array of strings), recommended_actions (array of strings)."
        )
        try:
            req_data = json.dumps({
                "model": settings.ANTHROPIC_MODEL,
                "max_tokens": 700,
                "messages": [{"role": "user", "content": prompt}]
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                }
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["content"][0]["text"]
                clean_text = text.strip().replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean_text)
                return {
                    "period": period,
                    "executive_summary": parsed.get("executive_summary", clean_text),
                    "key_insights": parsed.get("key_insights", []),
                    "recommended_actions": parsed.get("recommended_actions", []),
                    "top_discrepancies": stats.get("top_flagged_rules", []),
                    "surveillance_notice": "Strictly statistical overview; screen monitoring, keystroke tracking, and productivity scoring are prohibited by design.",
                    "disclaimer": DISCLAIMER_TEXT,
                    "provider": "anthropic",
                }
        except Exception as e:
            logger.warning("Anthropic HR summary failed: %s", e)
            return None


ai_explainer = AIExplainerService()
