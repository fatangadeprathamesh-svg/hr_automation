import React, { useState, useEffect } from 'react';
import {
  fetchHRMetrics,
  fetchSubmissions,
  decideSubmission,
  createExportPack,
  fetchHrAiSummary,
} from '../api';
import GlassCard from '../components/common/GlassCard';
import StatsCard from '../components/common/StatsCard';
import StatusPill from '../components/common/StatusPill';
import SkeletonLoader from '../components/common/SkeletonLoader';
import EmptyState from '../components/common/EmptyState';
import ErrorBanner from '../components/common/ErrorBanner';
import GlassTooltip from '../components/common/GlassTooltip';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
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
  Calendar,
  Layers,
  PieChart as PieIcon,
  Flame,
  Sparkles,
} from 'lucide-react';

export default function HRPage() {
  const [selectedMonth, setSelectedMonth] = useState('2026-10');
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

  // Phase 9: AI Executive Briefing state
  const [aiSummary, setAiSummary] = useState(null);
  const [isAiSummaryLoading, setIsAiSummaryLoading] = useState(false);

  useEffect(() => {
    loadData(selectedMonth);
  }, [selectedMonth]);

  async function loadData(month) {
    setLoading(true);
    setError(null);
    try {
      const [m, s, ai] = await Promise.all([
        fetchHRMetrics(month),
        fetchSubmissions(month),
        fetchHrAiSummary(month),
      ]);
      setMetrics(m);
      setSubmissions(s);
      setAiSummary(ai);
    } catch (err) {
      setError(err.message || 'Failed to load HR compliance data.');
    } finally {
      setLoading(false);
    }
  }

  async function handleRefreshAiSummary() {
    setIsAiSummaryLoading(true);
    try {
      const ai = await fetchHrAiSummary(selectedMonth);
      setAiSummary(ai);
      setSuccessMsg(`AI Month-End Briefing updated for ${selectedMonth}.`);
    } catch (err) {
      console.warn('Failed to refresh AI summary:', err);
    } finally {
      setIsAiSummaryLoading(false);
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
      await loadData(selectedMonth);
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

  if (loading && !metrics) {
    return <SkeletonLoader rows={6} />;
  }

  const donutData = metrics?.submission_donut || [
    { name: 'Submitted', value: 24, fill: '#10B981' },
    { name: 'Pending', value: 6, fill: '#F26A21' },
  ];

  const issuesByRule = metrics?.issues_by_rule || [];
  const topRecurring = metrics?.top_recurring_issues || [];

  return (
    <div className="space-y-6">
      {/* Top Notification Alerts */}
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

      {/* Header with Month Selector Dropdown */}
      <div className="glass-panel rounded-2xl px-6 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-white">
            Company-Wide HR Audit Dashboard
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Monitoring submission completion rates, policy blockers, and payroll export readiness.
          </p>
        </div>

        {/* Month Selector */}
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-[#F26A21]" />
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            Audit Month:
          </span>
          <select
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white/90 dark:bg-slate-800/90 text-xs font-bold text-slate-800 dark:text-white focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
            aria-label="Select audit cycle month"
          >
            <option value="2026-10">October 2026 (Active Close)</option>
            <option value="2026-09">September 2026 (Archived)</option>
            <option value="2026-08">August 2026 (Archived)</option>
          </select>
        </div>
      </div>

      {/* Phase 9: AI Executive Month-End Briefing */}
      <GlassCard className="border-l-4 border-l-[#F26A21]">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-orange-100 dark:bg-orange-950/40 text-[#F26A21]">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  AI Executive Month-End Briefing ({selectedMonth})
                </h3>
                <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-2 py-0.5 rounded border border-amber-200/50">
                  AI-generated, review before use
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Automated statistical synthesis across timesheet, attendance, and expense feeds.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleRefreshAiSummary}
            disabled={isAiSummaryLoading}
            className="px-3 py-1.5 rounded-xl border border-orange-200 dark:border-orange-900/60 bg-orange-50/50 dark:bg-orange-950/20 text-[#F26A21] hover:bg-orange-100/50 text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {isAiSummaryLoading ? 'Generating...' : 'Refresh AI Briefing'}
          </button>
        </div>

        {isAiSummaryLoading ? (
          <div className="py-6 flex flex-col items-center justify-center gap-2 text-slate-400">
            <Sparkles className="w-6 h-6 text-[#F26A21] animate-spin" />
            <p className="text-xs">Generating statistical month-end analysis with AI...</p>
          </div>
        ) : (
          <div className="space-y-3 text-xs">
            <p className="text-slate-700 dark:text-slate-300 leading-relaxed bg-slate-50/70 dark:bg-slate-800/40 p-3 rounded-xl border border-slate-200/50 dark:border-slate-700/50">
              {aiSummary?.executive_summary}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
              <div className="p-3 rounded-xl bg-slate-50/50 dark:bg-slate-800/30 border border-slate-200/50 dark:border-slate-700/50">
                <span className="font-bold text-slate-800 dark:text-white block mb-1.5 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  Key Statistical Insights:
                </span>
                <ul className="space-y-1 text-slate-600 dark:text-slate-300 list-disc list-inside">
                  {aiSummary?.key_insights?.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className="p-3 rounded-xl bg-slate-50/50 dark:bg-slate-800/30 border border-slate-200/50 dark:border-slate-700/50">
                <span className="font-bold text-slate-800 dark:text-white block mb-1.5 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                  Recommended HR Actions:
                </span>
                <ul className="space-y-1 text-slate-600 dark:text-slate-300 list-disc list-inside">
                  {aiSummary?.recommended_actions?.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500 border-t border-slate-200/40 dark:border-slate-800/60">
              <span>{aiSummary?.surveillance_notice || 'Strictly statistical overview; screen monitoring, keystroke tracking, and productivity scoring are prohibited by design.'}</span>
              <span className="font-mono">Provider: {aiSummary?.provider || 'deterministic_template'}</span>
            </div>
          </div>
        )}
      </GlassCard>

      {/* 4 Financial KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Submitted vs Pending"
          value={`${metrics?.submitted_count || 24} / ${metrics?.total_employees || 30}`}
          subtitle="80.0% completion rate"
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
          subtitle="Policy SLA: under 2.5 days"
          icon={FileText}
          color="blue"
        />
      </div>

      {/* Financial-Dashboard Recharts Section: Donut + Stacked Bar */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Chart 1: Submission Donut Chart (4 cols) */}
        <GlassCard className="lg:col-span-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <PieIcon className="w-4 h-4 text-[#10B981]" />
                <span>Submission Progress</span>
              </h3>
              <span className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 font-bold">
                {Math.round(((metrics?.submitted_count || 24) / (metrics?.total_employees || 30)) * 100)}%
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">
              Ratio of locked employee submissions vs pending drafts.
            </p>
          </div>

          <div className="h-60 w-full relative flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={donutData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {donutData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill || '#F26A21'} />
                  ))}
                </Pie>
                <Tooltip content={<GlassTooltip unit=" employees" />} />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  iconType="circle"
                  formatter={(value) => (
                    <span className="text-[11px] text-slate-600 dark:text-slate-300 font-medium">{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
            {/* Center label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none pb-8">
              <span className="text-xl font-extrabold text-slate-800 dark:text-white">
                {metrics?.submitted_count || 24}/{metrics?.total_employees || 30}
              </span>
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Closed</span>
            </div>
          </div>

          <div className="mt-2 pt-3 border-t border-slate-200/50 dark:border-slate-700/50 text-[11px] text-slate-500 dark:text-slate-400">
            <strong>Summary:</strong> {metrics?.submitted_count || 24} of {metrics?.total_employees || 30} records have met the submission gate; {metrics?.pending_count || 6} draft records require resolution.
          </div>
        </GlassCard>

        {/* Chart 2: Issues-by-Rule Stacked Bar Chart (8 cols) */}
        <GlassCard className="lg:col-span-8 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-[#F26A21]" />
                <span>Issues by Policy Rule (Blockers vs Warnings)</span>
              </h3>
              <div className="flex items-center gap-2 text-[11px]">
                <span className="inline-flex items-center gap-1 font-semibold text-rose-600 dark:text-rose-400">
                  <span className="w-2 h-2 rounded-full bg-rose-500" /> Blockers (Red)
                </span>
                <span className="inline-flex items-center gap-1 font-semibold text-amber-600 dark:text-amber-400">
                  <span className="w-2 h-2 rounded-full bg-amber-500" /> Warnings (Amber)
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">
              Breakdown of non-blocking warnings versus hard payroll submission blockers.
            </p>
          </div>

          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={issuesByRule} margin={{ top: 10, right: 10, left: -20, bottom: 15 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                <XAxis
                  dataKey="rule"
                  stroke="#94a3b8"
                  fontSize={11}
                  label={{ value: 'Policy Rule Family', position: 'insideBottom', offset: -10, fontSize: 11, fill: '#64748b' }}
                />
                <YAxis
                  allowDecimals={false}
                  stroke="#94a3b8"
                  fontSize={11}
                  label={{ value: 'Flags Count', angle: -90, position: 'insideLeft', offset: 25, fontSize: 11, fill: '#64748b' }}
                />
                <Tooltip content={<GlassTooltip />} />
                <Bar dataKey="blockers" name="Hard Blockers" fill="#EF4444" stackId="a" />
                <Bar dataKey="warnings" name="Warnings" fill="#F59E0B" stackId="a" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-2 pt-3 border-t border-slate-200/50 dark:border-slate-700/50 text-[11px] text-slate-500 dark:text-slate-400">
            <strong>Summary:</strong> Missing punches and timesheet hour discrepancies represent the primary sources of payroll blocking flags.
          </div>
        </GlassCard>
      </div>

      {/* Top 5 Recurring Issues Card */}
      <GlassCard>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Flame className="w-4 h-4 text-[#F26A21]" />
            <span>Top 5 Recurring Policy Exceptions ({selectedMonth})</span>
          </h3>
          <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
            Aggregated across 30 employees
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {topRecurring.map((issue) => (
            <div
              key={issue.rank}
              className="p-3 rounded-xl bg-white/50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="w-5 h-5 rounded-full bg-orange-100 dark:bg-orange-950/60 text-[#F26A21] flex items-center justify-center font-bold text-[10px]">
                    #{issue.rank}
                  </span>
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      issue.impact === 'High'
                        ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300'
                        : 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                    }`}
                  >
                    {issue.impact}
                  </span>
                </div>
                <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 line-clamp-2">
                  {issue.rule}
                </h4>
              </div>
              <span className="mt-2 text-[11px] font-mono text-slate-500 dark:text-slate-400">
                {issue.frequency} instances
              </span>
            </div>
          ))}
        </div>
      </GlassCard>

      {/* Submissions Queue (Solid Table per spec) */}
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
            onClick={() => loadData(selectedMonth)}
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
            description={`No employee snapshot packs have been frozen for the ${selectedMonth} cycle yet.`}
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
