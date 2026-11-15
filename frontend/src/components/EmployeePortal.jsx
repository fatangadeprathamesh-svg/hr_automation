import React, { useState, useEffect } from 'react';
import { fetchReadiness, submitCorrection, submitMonthEnd, fetchSubmissions, fetchPendingCorrections } from '../api';

export default function EmployeePortal({ persona, token, onStateChange }) {
  const [readiness, setReadiness] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [pendingCorrections, setPendingCorrections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFlag, setSelectedFlag] = useState(null);
  const [correctionForm, setCorrectionForm] = useState({
    proposedValue: '',
    fieldName: 'clock_out',
    reason: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [submittingMonthEnd, setSubmittingMonthEnd] = useState(false);

  useEffect(() => {
    loadAllData();
  }, [persona, token]);

  async function loadAllData() {
    setLoading(true);
    setError(null);
    try {
      const [rData, subData, corrData] = await Promise.all([
        fetchReadiness('2026-10', token, persona),
        fetchSubmissions('2026-10', token, persona).catch(() => []),
        fetchPendingCorrections(token, persona).catch(() => []),
      ]);
      setReadiness(rData);
      setSubmissions(subData || []);
      setPendingCorrections(corrData || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleOpenCorrection(flag) {
    setSelectedFlag(flag);
    const defaultField = flag.evidence?.missing === 'clock_in' ? 'clock_in' : 'clock_out';
    let placeholder = '';
    if (flag.rule_id === 'MISSING_PUNCH') {
      placeholder = `${flag.evidence?.work_date || '2026-10-02'}T17:30:00-04:00`;
    } else if (flag.rule_id === 'MISSING_RECEIPT') {
      placeholder = 's3://hr-receipts/receipt.pdf';
    } else {
      placeholder = '8.0';
    }
    setCorrectionForm({
      proposedValue: '',
      fieldName: defaultField,
      reason: '',
      placeholder,
    });
  }

  async function handleCorrectionSubmit(e) {
    e.preventDefault();
    if (!selectedFlag) return;
    setSubmitting(true);
    try {
      const entityId = selectedFlag.evidence?.entity_id || selectedFlag.evidence?.record_id || selectedFlag.flag_id;
      let entityName = "attendance";
      if (selectedFlag.rule_id === "MISSING_RECEIPT") entityName = "expense_claim";
      if (selectedFlag.rule_id === "HOURS_MISMATCH") entityName = "timesheet";

      let proposedData = {};
      if (entityName === "attendance") {
        proposedData[correctionForm.fieldName] = correctionForm.proposedValue;
      } else if (entityName === "expense_claim") {
        proposedData["receipt_reference"] = correctionForm.proposedValue;
      } else {
        proposedData["regular_hours"] = parseFloat(correctionForm.proposedValue);
      }

      await submitCorrection({
        flag_id: selectedFlag.flag_id,
        entity_name: entityName,
        entity_id: entityId,
        proposed_data: proposedData,
        employee_reason: correctionForm.reason,
      }, token, persona);

      setSelectedFlag(null);
      setCorrectionForm({ proposedValue: '', fieldName: 'clock_out', reason: '' });
      await loadAllData();
      if (onStateChange) onStateChange();
    } catch (err) {
      alert(`Submission failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmitMonthEnd() {
    if (!window.confirm("Submit your verified month-end self-audit and freeze audit snapshot?")) return;
    setSubmittingMonthEnd(true);
    try {
      const res = await submitMonthEnd(readiness.period, token, persona);
      alert(`Month-end pack submitted successfully!\nSnapshot ID: ${res.snapshot_id}`);
      await loadAllData();
      if (onStateChange) onStateChange();
    } catch (err) {
      alert(`Submission failed: ${err.message}`);
    } finally {
      setSubmittingMonthEnd(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500">
        <span className="animate-pulse">Loading employee self-audit readiness...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-red-700">
        <h3 className="font-semibold">Unable to load readiness data</h3>
        <p className="text-sm mt-1">{error}</p>
        <button
          onClick={loadAllData}
          className="mt-3 px-4 py-1.5 bg-red-600 text-white rounded text-sm hover:bg-red-700 font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  const latestSubmission = submissions.length > 0 ? submissions[0] : null;

  return (
    <div className="space-y-6">
      {/* Top Banner: Readiness & Submission Eligibility */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xl font-bold text-slate-900">Month-End Audit Readiness</h2>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-slate-100 text-slate-700">
                Period: {readiness.period}
              </span>
              <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                readiness.data_health === 'complete' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
              }`}>
                Data Health: {readiness.data_health.toUpperCase()}
              </span>
              {latestSubmission && (
                <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-blue-100 text-blue-800">
                  Pack Status: {latestSubmission.status.toUpperCase()}
                </span>
              )}
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Deterministic verification of punch records, timesheets, and expense claims.
            </p>
          </div>

          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className="text-xs text-slate-400 uppercase font-semibold">Readiness Score</div>
              <div className="text-3xl font-extrabold text-brand-600">{readiness.readiness_score}%</div>
              <div className="text-[10px] text-slate-400">Informational only</div>
            </div>

            <div className="flex flex-col items-end gap-2">
              <div className={`px-4 py-2 rounded-lg text-sm font-semibold border ${
                readiness.submission_allowed
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                  : 'bg-rose-50 border-rose-300 text-rose-800'
              }`}>
                {readiness.submission_allowed ? 'SUBMISSION ALLOWED' : 'SUBMISSION BLOCKED'}
              </div>

              {readiness.submission_allowed && (!latestSubmission || latestSubmission.status === 'returned') && (
                <button
                  onClick={handleSubmitMonthEnd}
                  disabled={submittingMonthEnd}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition shadow-sm disabled:opacity-50"
                >
                  {submittingMonthEnd ? "Freezing..." : "Submit Month-End Self-Audit"}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Informational Readiness Formula Alert */}
        <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded text-xs text-slate-600 flex flex-wrap items-center justify-between gap-2">
          <span>{readiness.readiness_formula}</span>
          <span className="font-semibold text-rose-600">Blockers: {readiness.blocking_count}</span>
        </div>

        {/* If submission exists, show summary */}
        {latestSubmission && (
          <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs flex justify-between items-center text-blue-900">
            <div>
              <span className="font-bold">Latest Snapshot: </span>
              <span className="font-mono">{latestSubmission.snapshot_id}</span>
              <span className="ml-3 text-blue-700">Submitted at {new Date(latestSubmission.submitted_at).toLocaleString()}</span>
            </div>
            {latestSubmission.hr_return_reason && (
              <span className="text-rose-700 font-semibold">Return note: {latestSubmission.hr_return_reason}</span>
            )}
          </div>
        )}
      </div>

      {/* Source Coverage Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {Object.entries(readiness.source_coverage || {}).map(([source, status]) => (
          <div key={source} className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
            <div className="text-[11px] text-slate-400 uppercase font-medium">{source}</div>
            <div className="flex items-center gap-1.5 mt-1">
              <span className={`w-2 h-2 rounded-full ${status === 'complete' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              <span className="text-xs font-semibold text-slate-700 capitalize">{status}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Actionable Flags List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
          <div>
            <h3 className="font-semibold text-slate-800">Actionable Audit Flags</h3>
            <p className="text-xs text-slate-500">Items requiring employee explanation or correction.</p>
          </div>
          <span className="text-xs font-bold px-2 py-1 bg-rose-100 text-rose-800 rounded">
            {readiness.blocking_count} Blocking Issues
          </span>
        </div>

        {readiness.blocking_issues.length === 0 && readiness.warnings.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-sm">
            All deterministic audit rules passed! Your month-end self-audit is complete.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {[...readiness.blocking_issues, ...readiness.warnings].map((flag) => {
              const pendingCorr = pendingCorrections.find(
                (c) => c.flag_id === flag.flag_id || c.entity_id === flag.evidence?.record_id || c.entity_id === flag.evidence?.entity_id
              );

              return (
                <div key={flag.flag_id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                        flag.severity === 'blocking' ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700'
                      }`}>
                        {flag.severity.toUpperCase()}
                      </span>
                      <span className="font-mono text-xs font-semibold text-slate-800">{flag.rule_id}</span>
                      <span className="text-xs text-slate-400">Policy: {flag.policy_version}</span>
                      {pendingCorr && (
                        <span className="text-[10px] font-bold px-2 py-0.5 bg-amber-100 text-amber-800 rounded">
                          CORRECTION PENDING REVIEW
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-700">{flag.suggested_action || "Review evidence and submit correction."}</p>
                    <div className="text-xs font-mono text-slate-500 bg-slate-100 p-2 rounded max-w-xl">
                      {JSON.stringify(flag.evidence, null, 2)}
                    </div>
                  </div>

                  <div>
                    {pendingCorr ? (
                      <span className="text-xs font-medium text-amber-600 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-lg inline-block">
                        Awaiting Manager Decision
                      </span>
                    ) : (
                      <button
                        onClick={() => handleOpenCorrection(flag)}
                        className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded text-xs font-semibold shrink-0 transition"
                      >
                        Submit Correction
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Correction Modal */}
      {selectedFlag && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="font-bold text-slate-800">Submit Correction for {selectedFlag.rule_id}</h3>
              <button
                onClick={() => setSelectedFlag(null)}
                className="text-slate-400 hover:text-slate-600 text-lg"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCorrectionSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Target Record ID</label>
                <input
                  type="text"
                  disabled
                  value={selectedFlag.evidence?.record_id || selectedFlag.evidence?.entity_id || "RECORD_REF"}
                  className="w-full text-xs font-mono bg-slate-100 border border-slate-300 rounded px-3 py-2 text-slate-600"
                />
              </div>

              {selectedFlag.rule_id === 'MISSING_PUNCH' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Punch Field to Correct</label>
                  <select
                    value={correctionForm.fieldName}
                    onChange={(e) => setCorrectionForm({ ...correctionForm, fieldName: e.target.value })}
                    className="w-full text-xs border border-slate-300 rounded px-3 py-2 bg-white"
                  >
                    <option value="clock_out">Clock Out</option>
                    <option value="clock_in">Clock In</option>
                  </select>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Proposed Value ({selectedFlag.rule_id === 'MISSING_RECEIPT' ? 'Receipt URI' : selectedFlag.rule_id === 'HOURS_MISMATCH' ? 'Hours' : 'ISO Timestamp or Time HH:MM:SS'})
                </label>
                <input
                  type="text"
                  required
                  placeholder={correctionForm.placeholder || "2026-10-02T17:30:00-04:00 or 17:30:00"}
                  value={correctionForm.proposedValue}
                  onChange={(e) => setCorrectionForm({ ...correctionForm, proposedValue: e.target.value })}
                  className="w-full text-xs font-mono border border-slate-300 rounded px-3 py-2 focus:ring-2 focus:ring-brand-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Employee Explanation / Justification</label>
                <textarea
                  required
                  rows={3}
                  placeholder="Explain why this punch or expense requires correction..."
                  value={correctionForm.reason}
                  onChange={(e) => setCorrectionForm({ ...correctionForm, reason: e.target.value })}
                  className="w-full text-xs border border-slate-300 rounded px-3 py-2 focus:ring-2 focus:ring-brand-500 outline-none"
                />
              </div>

              <div className="p-2.5 bg-amber-50 border border-amber-200 rounded text-[11px] text-amber-800">
                Notice: This correction will be bound to the record's current version and routed to your assigned manager for formal authorization.
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedFlag(null)}
                  className="px-4 py-2 border border-slate-300 rounded text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded text-xs font-bold transition disabled:opacity-50"
                >
                  {submitting ? "Submitting..." : "Send to Manager"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
