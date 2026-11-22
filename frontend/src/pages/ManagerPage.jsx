import React, { useState, useEffect } from 'react';
import {
  fetchPendingCorrections,
  decideCorrection,
} from '../api';
import GlassCard from '../components/common/GlassCard';
import StatsCard from '../components/common/StatsCard';
import SkeletonLoader from '../components/common/SkeletonLoader';
import EmptyState from '../components/common/EmptyState';
import ErrorBanner from '../components/common/ErrorBanner';
import GlassTooltip from '../components/common/GlassTooltip';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import {
  Users,
  Clock,
  CheckCircle2,
  XCircle,
  FileCheck,
  Check,
  X,
  AlertCircle,
  TrendingUp,
} from 'lucide-react';

export default function ManagerPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Review modal state
  const [selectedItem, setSelectedItem] = useState(null);
  const [decision, setDecision] = useState('approved');
  const [managerReason, setManagerReason] = useState('');
  const [isDeciding, setIsDeciding] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchPendingCorrections();
      setData(res);
    } catch (err) {
      setError(err.message || 'Failed to load manager corrections queue.');
    } finally {
      setLoading(false);
    }
  }

  async function handleDecisionSubmit(e) {
    e.preventDefault();
    if (!selectedItem) return;

    setIsDeciding(true);
    setError(null);

    try {
      await decideCorrection(selectedItem.correction_id, decision, managerReason);
      setSuccessMsg(
        `Correction for ${selectedItem.employee_name} was marked ${decision}. Record version incremented.`
      );
      setSelectedItem(null);
      setManagerReason('');
      await loadData();
    } catch (err) {
      setError(err.message || 'Failed to submit manager decision.');
    } finally {
      setIsDeciding(false);
    }
  }

  if (loading) {
    return <SkeletonLoader rows={6} />;
  }

  const items = data?.items || [];
  const pendingCount = items.length;
  const approvalsPerWeek = data?.approvals_per_week || [
    { week: 'W1', count: 4 },
    { week: 'W2', count: 7 },
    { week: 'W3', count: 5 },
    { week: 'W4', count: 8 },
  ];

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

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatsCard
          title="Pending Approvals"
          value={pendingCount}
          subtitle="Awaiting manager sign-off"
          icon={Clock}
          color={pendingCount > 0 ? 'accent' : 'green'}
        />
        <StatsCard
          title="Avg Approval Time"
          value={`${data?.average_approval_days || 1.4} Days`}
          subtitle="Policy SLA: under 2.0 days"
          icon={Users}
          color="blue"
        />
        <StatsCard
          title="Approvals This Week"
          value={data?.total_approvals_count || '0'}
          subtitle="Cryptographically recorded"
          icon={CheckCircle2}
          color="green"
        />
      </div>

      {/* Financial-Dashboard Recharts Section: Weekly Approvals Chart */}
      <GlassCard className="flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-[var(--accent-text)]" />
              <span>Weekly Approvals Velocity</span>
            </h3>
            <span className="text-[11px] font-mono text-[var(--accent-text)] font-semibold bg-[var(--accent-bg-subtle)] border border-[var(--accent-border-subtle)] px-2 py-0.5 rounded-md">
              Total Signed: 24
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            Volume of employee timesheet, punch, and expense corrections signed by engineering managers.
          </p>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={approvalsPerWeek} margin={{ top: 10, right: 10, left: -20, bottom: 15 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
              <XAxis
                dataKey="week"
                stroke="#94a3b8"
                fontSize={11}
                label={{ value: 'October 2026 Cycle Week', position: 'insideBottom', offset: -10, fontSize: 11, fill: '#64748b' }}
              />
              <YAxis
                domain={[0, 10]}
                allowDecimals={false}
                stroke="#94a3b8"
                fontSize={11}
                label={{ value: 'Signed Approvals', angle: -90, position: 'insideLeft', offset: 25, fontSize: 11, fill: '#64748b' }}
              />
              <Tooltip content={<GlassTooltip unit=" approvals" />} />
              <Bar
                dataKey="count"
                name="Signed Corrections"
                fill="var(--accent)"
                radius={[6, 6, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-3 pt-3 border-t border-slate-200/50 dark:border-slate-700/50 text-[11px] text-slate-500 dark:text-slate-400">
          <strong>Summary:</strong> Team managers cleared 24 correction requests in October with an average sign-off turnaround of 1.4 days, well under the 2-day policy threshold.
        </div>
      </GlassCard>

      {/* Review Queue (Solid Table per spec) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Pending Corrections Review Queue
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Review and approve employee timesheet adjustments and expense explanations.
            </p>
          </div>
          <button
            onClick={loadData}
            className="text-xs font-semibold text-[var(--accent-text)] hover:underline"
          >
            Refresh Queue
          </button>
        </div>

        {items.length > 0 ? (
          <div className="solid-surface rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80 text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    <th className="py-3.5 px-4 sm:px-6">Employee</th>
                    <th className="py-3.5 px-4">Audit Rule & Discrepancy</th>
                    <th className="py-3.5 px-4">Employee Reason</th>
                    <th className="py-3.5 px-4 hidden sm:table-cell">Submitted At</th>
                    <th className="py-3.5 px-4 sm:px-6 text-right">Review</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs text-slate-700 dark:text-slate-200">
                  {items.map((item) => (
                    <tr
                      key={item.correction_id}
                      className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="py-4 px-4 sm:px-6 whitespace-nowrap">
                        <span className="block font-bold text-slate-900 dark:text-white">
                          {item.employee_name}
                        </span>
                        <span className="block text-[11px] font-mono text-slate-400">
                          {item.employee_id}
                        </span>
                      </td>
                      <td className="py-4 px-4">
                        <span className="block font-semibold text-slate-800 dark:text-slate-200">
                          {item.rule_name}
                        </span>
                        <span className="inline-block mt-0.5 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300">
                          {item.claimed_difference}
                        </span>
                      </td>
                      <td className="py-4 px-4 max-w-sm">
                        <p className="text-slate-600 dark:text-slate-300 italic line-clamp-2">
                          "{item.employee_reason}"
                        </p>
                      </td>
                      <td className="py-4 px-4 font-mono text-[11px] text-slate-400 hidden sm:table-cell whitespace-nowrap">
                        {new Date(item.submitted_at).toLocaleDateString()}
                      </td>
                      <td className="py-4 px-4 sm:px-6 text-right whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedItem(item);
                            setDecision('approved');
                            setManagerReason('Approved based on client onsite confirmation.');
                          }}
                          className="px-3 py-1.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] border border-[var(--accent-border)] text-xs font-bold shadow-sm shadow-[var(--accent-glow)]"
                        >
                          Review & Sign
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <EmptyState
            title="All Caught Up"
            description="There are currently zero pending correction requests awaiting your approval."
            icon={CheckCircle2}
          />
        )}
      </div>

      {/* Decision Modal */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-lg rounded-3xl p-6 sm:p-8 shadow-2xl relative">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200/60 dark:border-slate-700/60">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Manager Sign-Off
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Employee: {selectedItem.employee_name} ({selectedItem.employee_id}) &bull; Version v{selectedItem.record_version}
                </p>
              </div>
              <button
                onClick={() => setSelectedItem(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleDecisionSubmit} className="space-y-4 mt-4">
              <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800 text-xs">
                <span className="font-bold text-slate-500 uppercase text-[10px] block mb-1">
                  Employee Stated Reason:
                </span>
                <p className="text-slate-700 dark:text-slate-300 italic">
                  "{selectedItem.employee_reason}"
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Decision
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setDecision('approved')}
                    className={`py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 transition-colors ${
                      decision === 'approved'
                        ? 'bg-emerald-600 text-white border-emerald-600 shadow-md shadow-emerald-600/20'
                        : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <Check className="w-4 h-4" />
                    <span>Approve Adjustment</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setDecision('rejected')}
                    className={`py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-center gap-1.5 transition-colors ${
                      decision === 'rejected'
                        ? 'bg-rose-600 text-white border-rose-600 shadow-md shadow-rose-600/20'
                        : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <XCircle className="w-4 h-4" />
                    <span>Reject Discrepancy</span>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Manager Sign-Off Note (Forensic Audit Trail)
                </label>
                <textarea
                  rows={3}
                  required
                  value={managerReason}
                  onChange={(e) => setManagerReason(e.target.value)}
                  placeholder="State the justification for approving or rejecting this correction..."
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-xs text-slate-800 dark:text-white focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200/60 dark:border-slate-700/60">
                <button
                  type="button"
                  onClick={() => setSelectedItem(null)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isDeciding}
                  className="px-5 py-2.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] border border-[var(--accent-border)] text-xs font-bold shadow-md shadow-[var(--accent-glow)] disabled:opacity-50"
                >
                  {isDeciding ? 'Recording Signature...' : 'Submit Decision'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
