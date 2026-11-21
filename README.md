# Month-End HR Self-Audit Assistant

> An employee-centric, deterministic, privacy-first month-end audit platform designed to eliminate payroll discrepancies, expense errors, and compliance blockers before monthly financial close.

---

## 1. Executive Summary & Architecture Overview

The **Month-End HR Self-Audit Assistant** empowers employees, managers, and HR administrators to verify and reconcile attendance, timesheet hours, expense claims, leave records, and compliance documentation prior to month-end payroll submission.

Unlike traditional surveillance tools or subjective grading algorithms, this system is governed by strict ethical and operational design principles:
- **100% Deterministic Rule Engine**: Every audit decision is evaluated by reproducible code with exact threshold comparison.
- **Strict 4-Outcome Evaluation Matrix**: Every rule outputs one of `pass`, `fail`, `unknown`, or `not_applicable`.
- **Zero False Accusations (Data Health Safeguard)**: Missing, corrupted, or incomplete upstream data is classified as `unknown` (`is_data_health_issue=True`) and flagged to IT/HR Operations—it is **never** counted as an employee infraction.
- **Anti-Surveillance & Anti-Grading Guarantee**: The system measures data completeness and compliance readiness only. It **never** computes productivity scores, keystroke metrics, employee rankings, or punitive metrics.
- **Provider-Agnostic Auxiliary LLM**: Generative AI is strictly auxiliary (used only for plain-English explanations, correction drafting assistance, and executive summaries) with automated PII redaction and offline deterministic fallback templates.
- **Tamper-Evident Ledger**: Every correction and approval is sealed with cryptographic SHA-256 hash chaining (`prev_hash` $\rightarrow$ `record_hash`).

```
+-----------------------------------------------------------------------------------+
|                                  USER INTERFACES                                  |
|   [React 18 + Vite]  -  Employee Dashboard  |  Manager Review  |  HR Admin Console |
+-----------------------------------------+-----------------------------------------+
                                          | REST API (HTTP + httpOnly Cookies)
+-----------------------------------------v-----------------------------------------+
|                               FASTAPI BACKEND CORE                                |
|  +---------------------+  +----------------------+  +---------------------------+ |
|  | Authentication &    |  | Deterministic Rule   |  | Corrections State Machine | |
|  | Role-Based Access   |  | Engine (9 Rules)     |  | & Optimistic Lock (409)   | |
|  +---------------------+  +----------------------+  +---------------------------+ |
|  +---------------------+  +----------------------+  +---------------------------+ |
|  | Auxiliary LLM Layer |  | Submission Packager  |  | SHA-256 Hash-Chained      | |
|  | (PII Sanitization)  |  | & Dual Payroll/Fin   |  | Audit Ledger              | |
|  +---------------------+  +----------------------+  +---------------------------+ |
+-----------------------------------------+-----------------------------------------+
                                          | SQLAlchemy 2.0 ORM
+-----------------------------------------v-----------------------------------------+
|                                  PERSISTENCE LAYER                                |
|          SQLite (Local Development) / PostgreSQL (Production) + Alembic           |
+-----------------------------------------+-----------------------------------------+
                                          | Webhooks & Triggers
+-----------------------------------------v-----------------------------------------+
|                                 n8n WORKFLOW ENGINE                               |
|   A: Scheduled Reminders | B: Ingestion Sync | C: Slack Alerts | D: Dual Export   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Eleven-Phase Delivery Audit Trail

| Phase | Title | Commit | Core Deliverables |
|:---:|:---|:---:|:---|
| **0** | Baseline & Recovery | `886081b` | Python 3.11+, Node 18+, venv setup, `.env` baseline, no-docker recovery. |
| **1** | Frontend Shell | `07ac8cc` | React 18, Tailwind CSS, sliding orange blade login, 6-digit OTP UI, employee dashboard. |
| **2** | Financial Dashboard | `2e10793` | Recharts expense breakdown, animated readiness ring (78% $\rightarrow$ 100%), blocker drawer. |
| **3** | Database Architecture | `db53c54` | 16 Alembic tables, UUID keys, effective-dated policy versions, 30-employee seed dataset. |
| **4** | Rules Engine v1 | `58df3df` | `MISSING_PUNCH`, `HOURS_MISMATCH`, `MISSING_RECEIPT`, 50 unit tests, data health guards. |
| **5** | Corrections & Ledger | `d1d8fc6` | Corrections state machine, optimistic locking (409), dual export, SHA-256 hash-chained ledger. |
| **6** | Auth & Security | `5498bda` | bcrypt passwords, 10m email OTP, Google SSO OAuth2, httpOnly cookies, RBAC, rate limiting. |
| **7** | n8n Automation | `72dff5e` | Blueprints Workflows A–E, zero hardcoded credentials, 5-step controlled export integration tests. |
| **8** | Rules Engine v2 | `a3b2a60` | `LEAVE_CONFLICT`, `DUPLICATE_CLAIM`, `OVER_LIMIT_CLAIM`, `UNAPPROVED_OVERTIME`, `PENDING_APPROVALS`, `EXPIRING_DOCUMENTS`. |
| **9** | Auxiliary AI Layer | `d59ce17` | Plain-English explainers, correction drafting assist, HR executive summary, PII scrub, offline fallback. |
| **10**| Evaluation & Delivery | `feat(phase-10)` | Labeled ground truth benchmark (28 cases), evaluation script, 100% precision/recall, master documentation. |

---

## 3. Quickstart Guide (Windows PowerShell)

### Prerequisites
- Python 3.11 or higher
- Node.js 18 or higher & npm
- Git

### 1. Clone & Setup Environment Files
```powershell
# Copy environment configuration templates
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env
```

### 2. Backend Setup
```powershell
# Navigate to backend directory
cd backend

# Create virtual environment and activate
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed 30 synthetic employees, policy versions, and historical audit records
python app/seed.py

# Start backend server (runs on port 8000)
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup (New Terminal)
```powershell
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server (runs on port 3000)
npm run dev
```

### 4. Demo Login Credentials
| Role | Email | Password | OTP Code (Dev) | Permissions |
|:---|:---|:---|:---:|:---|
| **Employee** | `alice@example.com` | `Password123!` | Any 6 digits | View own dashboard, submit corrections, sign-off. |
| **Manager** | `bob.manager@example.com` | `Password123!` | Any 6 digits | Review direct reports, approve/reject corrections. |
| **HR Admin** | `carol.hr@example.com` | `Password123!` | Any 6 digits | Organization overview, dual payroll/finance export, audit ledger. |

---

## 4. Deterministic Rules Engine Specification

The system evaluates 9 deterministic rules against month-end employee data.

| Rule ID | Name | Monitored Condition | Default Threshold | Fail Severity |
|:---|:---|:---|:---|:---:|
| `MISSING_PUNCH` | Unpaired Punches | Clock-in without clock-out or vice-versa | 0 unpaired punches | `blocking` |
| `HOURS_MISMATCH` | Hours Discrepancy | Variance between timesheet and physical badge punches | 30 minutes | `blocking` |
| `MISSING_RECEIPT` | Unreceipted Expense | Expense claim lacking receipt reference | $\ge \$25.00$ | `blocking` |
| `LEAVE_CONFLICT` | Leave Overlap | Attendance punches or timesheets on approved leave days | 0h (full day) / 4.5h (half day) | `blocking` / `warning` |
| `DUPLICATE_CLAIM` | Duplicate Expense | Identical receipt reference or (date + amount + merchant) | Exact match | `blocking` |
| `OVER_LIMIT_CLAIM` | Expense Cap Exceeded | Claim amount exceeding policy category limits | Meals \$75, Travel \$500, etc. | `blocking` |
| `UNAPPROVED_OVERTIME` | Overtime Compliance | Overtime without manager approval or exceeding daily maximum | 8.0h standard / 12.0h cap | `warning` / `blocking` |
| `PENDING_APPROVALS` | Pending Workflow Items| Timesheets, expenses, or corrections awaiting review | 0 pending at close | `blocking` |
| `EXPIRING_DOCUMENTS` | Compliance Expiry | Passports, visas, work permits nearing expiration | 60 days (warning), 30 days (blocking) | `warning` / `blocking` |

### 4-Outcome Evaluation Matrix
1. **`PASS`**: Data conforms strictly to policy requirements.
2. **`FAIL`**: Valid discrepancy detected requiring employee correction or manager review.
3. **`UNKNOWN`**: Upstream feed incomplete, corrupted, or truncated (`is_data_health_issue=True`). **Never blamed on employee.**
4. **`NOT_APPLICABLE`**: Record category not present for this employee in the evaluated period.

---

## 5. Evaluation Benchmark & Performance Metrics (Phase 10)

The system was evaluated against a labeled ground truth dataset ([`evaluation/ground_truth_dataset.json`](file:///c:/Users/Dell/Downloads/hr-self-audit/evaluation/ground_truth_dataset.json)) comprising 28 benchmark cases spanning positive, negative, boundary, and corrupted feed conditions across all 9 rules.

### Performance Summary
```
================================================================================
 MONTH-END HR SELF-AUDIT ASSISTANT - DETERMINISTIC RULE ENGINE BENCHMARK
================================================================================
Rules Evaluated:         9
Total Test Cases:        28
--------------------------------------------------------------------------------
Precision:               100.0% (14/14)  [Zero False Positives]
Recall (Sensitivity):    100.0% (14/14)  [Zero False Negatives]
Specificity:             100.0% (11/11)
Accuracy:                100.0% (25/25)
F1-Score:                1.0000
Data Health Handling:    100.0% (3/3)    [Zero False Accusations]
--------------------------------------------------------------------------------
```

### Detailed Per-Rule Breakdown
| Rule ID | Cases | True Pos (TP) | False Pos (FP) | True Neg (TN) | False Neg (FN) | Precision | Recall | F1 | Data Health | Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `MISSING_PUNCH` | 5 | 2 | 0 | 2 | 0 | **100%** | **100%** | 1.00 | 100% (1/1) | **PASSED** |
| `HOURS_MISMATCH` | 3 | 1 | 0 | 1 | 0 | **100%** | **100%** | 1.00 | 100% (1/1) | **PASSED** |
| `MISSING_RECEIPT` | 4 | 1 | 0 | 2 | 0 | **100%** | **100%** | 1.00 | 100% (1/1) | **PASSED** |
| `LEAVE_CONFLICT` | 3 | 2 | 0 | 1 | 0 | **100%** | **100%** | 1.00 | N/A | **PASSED** |
| `DUPLICATE_CLAIM` | 2 | 1 | 0 | 1 | 0 | **100%** | **100%** | 1.00 | N/A | **PASSED** |
| `OVER_LIMIT_CLAIM` | 2 | 1 | 0 | 1 | 0 | **100%** | **100%** | 1.00 | N/A | **PASSED** |
| `UNAPPROVED_OVERTIME` | 3 | 2 | 0 | 1 | 0 | **100%** | **100%** | 1.00 | N/A | **PASSED** |
| `PENDING_APPROVALS` | 2 | 1 | 0 | 1 | 0 | **100%** | **100%** | 1.00 | N/A | **PASSED** |
| `EXPIRING_DOCUMENTS` | 4 | 3 | 0 | 1 | 0 | **100%** | **100%** | 1.00 | N/A | **PASSED** |

To reproduce the benchmark at any time:
```powershell
python evaluation/evaluate_rules.py
```

---

## 6. Security, Privacy, & Anti-Surveillance Safeguards

1. **PII Sanitization & Redaction**: The auxiliary LLM engine processes anonymized record IDs, dates, and amounts only. Names, email addresses, national IDs, and biometric data are never passed to LLM prompts.
2. **Deterministic Fallbacks**: If external LLM APIs fail or time out, the system automatically falls back to deterministic template generators without blocking user operations.
3. **No Surveillance Metrics**: The system rejects any request to rank employees, monitor active window time, calculate keystrokes, or output productivity scoring.
4. **Optimistic Locking (HTTP 409)**: Corrections enforce `original_record_version` concurrency checks. Concurrent updates return HTTP 409 Conflict with state diffs.
5. **Cryptographic Audit Ledger**: Every correction decision generates an immutable record with SHA-256 hash chaining:
   $$\text{record\_hash} = \text{SHA256}(\text{prev\_hash} + \text{correction\_id} + \text{reviewer\_id} + \text{decision} + \text{timestamp})$$
   Any manual tampering with database history breaks the ledger chain and is detected by `/audit-ledger/verify`.

---

## 7. API Reference

| Method | Endpoint | Access Role | Description |
|:---|:---|:---:|:---|
| `POST` | `/auth/login` | Public | Authenticate with email/password; initiates OTP challenge. |
| `POST` | `/auth/verify-otp` | Public | Validates 6-digit OTP and issues secure httpOnly JWT cookie. |
| `GET` | `/auth/me` | Authenticated | Returns authenticated user profile and permissions. |
| `POST` | `/auth/logout` | Authenticated | Clears session cookie and invalidates token. |
| `GET` | `/employees/me/readiness` | Employee | Retrieves employee audit readiness score, blockers, and flags. |
| `POST` | `/audit-runs` | Authenticated | Triggers a fresh deterministic audit evaluation. |
| `POST` | `/corrections` | Employee | Submits a proposed correction with employee justification. |
| `POST` | `/corrections/{id}/review` | Manager / HR | Approves or rejects a pending correction with manager justification. |
| `POST` | `/submissions` | Employee | Packages and freezes submission pack (only when 0 blockers exist). |
| `GET` | `/export/payroll` | HR Admin | Generates controlled payroll export file. |
| `GET` | `/export/finance` | HR Admin | Generates controlled finance/expense export file. |
| `GET` | `/audit-ledger` | HR Admin | Retrieves cryptographic audit ledger history. |
| `GET` | `/audit-ledger/verify` | HR Admin | Validates cryptographic SHA-256 integrity of the ledger chain. |
| `POST` | `/ai/explain` | Authenticated | Returns plain-English explanation of an audit flag. |
| `POST` | `/ai/draft-correction` | Authenticated | Drafts professional correction justification text. |
| `GET` | `/ai/hr-summary` | HR Admin | Generates executive month-end readiness briefing. |

---

## 8. n8n Automation Workflows

Blueprints for automated background operations are provided in [`n8n/workflows/`](file:///c:/Users/Dell/Downloads/hr-self-audit/n8n/workflows/):

- **Workflow A: Scheduled Audit Reminders**: Runs on Day 25 and Day 28 of each month; triggers audit runs and sends non-punitive notifications to employees with outstanding blockers.
- **Workflow B: Source Ingestion Sync**: Periodically polls upstream attendance and expense feeds; checks completeness flags and triggers audits upon import completion.
- **Workflow C: Manager Review Alerts**: Sends instant Slack/email notifications to managers when employees submit time-sensitive corrections.
- **Workflow D: Dual Controlled Export**: Triggers payroll and finance export pipelines once HR sign-off is completed.
- **Workflow E: Expiring Document Notifications**: Triggers 60-day warning and 30-day blocking notifications for expiring compliance documents.

---

## 9. Verification & Test Commands

To verify the complete system across all layers:

```powershell
# 1. Run Stage 10 Evaluation & Benchmark tests
pytest backend/tests/test_stage10_evaluation.py -v

# 2. Run Comprehensive Rule Engine & Explainer tests
pytest backend/tests/test_stage8_rules.py backend/tests/test_stage9_explainers.py backend/tests/test_stage10_evaluation.py -q

# 3. Execute live Evaluation Benchmark Runner
python evaluation/evaluate_rules.py

# 4. Build Frontend Production Bundle
npm --prefix frontend run build
```
