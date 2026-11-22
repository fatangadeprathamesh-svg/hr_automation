import React, { useState, useEffect } from 'react';
import {
  fetchReadiness,
  submitCorrection,
  submitMonthEnd,
  resolveAllBlockersDemo,
  resetFlagsDemo,
  explainFlagAI,
  draftCorrectionAI,
} from '../api';
import GlassCard from '../components/common/GlassCard';
import ReadinessRing from '../components/common/ReadinessRing';
import StatsCard from '../components/common/StatsCard';
import FlagsTable from '../components/common/FlagsTable';
import SkeletonLoader from '../components/common/SkeletonLoader';
import EmptyState from '../components/common/EmptyState';
import ErrorBanner from '../components/common/ErrorBanner';
import GlassTooltip from '../components/common/GlassTooltip';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Area,
} from 'recharts';
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Send,
  HelpCircle,
  X,
  Sparkles,
  RotateCcw,
} from 'lucide-react';

export default function EmployeePage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Correction modal state
  const [selectedFlag, setSelectedFlag] = useState(null);
  const [proposedValue, setProposedValue] = useState('');
  const [employeeReason, setEmployeeReason] = useState('');
  const [isSubmittingCorr, setIsSubmittingCorr] = useState(false);

  // Explain AI modal state
  const [explainFlag, setExplainFlag] = useState(null);
  const [explainDetails, setExplainDetails] = useState(null);
  const [isExplainingLoading, setIsExplainingLoading] = useState(false);

  // AI Draft Assistant state
  const [aiDraftLoading, setAiDraftLoading] = useState(false);
  const [hasAiDrafted, setHasAiDrafted] = useState(false);

  // Freeze submission state
  const [isFreezing, setIsFreezing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function handleOpenExplainer(flag) {
    setExplainFlag(flag);
    setExplainDetails(null);
    setIsExplainingLoading(true);
    try {
      const details = await explainFlagAI(flag);
      setExplainDetails(details);
    } catch (e) {
      console.warn('Failed to load AI explainer:', e);
    } finally {
      setIsExplainingLoading(false);
    }
  }

  async function handleGenerateAiDraft() {
    if (!selectedFlag) return;
    setAiDraftLoading(true);
    try {
      const draft = await draftCorrectionAI(selectedFlag, employeeReason);
      if (draft.proposed_value && (!proposedValue || proposedValue.trim() === '')) {
        setProposedValue(draft.proposed_value);
      }
      if (draft.draft_reason) {
        setEmployeeReason(draft.draft_reason);
      }
      setHasAiDrafted(true);
    } catch (e) {
      console.warn('AI drafting failed:', e);
    } finally {
      setAiDraftLoading(false);
    }
  }

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchReadiness('2026-10');
      setData(res);
    } catch (err) {
      setError(err.message || 'Failed to load readiness audit.');
    } finally {
      setLoading(false);
    }
  }

  function handleDemoResolveBlockers() {
    resolveAllBlockersDemo();
    loadData();
    setSuccessMsg('Blockers resolved! Notice the circular ring smoothly animating from 78% to 100%.');
  }

  function handleDemoReset() {
    resetFlagsDemo();
    loadData();
    setSuccessMsg('Audit flags reset to baseline 78% with open blockers.');
  }

  async function handleCorrectionSubmit(e) {
    e.preventDefault();
    if (!selectedFlag) return;
    setIsSubmittingCorr(true);
    setError(null);

    try {
      await submitCorrection({
        flag_id: selectedFlag.id,
        rule_id: selectedFlag.rule_id,
        proposed_value: proposedValue,
        employee_reason: employeeReason,
        record_version: selectedFlag.record_version || 1,
      });

      setSuccessMsg(`Correction for "${selectedFlag.title}" submitted to manager for review.`);
      setSelectedFlag(null);
      setProposedValue('');
      setEmployeeReason('');
      await loadData();
    } catch (err) {
      setError(err.message || 'Failed to submit correction.');
    } finally {
      setIsSubmittingCorr(false);
    }
  }

  async function handleSubmitMonthEnd() {
    setIsFreezing(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await submitMonthEnd('2026-10');
      setSuccessMsg(res.message || 'Month-end audit successfully frozen and submitted!');
      await loadData();
    } catch (err) {
      setError(err.message || 'Submission failed.');
    } finally {
      setIsFreezing(false);
    }
  }

  if (loading) {
    return <SkeletonLoader rows={6} />;
  }

  const blockers = data?.blocking_count || 0;
  const warnings = data?.warning_count || 0;
  const resolved = data?.resolved_count || 0;
  const readiness = data?.readiness_percentage || 78;
  const canSubmit = blockers === 0;

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
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-600 hover:text-emerald-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Interactive Demo Simulation Bar */}
      <div className="glass-panel rounded-2xl px-5 py-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200 font-medium">
          <Sparkles className="w-4 h-4 text-[var(--accent-text)]" />
          <span>Interactive Readiness Simulation:</span>
          <span className="text-slate-500 dark:text-slate-400">
            Watch the readiness ring dynamically animate when blockers are resolved.
          </span>
        </div>
        <div className="flex items-center gap-2">
          {blockers > 0 ? (
            <button
              type="button"
              onClick={handleDemoResolveBlockers}
              className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold flex items-center gap-1.5 shadow-sm shadow-emerald-600/20 transition-colors"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Simulate Resolve All Blockers (Animate to 100%)</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={handleDemoReset}
              className="px-3 py-1.5 rounded-xl border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 font-semibold flex items-center gap-1.5 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset to Initial State (78%)</span>
            </button>
          )}
        </div>
      </div>

      {/* Hero Overview Grid: Readiness Ring + Quick KPI Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Glassmorphic Readiness Ring Card */}
        <GlassCard className="flex flex-col items-center justify-center text-center p-6 lg:p-8">
          <ReadinessRing percentage={readiness} label="October 2026 Audit Readiness" />
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 max-w-xs">
            {canSubmit
              ? 'All policy blockers are resolved. You can now freeze and submit your audit pack.'
              : `${blockers} blocker(s) must be approved before month-end export is permitted.`}
          </p>

          <button
            type="button"
            disabled={!canSubmit || isFreezing}
            onClick={handleSubmitMonthEnd}
            className={`mt-5 w-full max-w-xs py-3 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-lg transition-all ${
              canSubmit
                ? 'bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] border border-[var(--accent-border)] shadow-md shadow-[var(--accent-glow)] cursor-pointer'
                : 'bg-slate-200 dark:bg-slate-800 text-slate-400 cursor-not-allowed shadow-none'
            }`}
          >
            <Send className="w-4 h-4" />
            <span>{isFreezing ? 'Freezing Snapshot...' : 'Freeze & Submit Month-End'}</span>
          </button>
        </GlassCard>

        {/* Stats Cards Grid */}
        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <StatsCard
            title="Blocking Issues"
            value={blockers}
            subtitle="Requires manager sign-off"
            icon={ShieldAlert}
            color={blockers > 0 ? 'red' : 'green'}
          />
          <StatsCard
            title="Warning Flags"
            value={warnings}
            subtitle="Informational policy notices"
            icon={AlertTriangle}
            color="amber"
          />
          <StatsCard
            title="Resolved Items"
            value={resolved}
            subtitle="Verified in current period"
            icon={CheckCircle2}
            color="green"
          />
          <StatsCard
            title="Audit Cycle"
            value="Oct 2026"
            subtitle="Payroll close: Nov 2, 2026"
            icon={Calendar}
            color="blue"
          />
        </div>
      </div>

      {/* Financial-Dashboard Recharts Section: 6-Month Trend & Issues by Type */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: 6-Month Trend Line Chart */}
        <GlassCard className="flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                6-Month Audit Readiness Trend
              </h3>
              <span className="text-[11px] font-mono text-[var(--accent-text)] font-semibold bg-[var(--accent-bg-subtle)] border border-[var(--accent-border-subtle)] px-2 py-0.5 rounded-md">
                Current: {readiness}%
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              Monthly compliance score across attendance, timesheets, and expense audits.
            </p>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data?.trend_history || []} margin={{ top: 10, right: 10, left: -20, bottom: 15 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                <XAxis
                  dataKey="month"
                  stroke="#94a3b8"
                  fontSize={11}
                  label={{ value: 'Audit Cycle Period', position: 'insideBottom', offset: -10, fontSize: 11, fill: '#64748b' }}
                />
                <YAxis
                  domain={[60, 100]}
                  stroke="#94a3b8"
                  fontSize={11}
                  tickFormatter={(v) => `${v}%`}
                  label={{ value: 'Score (%)', angle: -90, position: 'insideLeft', offset: 25, fontSize: 11, fill: '#64748b' }}
                />
                <Tooltip content={<GlassTooltip unit="%" />} />
                <Line
                  type="monotone"
                  dataKey="score"
                  name="Readiness Score"
                  stroke="var(--accent)"
                  strokeWidth={3}
                  dot={{ r: 5, fill: 'var(--accent)', strokeWidth: 2, stroke: 'var(--surface)' }}
                  activeDot={{ r: 7, fill: 'var(--accent)', stroke: 'var(--surface)', strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 pt-3 border-t border-slate-200/50 dark:border-slate-700/50 text-[11px] text-slate-500 dark:text-slate-400">
            <strong>Summary:</strong> Audit readiness averaged 90% over the last 6 months, dipping to {readiness}% in October due to unresolved punch exceptions.
          </div>
        </GlassCard>

        {/* Chart 2: Issues by Type Bar Chart */}
        <GlassCard className="flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Open Issues by Category
              </h3>
              <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                Total Unresolved: {blockers + warnings}
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              Discrepancies segmented by policy rule family for the active cycle.
            </p>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.issues_by_type || []} margin={{ top: 10, right: 10, left: -20, bottom: 15 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                <XAxis
                  dataKey="type"
                  stroke="#94a3b8"
                  fontSize={11}
                  label={{ value: 'Audit Rule Category', position: 'insideBottom', offset: -10, fontSize: 11, fill: '#64748b' }}
                />
                <YAxis
                  domain={[0, 4]}
                  allowDecimals={false}
                  stroke="#94a3b8"
                  fontSize={11}
                  label={{ value: 'Issue Count', angle: -90, position: 'insideLeft', offset: 25, fontSize: 11, fill: '#64748b' }}
                />
                <Tooltip content={<GlassTooltip />} />
                <Bar
                  dataKey="count"
                  name="Unresolved Issues"
                  fill="var(--accent)"
                  radius={[6, 6, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 pt-3 border-t border-slate-200/50 dark:border-slate-700/50 text-[11px] text-slate-500 dark:text-slate-400">
            <strong>Summary:</strong> Unresolved discrepancies are balanced across attendance missing punches, hours variance, and receipt uploads.
          </div>
        </GlassCard>
      </div>

      {/* Main Flags Section (Solid Table per spec) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Audit Findings & Flags
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Deterministic rule checks evaluated against timesheet, attendance, and expense records.
            </p>
          </div>
          <button
            onClick={loadData}
            className="text-xs font-semibold text-[var(--accent-text)] hover:underline"
          >
            Refresh Findings
          </button>
        </div>

        {data?.flags && data.flags.length > 0 ? (
          <FlagsTable
            flags={data.flags}
            onSelectFlag={(flag) => {
              setSelectedFlag(flag);
              setProposedValue(flag.rule_id === 'hours_mismatch' ? '8.0' : '');
              setEmployeeReason('');
              setHasAiDrafted(false);
            }}
            onExplainAI={(flag) => handleOpenExplainer(flag)}
          />
        ) : (
          <EmptyState
            title="Zero Audit Flags"
            description="Your attendance, timesheets, and claims are 100% compliant with company policies."
          />
        )}
      </div>

      {/* Correction Modal */}
      {selectedFlag && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-lg rounded-3xl p-6 sm:p-8 shadow-2xl relative">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200/60 dark:border-slate-700/60">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Submit Policy Correction
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Flag: {selectedFlag.title} &bull; Policy {selectedFlag.policy_version}
                </p>
              </div>
              <button
                onClick={() => setSelectedFlag(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCorrectionSubmit} className="space-y-4 mt-4">
              <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800 text-xs font-mono text-slate-700 dark:text-slate-300">
                <span className="font-bold block text-slate-500 uppercase text-[10px] mb-1">
                  System Evidence
                </span>
                {typeof selectedFlag.evidence === 'object' ? JSON.stringify(selectedFlag.evidence) : selectedFlag.evidence}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Proposed Value or Adjusted Punch Time
                </label>
                <input
                  type="text"
                  required
                  value={proposedValue}
                  onChange={(e) => setProposedValue(e.target.value)}
                  placeholder="e.g. 08:30 to 17:00, or 8.0 billable hours"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-xs text-slate-800 dark:text-white focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Reason for Correction (Sent to Manager)
                  </label>
                  <button
                    type="button"
                    onClick={handleGenerateAiDraft}
                    disabled={aiDraftLoading}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[var(--accent-bg-subtle)] hover:bg-[var(--accent-glow)] text-[var(--accent-text)] border border-[var(--accent-border-subtle)] font-semibold text-[11px] transition disabled:opacity-50"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    {aiDraftLoading ? 'Drafting...' : '✨ AI Assist Draft'}
                  </button>
                </div>
                <textarea
                  rows={3}
                  required
                  value={employeeReason}
                  onChange={(e) => setEmployeeReason(e.target.value)}
                  placeholder="Explain why this discrepancy occurred (e.g., onsite client visit, turnstile sensor missed badge)..."
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-xs text-slate-800 dark:text-white focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none"
                />
                {hasAiDrafted && (
                  <div className="mt-2 flex items-center gap-1.5 text-[11px] text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-2.5 py-1.5 rounded-lg border border-amber-200/50">
                    <Sparkles className="w-3 h-3 shrink-0" />
                    <span>AI-generated, review before use &bull; Edit as needed</span>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200/60 dark:border-slate-700/60">
                <button
                  type="button"
                  onClick={() => setSelectedFlag(null)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingCorr}
                  className="px-5 py-2.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] border border-[var(--accent-border)] text-xs font-bold shadow-md shadow-[var(--accent-glow)] disabled:opacity-50"
                >
                  {isSubmittingCorr ? 'Submitting...' : 'Send to Manager'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* AI Explainer Modal */}
      {explainFlag && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-lg rounded-3xl p-6 sm:p-8 shadow-2xl relative">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200/60 dark:border-slate-700/60">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-[var(--accent-bg-subtle)] text-[var(--accent-text)] border border-[var(--accent-border-subtle)]">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">
                      AI Policy Explainer
                    </h3>
                    <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-2 py-0.5 rounded border border-amber-200/50">
                      AI-generated, review before use
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Rule: {explainFlag.rule_id} &bull; Policy: {explainFlag.policy_version || 'POLICY-2026.1'}
                  </p>
                </div>
              </div>
              <button onClick={() => setExplainFlag(null)} className="p-1 rounded-lg text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {isExplainingLoading ? (
              <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-500 dark:text-slate-400">
                <Sparkles className="w-7 h-7 text-[var(--accent-text)] animate-spin" />
                <p className="text-xs font-medium">Generating policy analysis & resolution guidance...</p>
              </div>
            ) : (
              <div className="mt-4 space-y-3.5 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                <div>
                  <strong className="text-slate-800 dark:text-white block font-semibold mb-1">
                    Policy Standard:
                  </strong>
                  <p className="bg-slate-50 dark:bg-slate-800/50 p-2.5 rounded-xl border border-slate-200/50 dark:border-slate-700/50 text-slate-600 dark:text-slate-300">
                    {explainDetails?.policy_summary || 'Policy requires accurate time, punch pairs, and substantiated expense records.'}
                  </p>
                </div>

                <div>
                  <strong className="text-slate-800 dark:text-white block font-semibold mb-1">
                    Why was this flagged?
                  </strong>
                  <p>{explainDetails?.explanation || explainFlag.description}</p>
                </div>

                <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800/80 font-mono text-[11px]">
                  <span className="font-bold text-slate-400 block mb-1">Evidence Parameters:</span>
                  {typeof explainFlag.evidence === 'object' ? JSON.stringify(explainFlag.evidence) : explainFlag.evidence}
                </div>

                <div>
                  <strong className="text-slate-800 dark:text-white block font-semibold mb-1">
                    Recommended Resolution:
                  </strong>
                  <p className="text-slate-700 dark:text-slate-200 font-medium">
                    {explainDetails?.suggested_action || 'Submit a manager-reviewed correction request or attach missing documentation.'}
                  </p>
                </div>
              </div>
            )}

            <div className="mt-6 pt-4 border-t border-slate-200/60 dark:border-slate-700/60 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">
                Non-punitive self-audit guide
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setExplainFlag(null)}
                  className="px-3.5 py-2 rounded-xl bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white text-xs font-semibold"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const targetFlag = explainFlag;
                    setExplainFlag(null);
                    setSelectedFlag(targetFlag);
                    setEmployeeReason('');
                    setProposedValue('');
                    setHasAiDrafted(false);
                  }}
                  className="px-4 py-2 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] border border-[var(--accent-border)] text-xs font-bold inline-flex items-center gap-1.5 shadow-md shadow-[var(--accent-glow)]"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Proceed to Correction
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
