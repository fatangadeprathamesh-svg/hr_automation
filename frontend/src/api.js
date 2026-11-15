// Unified API & Mock Service Layer for Month-End HR Self-Audit Assistant

export const API_BASE = "http://127.0.0.1:8000";

// In Phase 1 shell, mock mode is enabled by default to run without external dependencies
export let USE_MOCK = true;

export function setUseMock(val) {
  USE_MOCK = Boolean(val);
}

// Pre-seeded test personas matching system spec
export const PERSONAS = {
  EMP001: {
    id: "EMP001",
    name: "Alice Employee",
    email: "alice@company.com",
    role: "employee",
    department: "Engineering",
    avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150",
  },
  MGR001: {
    id: "MGR001",
    name: "Bob Manager",
    email: "bob@company.com",
    role: "manager",
    department: "Engineering",
    avatar: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150",
  },
  HR001: {
    id: "HR001",
    name: "Carol HR Admin",
    email: "carol@company.com",
    role: "hr_admin",
    department: "Human Resources",
    avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150",
  },
};

// State stored in memory/localStorage for session persistence
let currentPersona = PERSONAS.EMP001;
let currentToken = localStorage.getItem("hr_auth_token") || "DEV_TOKEN_EMP001_employee";
let devMode = true;

// Initialize theme from storage
export function getSavedTheme() {
  return localStorage.getItem("hr_theme") || "light";
}

export function saveTheme(theme) {
  localStorage.setItem("hr_theme", theme);
  if (theme === "dark") {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
}

export function setPersona(persona) {
  if (persona) {
    currentPersona = persona;
    localStorage.setItem("hr_current_persona", JSON.stringify(persona));
  }
}

export function getCurrentPersona() {
  const saved = localStorage.getItem("hr_current_persona");
  if (saved) {
    try {
      currentPersona = JSON.parse(saved);
    } catch (_) {}
  }
  return currentPersona;
}

export function setToken(token) {
  currentToken = token || "";
  if (token) {
    localStorage.setItem("hr_auth_token", token);
  } else {
    localStorage.removeItem("hr_auth_token");
  }
}

export function getAuthHeaders(token = null, persona = null) {
  const p = persona || currentPersona;
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  } else if (currentToken) {
    headers["Authorization"] = `Bearer ${currentToken}`;
  } else {
    headers["Authorization"] = `Bearer DEV_TOKEN_${p.id}_${p.role}`;
  }
  return headers;
}

// -------------------------------------------------------------
// MOCK DATA GENERATOR & PERSISTENCE
// -------------------------------------------------------------

const initialMockFlags = [
  {
    id: "FLAG-2026-10-01",
    rule_id: "missing_punch",
    rule_name: "Missing Out-Punch",
    severity: "BLOCKING",
    status: "Open",
    date: "2026-10-14",
    title: "Missing Badge Out-Punch",
    description: "Morning badge-in registered at 09:00 AM EST with no closing badge-out recorded at turnstile.",
    evidence: "punch_in: 2026-10-14T09:00:00-05:00, punch_out: null, device: Turnstile-North-02",
    record_version: 1,
    policy_version: "2026.10.v1",
  },
  {
    id: "FLAG-2026-10-02",
    rule_id: "hours_mismatch",
    rule_name: "Hours Mismatch",
    severity: "BLOCKING",
    status: "Awaiting Manager",
    date: "2026-10-18",
    title: "Timesheet Exceeds Badge Access Hours",
    description: "Timesheet recorded 9.5 hours, but physical badge access indicates 7.0 hours (variance of 2.5h exceeds policy tolerance of 30 min).",
    evidence: "timesheet_hours: 9.50, badge_hours: 7.00, variance: +2.50h",
    record_version: 2,
    policy_version: "2026.10.v1",
  },
  {
    id: "FLAG-2026-10-03",
    rule_id: "missing_receipt",
    rule_name: "Missing Expense Receipt",
    severity: "WARNING",
    status: "Open",
    date: "2026-10-21",
    title: "Receipt Not Attached for Claim > $25",
    description: "Expense claim for client lunch ($84.50) is missing an itemized tax receipt image attachment.",
    evidence: "claim_id: EXP-2026-10-848, amount: $84.50, category: Meals, receipt_url: null",
    record_version: 1,
    policy_version: "2026.10.v1",
  },
  {
    id: "FLAG-2026-10-04",
    rule_id: "missing_punch",
    rule_name: "Missing In-Punch",
    severity: "RESOLVED",
    status: "Resolved",
    date: "2026-10-08",
    title: "Remote Work Adjustment Approved",
    description: "Punches were absent due to approved WFH status; manager signed off on timesheet adjustment.",
    evidence: "wfh_request_id: WFH-9921, approved_by: MGR001",
    record_version: 3,
    policy_version: "2026.10.v1",
  },
];

let mockFlagsState = [...initialMockFlags];

const mockAuditLogs = [
  {
    sequence_id: 104,
    event_id: "evt_9a41c0e3",
    timestamp: "2026-10-28T09:15:22Z",
    actor_id: "MGR001",
    actor_role: "manager",
    action_type: "APPROVE_CORRECTION",
    target_entity: "corrections",
    target_id: "CORR-883",
    current_hash: "3b8a4f91c9e830f6b4e7a2b9104c8f25879a61e3892740bc189d20c57801be92",
    prev_hash: "e7c2a1059f81bc9e47209148d8214fa70b91e7c5301824a91b849204c9e83120",
    verified: true,
  },
  {
    sequence_id: 103,
    event_id: "evt_8f31b209",
    timestamp: "2026-10-27T16:40:11Z",
    actor_id: "EMP001",
    actor_role: "employee",
    action_type: "SUBMIT_CORRECTION",
    target_entity: "corrections",
    target_id: "CORR-883",
    current_hash: "e7c2a1059f81bc9e47209148d8214fa70b91e7c5301824a91b849204c9e83120",
    prev_hash: "d41d8cd98f00b204e9800998ecf8427e00000000000000000000000000000000",
    verified: true,
  },
  {
    sequence_id: 102,
    event_id: "evt_7e20a114",
    timestamp: "2026-10-26T18:00:00Z",
    actor_id: "SYSTEM_AUDIT_ENGINE",
    actor_role: "system",
    action_type: "EVALUATE_RULES",
    target_entity: "audit_runs",
    target_id: "RUN-2026-10-ALL",
    current_hash: "d41d8cd98f00b204e9800998ecf8427e00000000000000000000000000000000",
    prev_hash: "8c91b849204c9e83120e7c2a1059f81bc9e47209148d8214fa70b91e7c530182",
    verified: true,
  },
  {
    sequence_id: 101,
    event_id: "evt_6d10f993",
    timestamp: "2026-10-26T17:45:00Z",
    actor_id: "N8N_WORKFLOW_A",
    actor_role: "service",
    action_type: "INGEST_SOURCE_FEED",
    target_entity: "source_imports",
    target_id: "FEED-ATT-OCT2026",
    current_hash: "8c91b849204c9e83120e7c2a1059f81bc9e47209148d8214fa70b91e7c530182",
    prev_hash: "0000000000000000000000000000000000000000000000000000000000000000",
    verified: true,
  },
];

// -------------------------------------------------------------
// AUTHENTICATION APIS
// -------------------------------------------------------------

export async function login({ email, password, isSignUp = false }) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 350));
    // Determine persona from email
    let persona = PERSONAS.EMP001;
    if (email.toLowerCase().includes("bob") || email.toLowerCase().includes("manager")) {
      persona = PERSONAS.MGR001;
    } else if (email.toLowerCase().includes("carol") || email.toLowerCase().includes("hr")) {
      persona = PERSONAS.HR001;
    }
    return {
      success: true,
      message: isSignUp ? "Account created. Verification code sent." : "One-time passcode sent to your email.",
      email,
      devCode: "123456",
      isDev: true,
      persona,
    };
  }

  // Real API fallback
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, is_signup: isSignUp }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Authentication request failed");
  }
  return res.json();
}

export async function verifyOtp({ email, code }) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 400));
    // Fixed code 123456 works in DEV mode
    if (code !== "123456" && code !== "999999") {
      throw new Error("Invalid verification code. Please check and try again.");
    }

    let persona = PERSONAS.EMP001;
    if (email && (email.toLowerCase().includes("bob") || email.toLowerCase().includes("manager"))) {
      persona = PERSONAS.MGR001;
    } else if (email && (email.toLowerCase().includes("carol") || email.toLowerCase().includes("hr"))) {
      persona = PERSONAS.HR001;
    }

    setPersona(persona);
    const token = `DEV_TOKEN_${persona.id}_${persona.role}`;
    setToken(token);

    return {
      success: true,
      token,
      persona,
      role: persona.role,
    };
  }

  const res = await fetch(`${API_BASE}/api/auth/verify-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Verification failed");
  }
  const data = await res.json();
  if (data.token) {
    setToken(data.token);
  }
  return data;
}

export function logout() {
  setToken("");
  localStorage.removeItem("hr_current_persona");
}

// Reset or resolve mock flags for live interactive demo
export function resolveAllBlockersDemo() {
  mockFlagsState = mockFlagsState.map((f) => ({
    ...f,
    status: "Resolved",
    severity: "RESOLVED",
  }));
}

export function resetFlagsDemo() {
  mockFlagsState = JSON.parse(JSON.stringify(initialMockFlags));
}

// -------------------------------------------------------------
// EMPLOYEE APIS
// -------------------------------------------------------------

export async function fetchReadiness(period = "2026-10") {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    const blockingCount = mockFlagsState.filter((f) => f.severity === "BLOCKING" && f.status !== "Resolved").length;
    const warningCount = mockFlagsState.filter((f) => f.severity === "WARNING" && f.status !== "Resolved").length;
    const resolvedCount = mockFlagsState.filter((f) => f.status === "Resolved").length;
    
    // Starting score is 78% when 2 blockers open; animates to 100% when 0 blockers
    let readiness = 78;
    if (blockingCount === 0) {
      readiness = 100;
    } else if (blockingCount === 1) {
      readiness = 89;
    }

    return {
      period,
      employee_id: currentPersona.id,
      readiness_percentage: readiness,
      blocking_count: blockingCount,
      warning_count: warningCount,
      resolved_count: resolvedCount,
      can_submit: blockingCount === 0,
      feed_status: "COMPLETE",
      flags: [...mockFlagsState],
      trend_history: [
        { month: "May", score: 92, target: 95 },
        { month: "Jun", score: 88, target: 95 },
        { month: "Jul", score: 96, target: 95 },
        { month: "Aug", score: 82, target: 95 },
        { month: "Sep", score: 94, target: 95 },
        { month: "Oct", score: readiness, target: 95 },
      ],
      issues_by_type: [
        { type: "Missing Punch", count: mockFlagsState.filter(f => f.rule_id === "missing_punch" && f.status !== "Resolved").length },
        { type: "Hours Mismatch", count: mockFlagsState.filter(f => f.rule_id === "hours_mismatch" && f.status !== "Resolved").length },
        { type: "Missing Receipt", count: mockFlagsState.filter(f => f.rule_id === "missing_receipt" && f.status !== "Resolved").length },
      ],
    };
  }

  const res = await fetch(`${API_BASE}/employees/me/readiness?period=${period}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch readiness");
  }
  return res.json();
}

export async function submitCorrection(payload) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    // Update local mock flag
    mockFlagsState = mockFlagsState.map((f) => {
      if (f.id === payload.flag_id) {
        return {
          ...f,
          status: "Awaiting Manager",
          record_version: (f.record_version || 1) + 1,
          proposed_value: payload.proposed_value,
          employee_reason: payload.employee_reason,
        };
      }
      return f;
    });

    return {
      success: true,
      correction_id: `CORR-${Math.floor(1000 + Math.random() * 9000)}`,
      flag_id: payload.flag_id,
      status: "pending_manager",
      message: "Correction submitted for manager review.",
    };
  }

  const res = await fetch(`${API_BASE}/corrections`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to submit correction");
  }
  return res.json();
}

export async function submitMonthEnd(period = "2026-10") {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 400));
    const blockers = mockFlagsState.filter((f) => f.severity === "BLOCKING" && f.status !== "Resolved");
    if (blockers.length > 0) {
      throw new Error(`Submission Gate Rejected: Found ${blockers.length} unresolved blocking issue(s). All blockers must be corrected before submission.`);
    }
    return {
      success: true,
      snapshot_id: `SNAP-${Math.random().toString(36).substring(2, 9).toUpperCase()}`,
      period,
      status: "submitted",
      frozen_at: new Date().toISOString(),
      message: "Month-end audit successfully frozen and submitted for HR sign-off.",
    };
  }

  const res = await fetch(`${API_BASE}/submissions`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ period }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Submission gate failed");
  }
  return res.json();
}

// -------------------------------------------------------------
// MANAGER APIS
// -------------------------------------------------------------

export async function fetchPendingCorrections() {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 250));
    return {
      pending_count: 2,
      average_approval_days: 1.4,
      approvals_per_week: [
        { week: "W1", count: 4 },
        { week: "W2", count: 7 },
        { week: "W3", count: 5 },
        { week: "W4", count: 8 },
      ],
      items: [
        {
          correction_id: "CORR-883",
          employee_id: "EMP001",
          employee_name: "Alice Employee",
          flag_id: "FLAG-2026-10-02",
          rule_id: "hours_mismatch",
          rule_name: "Hours Mismatch",
          claimed_difference: "+2.5 Hours",
          employee_reason: "Attended client discovery onsite session from 13:00 to 15:30. Badge-out was bypassed via visitor pass at client headquarters.",
          record_version: 2,
          submitted_at: "2026-10-27T16:40:00Z",
        },
        {
          correction_id: "CORR-904",
          employee_id: "EMP004",
          employee_name: "David Developer",
          flag_id: "FLAG-2026-10-05",
          rule_id: "missing_punch",
          rule_name: "Missing Out-Punch",
          claimed_difference: "Punched out 17:30",
          employee_reason: "Turnstile gate 3 did not chime on departure. Security log confirms exit at 17:31.",
          record_version: 1,
          submitted_at: "2026-10-28T10:15:00Z",
        },
      ],
    };
  }

  const res = await fetch(`${API_BASE}/corrections/pending`, { headers: getAuthHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch pending corrections");
  }
  return res.json();
}

export async function decideCorrection(correctionId, decision, managerReason) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    // If approved, mark flag as resolved
    if (decision === "approved") {
      mockFlagsState = mockFlagsState.map((f) => {
        if (f.id === "FLAG-2026-10-02") {
          return { ...f, status: "Resolved", severity: "RESOLVED" };
        }
        return f;
      });
    }
    return {
      success: true,
      correction_id: correctionId,
      decision,
      manager_reason: managerReason,
      updated_record_version: 3,
      message: `Correction ${decision} successfully.`,
    };
  }

  const res = await fetch(`${API_BASE}/corrections/${correctionId}/decision`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ decision, manager_reason: managerReason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Decision failed");
  }
  return res.json();
}

// -------------------------------------------------------------
// HR ADMIN APIS
// -------------------------------------------------------------

export async function fetchHRMetrics(period = "2026-10") {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));

    if (period === "2026-09") {
      return {
        period: "2026-09",
        submitted_count: 28,
        pending_count: 2,
        total_employees: 30,
        open_blockers: 1,
        average_readiness: 96.4,
        average_resolve_days: 1.3,
        submission_donut: [
          { name: "Submitted", value: 28, fill: "#10B981" },
          { name: "Pending", value: 2, fill: "#F26A21" },
        ],
        issues_by_rule: [
          { rule: "Missing Punch", count: 6, blockers: 2, warnings: 4 },
          { rule: "Hours Mismatch", count: 4, blockers: 1, warnings: 3 },
          { rule: "Missing Receipt", count: 5, blockers: 0, warnings: 5 },
          { rule: "Leave Overlap", count: 1, blockers: 1, warnings: 0 },
          { rule: "Unapproved OT", count: 0, blockers: 0, warnings: 0 },
        ],
        top_recurring_issues: [
          { rank: 1, rule: "Missing Out-Punch on Fridays", frequency: 6, impact: "Medium" },
          { rank: 2, rule: "Expense Claims Over $25 Missing Invoice", frequency: 5, impact: "Medium" },
          { rank: 3, rule: "Timesheet vs Access Badge > 30m", frequency: 4, impact: "High" },
          { rank: 4, rule: "Annual Leave Overlap with Work Hours", frequency: 1, impact: "High" },
          { rank: 5, rule: "Overtime Missing Pre-Approval", frequency: 0, impact: "Low" },
        ],
      };
    }

    if (period === "2026-08") {
      return {
        period: "2026-08",
        submitted_count: 26,
        pending_count: 4,
        total_employees: 30,
        open_blockers: 5,
        average_readiness: 88.5,
        average_resolve_days: 2.1,
        submission_donut: [
          { name: "Submitted", value: 26, fill: "#10B981" },
          { name: "Pending", value: 4, fill: "#F26A21" },
        ],
        issues_by_rule: [
          { rule: "Missing Punch", count: 11, blockers: 7, warnings: 4 },
          { rule: "Hours Mismatch", count: 8, blockers: 5, warnings: 3 },
          { rule: "Missing Receipt", count: 9, blockers: 3, warnings: 6 },
          { rule: "Leave Overlap", count: 4, blockers: 4, warnings: 0 },
          { rule: "Unapproved OT", count: 3, blockers: 2, warnings: 1 },
        ],
        top_recurring_issues: [
          { rank: 1, rule: "Missing Out-Punch on Fridays", frequency: 11, impact: "High" },
          { rank: 2, rule: "Expense Claims Over $25 Missing Invoice", frequency: 9, impact: "Medium" },
          { rank: 3, rule: "Timesheet vs Access Badge > 30m", frequency: 8, impact: "High" },
          { rank: 4, rule: "Annual Leave Overlap with Work Hours", frequency: 4, impact: "High" },
          { rank: 5, rule: "Overtime Missing Pre-Approval", frequency: 3, impact: "Medium" },
        ],
      };
    }

    // Default: October 2026
    return {
      period: "2026-10",
      submitted_count: 24,
      pending_count: 6,
      total_employees: 30,
      open_blockers: 4,
      average_readiness: 91.2,
      average_resolve_days: 1.8,
      submission_donut: [
        { name: "Submitted", value: 24, fill: "#10B981" },
        { name: "Pending", value: 6, fill: "#F26A21" },
      ],
      issues_by_rule: [
        { rule: "Missing Punch", count: 14, blockers: 9, warnings: 5 },
        { rule: "Hours Mismatch", count: 9, blockers: 7, warnings: 2 },
        { rule: "Missing Receipt", count: 7, blockers: 2, warnings: 5 },
        { rule: "Leave Overlap", count: 3, blockers: 3, warnings: 0 },
        { rule: "Unapproved OT", count: 2, blockers: 1, warnings: 1 },
      ],
      top_recurring_issues: [
        { rank: 1, rule: "Missing Out-Punch on Fridays", frequency: 14, impact: "High" },
        { rank: 2, rule: "Timesheet vs Access Badge > 30m", frequency: 9, impact: "High" },
        { rank: 3, rule: "Expense Claims Over $25 Missing Invoice", frequency: 7, impact: "Medium" },
        { rank: 4, rule: "Annual Leave Overlap with Work Hours", frequency: 3, impact: "High" },
        { rank: 5, rule: "Overtime Missing Pre-Approval", frequency: 2, impact: "Medium" },
      ],
    };
  }

  const res = await fetch(`${API_BASE}/submissions?period=${period}`, { headers: getAuthHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch HR metrics");
  }
  return res.json();
}

export async function fetchSubmissions(period = "2026-10") {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 250));
    return [
      {
        snapshot_id: "SNAP-EMP001-202610",
        employee_id: "EMP001",
        employee_name: "Alice Employee",
        department: "Engineering",
        period: "2026-10",
        readiness_score: 100,
        status: "submitted",
        submitted_at: "2026-10-28T14:20:00Z",
        policy_version: "2026.10.v1",
        hr_decision: null,
      },
      {
        snapshot_id: "SNAP-EMP002-202610",
        employee_id: "EMP002",
        employee_name: "Bryan Baker",
        department: "Product",
        period: "2026-10",
        readiness_score: 100,
        status: "approved",
        submitted_at: "2026-10-27T11:05:00Z",
        policy_version: "2026.10.v1",
        hr_decision: "approved",
      },
      {
        snapshot_id: "SNAP-EMP003-202610",
        employee_id: "EMP003",
        employee_name: "Catherine Chen",
        department: "Marketing",
        period: "2026-10",
        readiness_score: 95,
        status: "returned",
        submitted_at: "2026-10-26T09:30:00Z",
        policy_version: "2026.10.v1",
        hr_decision: "returned",
        hr_return_reason: "[EMPLOYEE] Missing tax receipt for travel claim #992.",
      },
    ];
  }

  const res = await fetch(`${API_BASE}/submissions?period=${period}`, { headers: getAuthHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch submissions");
  }
  return res.json();
}

export async function decideSubmission(snapshotId, decision, hrReason, assignedOwner = null) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    return {
      success: true,
      snapshot_id: snapshotId,
      status: decision,
      hr_decision: decision,
      hr_reason: hrReason,
      assigned_owner: assignedOwner,
      message: `Submission pack ${decision} successfully.`,
    };
  }

  const res = await fetch(`${API_BASE}/submissions/${snapshotId}/hr-decision`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      decision,
      hr_reason: hrReason,
      assigned_owner: assignedOwner,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Decision failed");
  }
  return res.json();
}

export async function createExportPack(snapshotId, exportType = "PDF_JSON_PACK") {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 450));
    return {
      export_run_id: `EXP-RUN-${Math.floor(10000 + Math.random() * 90000)}`,
      snapshot_id: snapshotId,
      pack_pdf_uri: `/storage/exports/hr_audit_${snapshotId}.pdf`,
      pack_json_uri: `/storage/exports/hr_audit_${snapshotId}.json`,
      status: "completed",
      is_replayed: false,
      message: "Frozen snapshot rendered into dual PDF and JSON export pack.",
    };
  }

  const res = await fetch(`${API_BASE}/exports`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      snapshot_id: snapshotId,
      export_type: exportType,
      destination_system: "payroll_staging",
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to generate export");
  }
  return res.json();
}

// -------------------------------------------------------------
// AUDIT LOG APIS
// -------------------------------------------------------------

export async function fetchAuditLog() {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    return {
      total_events: mockAuditLogs.length,
      ledger_status: "TAMPER_EVIDENT_VALID",
      root_hash: mockAuditLogs[0].current_hash,
      events: [...mockAuditLogs],
    };
  }

  const res = await fetch(`${API_BASE}/audit-events`, { headers: getAuthHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch audit log");
  }
  return res.json();
}

export async function verifyLedgerIntegrity() {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 350));
    return {
      verified: true,
      checked_events: mockAuditLogs.length,
      genesis_hash: "0000000000000000000000000000000000000000000000000000000000000000",
      head_hash: mockAuditLogs[0].current_hash,
      timestamp: new Date().toISOString(),
      message: "Cryptographic hash chain validated: 0 broken links, 0 tampering detected.",
    };
  }

  const res = await fetch(`${API_BASE}/audit-events/verify-integrity`, { headers: getAuthHeaders() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Integrity verification failed");
  }
  return res.json();
}
