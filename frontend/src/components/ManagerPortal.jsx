import React, { useState, useEffect } from 'react';
import { fetchPendingCorrections, decideCorrection } from '../api';
import DiffViewer from './DiffViewer';

export default function ManagerPortal({ persona, token, onStateChange }) {
  const [corrections, setCorrections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [decisionModal, setDecisionModal] = useState(null);
  const [managerReason, setManagerReason] = useState('');
  const [deciding, setDeciding] = useState(false);

  useEffect(() => {
    loadPending();
  }, [persona, token]);

  async function loadPending() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPendingCorrections(token, persona);
      setCorrections(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleDecision(decision) {
    if (!decisionModal) return;
    if (!managerReason.trim()) {
      alert("Manager review requires a mandatory decision reason.");
      return;
    }
    setDeciding(true);
    try {
      await decideCorrection(decisionModal.correction_id, decision, managerReason, token, persona);
      setDecisionModal(null);
      setManagerReason('');
      await loadPending();
      if (onStateChange) onStateChange();
    } catch (err) {
      alert(`Decision rejected: ${err.message}`);
    } finally {
      setDeciding(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500">
        <span className="animate-pulse">Loading assigned manager review queue...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-red-700">
        <h3 className="font-semibold">Unable to load review requests</h3>
        <p className="text-sm mt-1">{error}</p>
        <button
          onClick={loadPending}
          className="mt-3 px-4 py-1.5 bg-red-600 text-white rounded text-sm hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Manager Correction Approvals</h2>
          <p className="text-sm text-slate-500">
            Review side-by-side evidence, version bindings, and authorize employee month-end adjustments.
          </p>
        </div>
        <div className="text-right">
          <span className="text-xs font-semibold px-3 py-1 bg-brand-50 text-brand-700 rounded-full border border-brand-200">
            {corrections.length} Pending Review
          </span>
        </div>
      </div>

      {corrections.length === 0 ? (
        <div className="bg-white p-12 rounded-xl border border-slate-200 text-center text-slate-500">
          <div className="text-3xl mb-2">✓</div>
          <div className="font-semibold">All caught up!</div>
          <div className="text-xs text-slate-400 mt-1">No pending employee corrections requiring your decision.</div>
        </div>
      ) : (
        <div className="space-y-4">
          {corrections.map((item) => (
            <div key={item.correction_id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between pb-3 border-b border-slate-100 gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-800 text-sm">Employee: {item.employee_id}</span>
                    <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded font-mono">
                      Target: {item.entity_name} ({item.entity_id})
                    </span>
                    <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-800 rounded font-semibold uppercase">
                      {item.status}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    Submitted on {new Date(item.requested_at).toLocaleString()} | Bound Version: v{item.original_record_version}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setDecisionModal(item);
                      setManagerReason('');
                    }}
                    className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded text-xs font-bold transition shadow-sm"
                  >
                    Review & Decide
                  </button>
                </div>
              </div>

              {/* Employee Reason Callout */}
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
                <span className="font-semibold text-slate-700">Employee Explanation: </span>
                <span className="text-slate-600 italic">"{item.employee_reason}"</span>
              </div>

              {/* Side-by-Side Diff Inspector */}
              <DiffViewer
                originalData={item.original_data}
                proposedData={item.proposed_data}
                recordVersion={item.original_record_version}
              />
            </div>
          ))}
        </div>
      )}

      {/* Decision Modal */}
      {decisionModal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="font-bold text-slate-800">
                Authorize Correction for {decisionModal.employee_id}
              </h3>
              <button
                onClick={() => setDecisionModal(null)}
                className="text-slate-400 hover:text-slate-600 text-lg"
              >
                &times;
              </button>
            </div>

            <div className="text-xs text-slate-600 space-y-2">
              <p>
                Target Entity: <span className="font-mono font-bold text-slate-800">{decisionModal.entity_name}</span> (ID: {decisionModal.entity_id})
              </p>
              <p>
                Bound Version: <span className="font-mono font-bold text-brand-600">v{decisionModal.original_record_version}</span>
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Manager Justification & Reason (Mandatory audit trail)
              </label>
              <textarea
                required
                rows={3}
                placeholder="State your reason for approving or rejecting this correction..."
                value={managerReason}
                onChange={(e) => setManagerReason(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded px-3 py-2 focus:ring-2 focus:ring-brand-500 outline-none"
              />
            </div>

            <div className="p-2.5 bg-blue-50 border border-blue-200 rounded text-[11px] text-blue-800">
              Upon approval, the system will atomically increment the record version to v{decisionModal.original_record_version + 1} and execute an automated re-audit.
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setDecisionModal(null)}
                className="px-4 py-2 border border-slate-300 rounded text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deciding}
                onClick={() => handleDecision("rejected")}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded text-xs font-bold transition disabled:opacity-50"
              >
                {deciding ? "Saving..." : "Reject Correction"}
              </button>
              <button
                type="button"
                disabled={deciding}
                onClick={() => handleDecision("approved")}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-bold transition disabled:opacity-50"
              >
                {deciding ? "Saving..." : "Approve & Re-Audit"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
