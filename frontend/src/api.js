// API Client for Month-End HR Self-Audit Assistant

export const API_BASE = "http://127.0.0.1:8000";

// Pre-seeded test personas
export const PERSONAS = {
  EMP001: {
    id: "EMP001",
    name: "Alice Employee",
    role: "employee",
  },
  MGR001: {
    id: "MGR001",
    name: "Bob Manager",
    role: "manager",
  },
  HR001: {
    id: "HR001",
    name: "Carol HR Admin",
    role: "hr_admin",
  },
};

let currentPersona = PERSONAS.EMP001;
let currentToken = "";

export function setPersona(persona) {
  if (persona) {
    currentPersona = persona;
  }
}

export function getCurrentPersona() {
  return currentPersona;
}

export function setToken(token) {
  currentToken = token || "";
}

export function getAuthHeaders(token = null, persona = null) {
  const p = persona || currentPersona;
  const headers = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  } else if (currentToken) {
    headers["Authorization"] = `Bearer ${currentToken}`;
  } else {
    // Development fallback bearer token with verified server-side identity
    headers["Authorization"] = `Bearer DEV_TOKEN_${p.id}_${p.role}`;
  }
  return headers;
}

export async function fetchReadiness(period = "2026-10", token = null, persona = null) {
  const headers = getAuthHeaders(token, persona);
  const res = await fetch(`${API_BASE}/employees/me/readiness?period=${period}`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch readiness");
  }
  return res.json();
}

export async function fetchPendingCorrections(token = null, persona = null) {
  const headers = getAuthHeaders(token, persona);
  const res = await fetch(`${API_BASE}/corrections/pending`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch pending corrections");
  }
  return res.json();
}

export async function submitCorrection(payload, token = null, persona = null) {
  const headers = getAuthHeaders(token, persona);
  const res = await fetch(`${API_BASE}/corrections`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to submit correction");
  }
  return res.json();
}

export async function decideCorrection(correctionId, decision, managerReason, token = null, persona = null) {
  const headers = getAuthHeaders(token, persona);
  const res = await fetch(`${API_BASE}/corrections/${correctionId}/decision`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      decision,
      manager_reason: managerReason,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to decide correction");
  }
  return res.json();
}

export async function triggerAudit(employeeId, period = "2026-10", token = null, persona = null) {
  const headers = getAuthHeaders(token, persona);
  const res = await fetch(`${API_BASE}/audit-runs`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      employee_id: employeeId,
      period,
      trigger: "manual",
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to trigger audit run");
  }
  return res.json();
}

export async function submitMonthEnd(period = "2026-10", token = null, persona = null) {
  const headers = getAuthHeaders(token, persona);
  const res = await fetch(`${API_BASE}/submissions`, {
    method: "POST",
    headers,
    body: JSON.stringify({ period }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Submission gate failed");
  }
  return res.json();
}

export async function fetchSubmissions(period = null, token = null, persona = null) {
  const headers = getAuthHeaders(token, persona);
  const url = period ? `${API_BASE}/submissions?period=${period}` : `${API_BASE}/submissions`;
  const res = await fetch(url, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch submissions");
  }
  return res.json();
}

export async function getSubmissionSnapshot(snapshotId, token = null, persona = null) {
  const headers = getAuthHeaders(token, persona);
  const res = await fetch(`${API_BASE}/submissions/${snapshotId}`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch submission snapshot");
  }
  return res.json();
}

export async function decideSubmission(snapshotId, decision, hrReason, assignedOwner = null, token = null, persona = null) {
  const headers = getAuthHeaders(token, persona);
  const res = await fetch(`${API_BASE}/submissions/${snapshotId}/hr-decision`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      decision,
      hr_reason: hrReason,
      assigned_owner: assignedOwner,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "HR review decision failed");
  }
  return res.json();
}

export async function createExportPack(snapshotId, exportType = "PDF_JSON_PACK", token = null, persona = null) {
  const headers = getAuthHeaders(token, persona);
  const res = await fetch(`${API_BASE}/exports`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      snapshot_id: snapshotId,
      export_type: exportType,
      destination_system: "payroll_staging",
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to generate export pack");
  }
  return res.json();
}

export async function fetchExportRuns(token = null, persona = null) {
  const headers = getAuthHeaders(token, persona);
  const res = await fetch(`${API_BASE}/exports`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch export runs");
  }
  return res.json();
}

export function getDownloadUrl(exportRunId, fileType = "pdf") {
  return `${API_BASE}/exports/${exportRunId}/download/${fileType}`;
}
