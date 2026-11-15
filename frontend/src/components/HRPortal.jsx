import React, { useState, useEffect } from 'react';
import {
  triggerAudit,
  fetchSubmissions,
  decideSubmission,
  createExportPack,
  fetchExportRuns,
  getDownloadUrl,
} from '../api';

export default function HRPortal({ persona, token }) {
  const [targetEmp, setTargetEmp] = useState('EMP001');
  const [period, setPeriod] = useState('2026-10');
  const [auditResult, setAuditResult] = useState(null);
  const [loadingAudit, setLoadingAudit] = useState(false);

  const [submissions, setSubmissions] = useState([]);
  const [exportRuns, setExportRuns] = useState([]);
  const [loadingData, setLoadingData] = useState(true);

  // Return decision modal state
  const [returnModal, setReturnModal] = useState(null);
  const [returnReason, setReturnReason] = useState('');
  const [returnOwner, setReturnOwner] = useState('EMP001');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    loadHRData();
  }, [persona, token]);

  async function loadHRData() {
    setLoadingData(true);
    try {
      const [subs, exps] = await Promise.all([
        fetchSubmissions(null, token, persona).catch(() => []),
        fetchExportRuns(token, persona).catch(() => []),
      ]);
      setSubmissions(subs || []);
      setExportRuns(exps || []);
    } catch (err) {
      console.error("Failed to load HR portal data:", err);
    } finally {
      setLoadingData(false);
    }
  }

  async function handleRunAudit() {
    setLoadingAudit(true);
    setAuditResult(null);
    try {
      const res = await triggerAudit(targetEmp, period, token, persona);
      setAuditResult(res);
    } catch (err) {
      alert(`Audit run failed: ${err.message}`);
    } finally {
      setLoadingAudit(false);
    }
  }

  async function handleApproveSubmission(snapshotId) {
    if (!window.confirm("Approve this month-end submission pack for payroll export?")) return;
    setActionLoading(true);
    try {
      await decideSubmission(snapshotId, "approved", "All compliance checks verified.", null, token, persona);
      await loadHRData();
      alert("Submission approved!");
    } catch (err) {
      alert(`Approval failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleConfirmReturn(e) {
    e.preventDefault();
    if (!returnModal || !returnReason.trim()) return;
    setActionLoading(true);
    try {
      await decideSubmission(returnModal.snapshot_id, "returned", returnReason, returnOwner, token, persona);
      setReturnModal(null);
      setReturnReason('');
      await loadHRData();
      alert("Submission returned with remediation reason.");
    } catch (err) {
      alert(`Return action failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleGenerateExport(snapshotId) {
    setActionLoading(true);
    try {
      const exp = await createExportPack(snapshotId, "PDF_JSON_PACK", token, persona);
      alert(`Audit pack export generated successfully!\nExport ID: ${exp.export_run_id}`);
      await loadHRData();
    } catch (err) {
      alert(`Export generation failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">HR Compliance & Audit Control</h2>
          <p className="text-sm text-slate-500">
            Execute batch deterministic audit runs, review submitted packs, and generate dual PDF/JSON payroll exports.
          </p>
        </div>
        <button
          onClick={loadHRData}
          disabled={loadingData}
          className="px-3 py-1.5 border border-slate-300 rounded text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          {loadingData ? "Refreshing..." : "Refresh Queue"}
        </button>
      </div>

      {/* Manual Audit Run Trigger */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <h3 className="font-semibold text-slate-800 text-sm">Trigger Deterministic Audit Run</h3>
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1">Target Employee ID</label>
            <input
              type="text"
              value={targetEmp}
              onChange={(e) => setTargetEmp(e.target.value)}
              className="text-xs font-mono border border-slate-300 rounded px-3 py-1.5 focus:ring-2 focus:ring-brand-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 mb-1">Period (YYYY-MM)</label>
            <input
              type="text"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="text-xs font-mono border border-slate-300 rounded px-3 py-1.5 focus:ring-2 focus:ring-brand-500 outline-none"
            />
          </div>
          <div className="pt-5">
            <button
              onClick={handleRunAudit}
              disabled={loadingAudit}
              className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded text-xs font-bold transition disabled:opacity-50"
            >
              {loadingAudit ? "Running Rules..." : "Execute Audit Run"}
            </button>
          </div>
        </div>

        {auditResult && (
          <div className="mt-4 p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-slate-700">
                Audit Run: {auditResult.audit_run_id}
              </span>
              <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                auditResult.submission_allowed ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
              }`}>
                {auditResult.submission_allowed ? "SUBMISSION ALLOWED" : "SUBMISSION BLOCKED"}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="p-2 bg-white rounded border">
                <span className="text-slate-400">Policy: </span>
                <span className="font-semibold">{auditResult.policy_version}</span>
              </div>
              <div className="p-2 bg-white rounded border">
                <span className="text-slate-400">Blockers: </span>
                <span className="font-bold text-rose-600">{auditResult.blocking_count}</span>
              </div>
              <div className="p-2 bg-white rounded border">
                <span className="text-slate-400">Data Health: </span>
                <span className="font-semibold">{auditResult.data_health}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Submitted Month-End Packs for Review */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
          <div>
            <h3 className="font-semibold text-slate-800 text-sm">Submitted Month-End Packs ({submissions.length})</h3>
            <p className="text-xs text-slate-500">Review atomic frozen snapshots submitted by employees.</p>
          </div>
        </div>

        {submissions.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            No month-end packs submitted yet for review.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {submissions.map((sub) => (
              <div key={sub.snapshot_id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-800 text-sm">Employee: {sub.employee_id}</span>
                    <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-700 rounded font-mono">
                      Period: {sub.period}
                    </span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      sub.status === 'approved' ? 'bg-emerald-100 text-emerald-800' :
                      sub.status === 'returned' ? 'bg-rose-100 text-rose-800' : 'bg-blue-100 text-blue-800'
                    }`}>
                      {sub.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500">
                    Snapshot ID: <span className="font-mono text-slate-700">{sub.snapshot_id}</span> | Submitted: {new Date(sub.submitted_at).toLocaleString()}
                  </div>
                  {sub.hr_return_reason && (
                    <div className="text-xs text-rose-700 bg-rose-50 p-2 rounded">
                      Return Note: {sub.hr_return_reason}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {sub.status === 'submitted' && (
                    <>
                      <button
                        onClick={() => {
                          setReturnModal(sub);
                          setReturnReason('');
                          setReturnOwner(sub.employee_id);
                        }}
                        disabled={actionLoading}
                        className="px-3 py-1.5 border border-rose-300 text-rose-700 hover:bg-rose-50 rounded text-xs font-semibold transition"
                      >
                        Return with Reason
                      </button>
                      <button
                        onClick={() => handleApproveSubmission(sub.snapshot_id)}
                        disabled={actionLoading}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-bold transition"
                      >
                        Approve Pack
                      </button>
                    </>
                  )}

                  {sub.status === 'approved' && (
                    <button
                      onClick={() => handleGenerateExport(sub.snapshot_id)}
                      disabled={actionLoading}
                      className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded text-xs font-bold transition"
                    >
                      Generate PDF + JSON Export
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Generated Payroll Export Runs */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50">
          <h3 className="font-semibold text-slate-800 text-sm">Generated Dual Export Packs ({exportRuns.length})</h3>
          <p className="text-xs text-slate-500">Dual export parity: Human-readable PDF report and canonical JSON dataset.</p>
        </div>

        {exportRuns.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            No export packs generated yet. Approve a submitted pack above to generate exports.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {exportRuns.map((exp) => (
              <div key={exp.export_run_id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-800 text-sm font-mono">Run: {exp.export_run_id.slice(0, 8)}</span>
                    <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded">
                      Dest: {exp.destination_system}
                    </span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      exp.status === 'delivered' ? 'bg-emerald-100 text-emerald-800' : 'bg-blue-100 text-blue-800'
                    }`}>
                      {exp.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 font-mono truncate max-w-xl">
                    PDF: {exp.pack_pdf_uri}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <a
                    href={getDownloadUrl(exp.export_run_id, "pdf")}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded text-xs font-bold transition inline-flex items-center gap-1 shadow-sm"
                  >
                    Download PDF
                  </a>
                  <a
                    href={getDownloadUrl(exp.export_run_id, "json")}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded text-xs font-bold transition inline-flex items-center gap-1 shadow-sm"
                  >
                    View JSON
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Return Decision Modal */}
      {returnModal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="font-bold text-slate-800">Return Month-End Pack to Employee</h3>
              <button
                onClick={() => setReturnModal(null)}
                className="text-slate-400 hover:text-slate-600 text-lg"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleConfirmReturn} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Target Snapshot</label>
                <input
                  type="text"
                  disabled
                  value={returnModal.snapshot_id}
                  className="w-full text-xs font-mono bg-slate-100 border border-slate-300 rounded px-3 py-2 text-slate-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Assigned Remediation Owner</label>
                <input
                  type="text"
                  required
                  value={returnOwner}
                  onChange={(e) => setReturnOwner(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded px-3 py-2 focus:ring-2 focus:ring-brand-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Return Reason / Required Remediation</label>
                <textarea
                  required
                  rows={3}
                  placeholder="Explain what needs to be fixed before this pack can be approved for payroll..."
                  value={returnReason}
                  onChange={(e) => setReturnReason(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded px-3 py-2 focus:ring-2 focus:ring-brand-500 outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setReturnModal(null)}
                  className="px-4 py-2 border border-slate-300 rounded text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded text-xs font-bold transition disabled:opacity-50"
                >
                  {actionLoading ? "Returning..." : "Return to Owner"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
