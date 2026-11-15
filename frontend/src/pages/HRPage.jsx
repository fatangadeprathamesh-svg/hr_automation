import React, { useState, useEffect } from 'react';
import {
  fetchHRMetrics,
  fetchSubmissions,
  decideSubmission,
  createExportPack,
} from '../api';
import GlassCard from '../components/common/GlassCard';
import StatsCard from '../components/common/StatsCard';
import StatusPill from '../components/common/StatusPill';
import SkeletonLoader from '../components/common/SkeletonLoader';
import EmptyState from '../components/common/EmptyState';
import ErrorBanner from '../components/common/ErrorBanner';
import {
  ShieldCheck,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Download,
  FileText,
  X,
  Check,
  RotateCcw,
} from 'lucide-react';

export default function HRPage() {
  const [metrics, setMetrics] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Review modal state
  const [selectedSub, setSelectedSub] = useState(null);
  const [hrDecision, setHrDecision] = useState('approved');
  const [hrReason, setHrReason] = useState('');
  const [assignedOwner, setAssignedOwner] = useState('EMPLOYEE');
  const [isDeciding, setIsDeciding] = useState(false);

  // Export action state
  const [exportingId, setExportingId] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [m, s] = await Promise.all([
        fetchHRMetrics('2026-10'),
        fetchSubmissions('2026-10'),
      ]);
      setMetrics(m);
      setSubmissions(s);
    } catch (err) {
      setError(err.message || 'Failed to load HR compliance data.');
    } finally {
      setLoading(false);
    }
  }

  async function handleHrDecisionSubmit(e) {
    e.preventDefault();
    if (!selectedSub) return;

    setIsDeciding(true);
    setError(null);

    try {
      await decideSubmission(
        selectedSub.snapshot_id,
        hrDecision,
        hrReason,
        assignedOwner
      );
      setSuccessMsg(
        `Submission for ${selectedSub.employee_name} was marked ${hrDecision}.`
      );
      setSelectedSub(null);
      setHrReason('');
      await loadData();
    } catch (err) {
      setError(err.message || 'Failed to record HR decision.');
    } finally {
      setIsDeciding(false);
    }
  }

  async function handleExport(snapshotId) {
    setExportingId(snapshotId);
    setError(null);
    try {
      const res = await createExportPack(snapshotId);
      setSuccessMsg(`Export Pack Generated! Stored as frozen dual PDF & JSON package.`);
    } catch (err) {
      setError(err.message || 'Export generation failed.');
    } finally {
      setExportingId(null);
    }
  }

  if (loading) {
    return <SkeletonLoader rows={6} />;
  }

  return (
    <div className="space-y-6">
      {/* Notifications */}
      <ErrorBanner message={error} onDismiss={() => setError(null)} />
      {successMsg && (
        <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40 p-4 flex items-center justify-between text-emerald-800 dark:text-emerald-200 text-xs font-semibold">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)}>
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Submission Progress"
          value={`${metrics?.submitted_count || 24} / ${metrics?.total_employees || 30}`}
          subtitle="80% submission rate"
          icon={ShieldCheck}
          color="green"
        />
        <StatsCard
          title="Open Blockers"
          value={metrics?.open_blockers || 4}
          subtitle="Across 30 active employees"
          icon={AlertTriangle}
          color={metrics?.open_blockers > 0 ? 'red' : 'green'}
        />
        <StatsCard
          title="Average Readiness"
          value={`${metrics?.average_readiness || 91.2}%`}
          subtitle="Goal: above 95.0%"
          icon={Clock}
          color="accent"
        />
        <StatsCard
          title="Avg Time to Resolve"
          value={`${metrics?.average_resolve_days || 1.8} Days`}
          subtitle="Target: under 2.5 days"
          icon={FileText}
          color="blue"
        />
      </div>

      {/* Submissions Queue (Solid Table) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Month-End Submission Packs (Frozen Snapshots)
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Immutable snapshots locked at submission gate. Review or export to payroll staging.
            </p>
          </div>
          <button
            onClick={loadData}
            className="text-xs font-semibold text-[#F26A21] hover:underline"
          >
            Refresh Submissions
          </button>
        </div>

        {submissions.length > 0 ? (
          <div className="solid-surface rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80 text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    <th className="py-3.5 px-4 sm:px-6">Status</th>
                    <th className="py-3.5 px-4">Employee</th>
                    <th className="py-3.5 px-4">Snapshot ID & Policy</th>
                    <th className="py-3.5 px-4 hidden sm:table-cell">Submitted At</th>
                    <th className="py-3.5 px-4 sm:px-6 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs text-slate-700 dark:text-slate-200">
                  {submissions.map((sub) => (
                    <tr
                      key={sub.snapshot_id}
                      className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="py-4 px-4 sm:px-6 whitespace-nowrap">
                        <StatusPill status={sub.status} size="sm" />
                      </td>
                      <td className="py-4 px-4 whitespace-nowrap">
                        <span className="block font-bold text-slate-900 dark:text-white">
                          {sub.employee_name}
                        </span>
                        <span className="block text-[11px] text-slate-400">
                          {sub.department} &bull; {sub.employee_id}
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <span className="block font-mono text-[11px] text-slate-700 dark:text-slate-300 font-semibold">
                          {sub.snapshot_id}
                        </span>
                        <span className="block text-[10px] text-slate-400">
                          Policy: {sub.policy_version}
                        </span>
                      </td>
                      <td className="py-4 px-4 font-mono text-[11px] text-slate-400 hidden sm:table-cell whitespace-nowrap">
                        {new Date(sub.submitted_at).toLocaleDateString()}
                      </td>
                      <td className="py-4 px-4 sm:px-6 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2">
                          {sub.status === 'submitted' && (
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedSub(sub);
                                setHrDecision('approved');
                                setHrReason('Approved for final payroll export.');
                              }}
                              className="px-3 py-1.5 rounded-xl bg-[#F26A21] hover:bg-[#dc5612] text-white text-xs font-bold shadow-sm shadow-orange-500/20"
                            >
                              HR Review
                            </button>
                          )}
                          <button
                            type="button"
                            disabled={exportingId === sub.snapshot_id}
                            onClick={() => handleExport(sub.snapshot_id)}
                            className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:border-[#F26A21] hover:text-[#F26A21] text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                          >
                            <Download className="w-3.5 h-3.5" />
                            <span>{exportingId === sub.snapshot_id ? 'Exporting...' : 'Dual Export'}</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <EmptyState
            title="Zero Submissions"
            description="No employee snapshot packs have been frozen for the October 2026 cycle yet."
          />
        )}
      </div>

      {/* HR Review Decision Modal */}
      {selectedSub && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-lg rounded-3xl p-6 sm:p-8 shadow-2xl relative">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200/60 dark:border-slate-700/60">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  HR Review & Sign-Off
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Snapshot: {selectedSub.snapshot_id} &bull; {selectedSub.employee_name}
                </p>
              </div>
              <button
                onClick={() => setSelectedSub(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleHrDecisionSubmit} className="space-y-4 mt-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  HR Decision
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setHrDecision('approved')}
                    className={`py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 transition-colors ${
                      hrDecision === 'approved'
                        ? 'bg-emerald-600 text-white border-emerald-600 shadow-md shadow-emerald-600/20'
                        : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <Check className="w-4 h-4" />
                    <span>Approve for Export</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setHrDecision('returned')}
                    className={`py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 transition-colors ${
                      hrDecision === 'returned'
                        ? 'bg-amber-600 text-white border-amber-600 shadow-md shadow-amber-600/20'
                        : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <RotateCcw className="w-4 h-4" />
                    <span>Return for Correction</span>
                  </button>
                </div>
              </div>

              {hrDecision === 'returned' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Assign Responsibility To
                  </label>
                  <select
                    value={assignedOwner}
                    onChange={(e) => setAssignedOwner(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-xs text-slate-800 dark:text-white"
                  >
                    <option value="EMPLOYEE">Employee (e.g. upload missing tax receipt)</option>
                    <option value="MANAGER">Manager (e.g. approve overtime authorization)</option>
                    <option value="PAYROLL">Payroll Operations</option>
                  </select>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  HR Review Justification Note
                </label>
                <textarea
                  rows={3}
                  required
                  value={hrReason}
                  onChange={(e) => setHrReason(e.target.value)}
                  placeholder="State the audit justification or specific required correction..."
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-xs text-slate-800 dark:text-white focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200/60 dark:border-slate-700/60">
                <button
                  type="button"
                  onClick={() => setSelectedSub(null)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isDeciding}
                  className="px-5 py-2.5 rounded-xl bg-[#F26A21] hover:bg-[#dc5612] text-white text-xs font-bold shadow-md shadow-orange-500/20 disabled:opacity-50"
                >
                  {isDeciding ? 'Saving Decision...' : 'Confirm Decision'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
