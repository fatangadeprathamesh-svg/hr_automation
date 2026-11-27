import React, { useState, useEffect, useRef } from 'react';
import {
  fetchReadiness,
  submitCorrection,
  submitMonthEnd,
  explainFlagAI,
  draftCorrectionAI,
  fetchAuditPeriods,
  checkBackendHealth,
  fetchSyncStatus,
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
  AlertCircle,
  FileText,
} from 'lucide-react';

export default function EmployeePage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [isServerUnreachable, setIsServerUnreachable] = useState(false);
  const [syncStatus, setSyncStatus] = useState(null);

  // Month selector
  const [selectedMonth, setSelectedMonth] = useState('2026-10');
  const [availableMonths, setAvailableMonths] = useState(['2026-10']);

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
    async function initPeriods() {
      try {
        const res = await fetchAuditPeriods();
        if (res?.periods && res.periods.length > 0) {
          setAvailableMonths(res.periods);
          setSelectedMonth(res.default_period || res.periods[0]);
        }
      } catch (e) {
        console.warn('Could not fetch audit periods:', e);
      }
    }
    initPeriods();
  }, []);

  const lastFetchRef = useRef(0);

  useEffect(() => {
    if (selectedMonth) {
      loadData(selectedMonth);
    }
  }, [selectedMonth]);

  // Tab focus listener with 30s throttling and background refresh (no blanking screen)
  useEffect(() => {
    function onFocus() {
      const now = Date.now();
      if (selectedMonth && now - lastFetchRef.current > 30000) {
        lastFetchRef.current = now;
        loadData(selectedMonth, true);
      }
    }
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [selectedMonth]);

  // Offline health check timer (every 5 seconds)
  useEffect(() => {
    if (!isServerUnreachable) return;
    const interval = setInterval(async () => {
      const health = await checkBackendHealth();
      if (health.online) {
        setIsServerUnreachable(false);
        loadData(selectedMonth, true);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [isServerUnreachable, selectedMonth]);

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

  async function loadData(month = selectedMonth, isBackground = false) {
    if (!isBackground) {
      setLoading(true);
    }
    setError(null);
    try {
      lastFetchRef.current = Date.now();
      const [res, sync] = await Promise.all([
        fetchReadiness(month),
        fetchSyncStatus().catch(() => null),
      ]);
      setData(res);
      setIsServerUnreachable(false);
      if (sync) setSyncStatus(sync);
    } catch (err) {
      const msg = err.message || '';
      if (msg.includes('Cannot reach the server') || msg.includes('Failed to fetch')) {
        setIsServerUnreachable(true);
      } else {
        setError(msg || 'Failed to load readiness audit.');
      }
    } finally {
      if (!isBackground) {
        setLoading(false);
      }
    }
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
      });

      setSuccessMsg(
        `Correction for ${selectedFlag.rule_name} submitted successfully for manager sign-off.`
      );
      setSelectedFlag(null);
      setProposedValue('');
      setEmployeeReason('');
      setHasAiDrafted(false);
      await loadData(selectedMonth);
    } catch (err) {
      setError(err.message || 'Failed to submit correction.');
    } finally {
      setIsSubmittingCorr(false);
    }
  }

  async function handleSubmitMonthEnd() {
    setIsFreezing(true);
    setError(null);

    try {
      const res = await submitMonthEnd(selectedMonth);
      setSuccessMsg(res.message || 'Month-end audit successfully frozen and submitted!');
      await loadData(selectedMonth);
    } catch (err) {
      setError(err.message || 'Submission failed.');
    } finally {
      setIsFreezing(false);
    }
  }

  if (loading) {
    return <SkeletonLoader rows={6} />;
  }

  const isLinked = data?.is_linked !== false;
  const hasData = data?.has_data !== false;
  const hasEvaluated = Boolean(data?.has_evaluated);
  const blockers = data?.blocking_count || 0;
  const warnings = data?.warning_count || 0;
  const resolved = data?.resolved_count || 0;
  const readiness = data?.readiness_percentage ?? data?.readiness_score ?? null;
  const canSubmit = hasEvaluated && blockers === 0 && Boolean(data?.can_submit);

  return (
    <div className="space-y-6">
      {/* Top Header & Month Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span>Employee Month-End Self-Audit</span>
              {data?.employee_id && (
                <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-md bg-[var(--surface-2)] text-[var(--accent-text)] border border-[var(--border)]">
                  {data.employee_id} {data.employee_name ? `• ${data.employee_name}` : ''}
                </span>
              )}
            </h1>
            {/* Sync freshness chip */}
            {syncStatus?.last_evaluation_time && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Data synced {new Date(syncStatus.last_evaluation_time).toLocaleTimeString()} | {syncStatus.total_findings ?? 0} findings
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Deterministic pre-payroll verification of punches, hours, and expense claims.
          </p>
        </div>

        {/* Audit Month Selector */}
        <div className="flex items-center gap-2">
          <label htmlFor="period-select" className="text-xs font-medium text-slate-600 dark:text-slate-300">
            Audit Month:
          </label>
          <select
            id="period-select"
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-[var(--surface)] text-[var(--text)] border border-[var(--border)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
          >
            {availableMonths.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Backend Unreachable Banner (Single banner with Retry button; no 'not linked' when offline) */}
      {isServerUnreachable ? (
        <div className="rounded-2xl border border-rose-300 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/40 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs text-rose-900 dark:text-rose-200">
              <h4 className="font-bold text-sm mb-0.5">Cannot reach the server (http://127.0.0.1:8000)</h4>
              <p>Start the backend and press Retry. Checking connection every 5s...</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => loadData(selectedMonth)}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold shrink-0 transition shadow-sm"
          >
            Retry
          </button>
        </div>
      ) : (
        <>
          {/* Unlinked Account Notice (Shown ONLY when backend is reachable) */}
          {!isLinked && (
            <div className="rounded-2xl border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/40 p-5 flex items-start gap-3 shadow-sm">
              <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
              <div className="text-xs text-amber-900 dark:text-amber-200">
                <h4 className="font-bold text-sm mb-1">Account Not Linked to Employee Record</h4>
                <p>{data?.message || 'Your account is not linked to an employee record yet. Import the master CSV or ask HR.'}</p>
              </div>
            </div>
          )}

          {/* No Data Notice */}
          {isLinked && !hasData && (
            <div className="rounded-2xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/40 p-5 flex items-start gap-3 shadow-sm">
              <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
              <div className="text-xs text-blue-900 dark:text-blue-200">
                <h4 className="font-bold text-sm mb-1">No Data Available</h4>
                <p>No imported attendance, timesheet, or expense records were found for your account in {selectedMonth}. Import master CSV data to begin audit evaluation.</p>
              </div>
            </div>
          )}
        </>
      )}

      {/* Notifications */}
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

      {/* Hero Overview Grid: Readiness Ring + Quick KPI Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Glassmorphic Readiness Ring Card */}
        <GlassCard className="flex flex-col items-center justify-center text-center p-6 lg:p-8">
          <ReadinessRing percentage={readiness} label={`${selectedMonth} Audit Readiness`} />
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 max-w-xs">
            {!isLinked
              ? 'Account not linked to an employee record.'
              : !hasData
              ? 'No data imported for this employee.'
              : !hasEvaluated
              ? 'Evaluation has not run for this cycle.'
              : canSubmit
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
            value={!isLinked || !hasData || !hasEvaluated ? '--' : blockers}
            subtitle={
              !isLinked || !hasData || !hasEvaluated
                ? 'Not evaluated yet. Import data to run the audit'
                : blockers > 0
                ? 'Requires manager sign-off'
                : 'All critical checks clear'
            }
            icon={ShieldAlert}
            color={!isLinked || !hasData || !hasEvaluated ? 'blue' : blockers > 0 ? 'red' : 'green'}
          />
          <StatsCard
            title="Warning Flags"
            value={!isLinked || !hasData || !hasEvaluated ? '--' : warnings}
            subtitle={
              !isLinked || !hasData || !hasEvaluated
                ? 'Not evaluated yet. Import data to run the audit'
                : warnings > 0
                ? 'Informational policy notices'
                : 'No policy warnings'
            }
            icon={AlertTriangle}
            color={!isLinked || !hasData || !hasEvaluated ? 'blue' : warnings > 0 ? 'amber' : 'green'}
          />
          <StatsCard
            title="Resolved Items"
            value={!isLinked || !hasData || !hasEvaluated ? '--' : resolved}
            subtitle={
              !isLinked || !hasData || !hasEvaluated
                ? 'Not evaluated yet. Import data to run the audit'
                : 'Verified in current period'
            }
            icon={CheckCircle2}
            color={!isLinked || !hasData || !hasEvaluated ? 'blue' : 'green'}
          />
          <StatsCard
            title="Audit Cycle"
            value={selectedMonth}
            subtitle={hasEvaluated ? 'Evaluation complete' : 'Not evaluated yet. Import data to run the audit'}
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
                Historical Audit Readiness Trend
              </h3>
              {readiness !== null && (
                <span className="text-[11px] font-mono text-[var(--accent-text)] font-semibold bg-[var(--accent-bg-subtle)] border border-[var(--accent-border-subtle)] px-2 py-0.5 rounded-md">
                  Current: {readiness}%
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              Real monthly compliance scores evaluated from attendance, timesheet, and expense audit findings.
            </p>
          </div>

          <div className="h-64 w-full">
            {data?.trend_history && data.trend_history.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.trend_history} margin={{ top: 10, right: 10, left: -20, bottom: 15 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                  <XAxis
                    dataKey="month"
                    stroke="#94a3b8"
                    fontSize={11}
                    label={{ value: 'Audit Cycle Period', position: 'insideBottom', offset: -10, fontSize: 11, fill: '#64748b' }}
                  />
                  <YAxis
                    domain={[0, 100]}
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
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400 italic">
                No historical trend data recorded yet.
              </div>
            )}
          </div>

          {data?.trend_history && data.trend_history.length > 0 && readiness !== null && (
            <div className="mt-3 pt-3 border-t border-slate-200/50 dark:border-slate-700/50 text-[11px] text-slate-500 dark:text-slate-400">
              <strong>Summary:</strong> Audit readiness for {selectedMonth} is {readiness}% with {blockers} blocking issue(s).
            </div>
          )}
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
              Real open discrepancy counts across policy rule categories for {selectedMonth}.
            </p>
          </div>

          <div className="h-64 w-full">
            {data?.issues_by_type && data.issues_by_type.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.issues_by_type} margin={{ top: 10, right: 10, left: -20, bottom: 15 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                  <XAxis
                    dataKey="type"
                    stroke="#94a3b8"
                    fontSize={11}
                    label={{ value: 'Policy Rule Category', position: 'insideBottom', offset: -10, fontSize: 11, fill: '#64748b' }}
                  />
                  <YAxis
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
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400 italic">
                No category issues recorded for this cycle.
              </div>
            )}
          </div>

          <div className="mt-3 pt-3 border-t border-slate-200/50 dark:border-slate-700/50 text-[11px] text-slate-500 dark:text-slate-400">
            {blockers + warnings > 0 ? (
              <span>
                <strong>Summary:</strong> {blockers} blocking issue(s) and {warnings} warning(s) currently open for {selectedMonth}.
              </span>
            ) : hasEvaluated ? (
              <span>
                <strong>Summary:</strong> Zero policy violations detected across evaluated categories for {selectedMonth}.
              </span>
            ) : (
              <span>
                <strong>Summary:</strong> Evaluation has not yet executed for {selectedMonth}.
              </span>
            )}
          </div>
        </GlassCard>
      </div>

      {/* Main Flags Section */}
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
            onClick={() => loadData(selectedMonth)}
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
        ) : hasEvaluated ? (
          <EmptyState
            title="Zero Audit Flags"
            description="Your attendance, timesheets, and claims are 100% compliant with company policies."
          />
        ) : (
          <EmptyState
            title="Not Evaluated"
            description="Audit rules have not been evaluated for this period yet. Import master data or request HR to run an audit."
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

            <form onSubmit={handleCorrectionSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Proposed Value / Explanation
                </label>
                <input
                  type="text"
                  required
                  value={proposedValue}
                  onChange={(e) => setProposedValue(e.target.value)}
                  placeholder="e.g. 8.0, 17:30, or receipt description"
                  className="w-full px-3 py-2 rounded-xl text-xs bg-[var(--surface)] text-[var(--text)] border border-[var(--border)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Employee Reason & Justification
                  </label>
                  <button
                    type="button"
                    onClick={handleGenerateAiDraft}
                    disabled={aiDraftLoading}
                    className="inline-flex items-center gap-1 text-[11px] font-bold text-[var(--accent-text)] hover:opacity-80 transition-opacity"
                  >
                    <Sparkles className="w-3 h-3" />
                    <span>{aiDraftLoading ? 'Drafting...' : 'AI Draft Reason'}</span>
                  </button>
                </div>
                <textarea
                  required
                  rows={3}
                  value={employeeReason}
                  onChange={(e) => setEmployeeReason(e.target.value)}
                  placeholder="Provide detailed explanation for your manager..."
                  className="w-full px-3 py-2 rounded-xl text-xs bg-[var(--surface)] text-[var(--text)] border border-[var(--border)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                />
                {hasAiDrafted && (
                  <p className="text-[11px] text-emerald-600 dark:text-emerald-400 mt-1">
                    AI generated justification based on compliance policy guidelines.
                  </p>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedFlag(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold border border-[var(--border)] hover:bg-[var(--surface-2)] text-[var(--text)]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingCorr}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-[var(--accent)] text-[var(--accent-ink)] hover:opacity-90 disabled:opacity-50"
                >
                  {isSubmittingCorr ? 'Submitting...' : 'Submit to Manager'}
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
            <div className="flex items-center justify-between pb-3 border-b border-slate-200/60 dark:border-slate-700/60">
              <div className="flex items-center gap-2">
                <HelpCircle className="w-5 h-5 text-[var(--accent-text)]" />
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Compliance Rule Explainer
                </h3>
              </div>
              <button
                onClick={() => setExplainFlag(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-3 text-xs">
              {isExplainingLoading ? (
                <div className="py-8 text-center text-slate-500">
                  <Sparkles className="w-6 h-6 animate-spin mx-auto mb-2 text-[var(--accent-text)]" />
                  Generating plain-language compliance policy explanation...
                </div>
              ) : (
                <>
                  <div>
                    <span className="font-bold text-slate-700 dark:text-slate-300">Rule:</span>{' '}
                    <span className="font-mono text-[var(--accent-text)]">{explainFlag.rule_id}</span>
                  </div>
                  <div>
                    <span className="font-bold text-slate-700 dark:text-slate-300">Explanation:</span>
                    <p className="mt-1 text-slate-600 dark:text-slate-300 leading-relaxed bg-[var(--surface-2)] p-3 rounded-xl border border-[var(--border)]">
                      {explainDetails?.plain_explanation || explainFlag.description || 'Deterministic policy validation rule.'}
                    </p>
                  </div>
                  <div>
                    <span className="font-bold text-slate-700 dark:text-slate-300">Policy Reference:</span>
                    <p className="mt-1 text-slate-500 dark:text-slate-400">
                      {explainDetails?.policy_summary || 'Policy requires accurate time, punch pairs, and substantiated expense records.'}
                    </p>
                  </div>
                </>
              )}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setExplainFlag(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-[var(--accent)] text-[var(--accent-ink)] hover:opacity-90"
              >
                Got It
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
