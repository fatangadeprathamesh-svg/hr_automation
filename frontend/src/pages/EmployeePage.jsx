import React, { useState, useEffect } from 'react';
import {
  fetchReadiness,
  submitCorrection,
  submitMonthEnd,
  getCurrentPersona,
} from '../api';
import GlassCard from '../components/common/GlassCard';
import ReadinessRing from '../components/common/ReadinessRing';
import StatsCard from '../components/common/StatsCard';
import FlagsTable from '../components/common/FlagsTable';
import SkeletonLoader from '../components/common/SkeletonLoader';
import EmptyState from '../components/common/EmptyState';
import ErrorBanner from '../components/common/ErrorBanner';
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Send,
  HelpCircle,
  X,
  FileCheck,
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

  // Freeze submission state
  const [isFreezing, setIsFreezing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

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
    return (
      <div className="space-y-6">
        <SkeletonLoader rows={6} />
      </div>
    );
  }

  const blockers = data?.blocking_count || 0;
  const warnings = data?.warning_count || 0;
  const resolved = data?.resolved_count || 0;
  const readiness = data?.readiness_percentage || 0;
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
          <button
            onClick={() => setSuccessMsg(null)}
            className="text-emerald-600 hover:text-emerald-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

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
                ? 'bg-[#F26A21] hover:bg-[#dc5612] text-white shadow-orange-500/25 cursor-pointer'
                : 'bg-slate-200 dark:bg-slate-800 text-slate-400 cursor-not-allowed shadow-none'
            }`}
          >
            <Send className="w-4 h-4" />
            <span>{isFreezing ? 'Freezing Snapshot...' : 'Freeze & Submit Month-End'}</span>
          </button>
        </GlassCard>

        {/* Stats Grid */}
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

      {/* Main Flags Section (Solid Table) */}
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
            className="text-xs font-semibold text-[#F26A21] hover:underline"
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
            }}
            onExplainAI={(flag) => setExplainFlag(flag)}
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
                {selectedFlag.evidence}
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
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-xs text-slate-800 dark:text-white focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Reason for Correction (Sent to Manager)
                </label>
                <textarea
                  rows={3}
                  required
                  value={employeeReason}
                  onChange={(e) => setEmployeeReason(e.target.value)}
                  placeholder="Explain why this discrepancy occurred (e.g., onsite client visit, turnstile sensor missed badge)..."
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-xs text-slate-800 dark:text-white focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
                />
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
                  className="px-5 py-2.5 rounded-xl bg-[#F26A21] hover:bg-[#dc5612] text-white text-xs font-bold shadow-md shadow-orange-500/20 disabled:opacity-50"
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
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-orange-100 text-[#F26A21]">
                  <HelpCircle className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    Rule Explainer
                  </h3>
                  <p className="text-xs text-slate-400">
                    Rule ID: {explainFlag.rule_id} &bull; Policy: {explainFlag.policy_version}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setExplainFlag(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-3 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              <p>
                <strong className="text-slate-800 dark:text-white">Why was this flagged?</strong><br />
                {explainFlag.description}
              </p>
              <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800 font-mono text-[11px]">
                <span className="font-bold text-slate-400 block mb-1">Evidence Parameters:</span>
                {explainFlag.evidence}
              </div>
              <p>
                <strong className="text-slate-800 dark:text-white">How to resolve:</strong><br />
                Submit a correction request proposing the verified hours or attach missing receipts. Your manager will receive this request for version-bound sign-off.
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-200/60 dark:border-slate-700/60 flex justify-end">
              <button
                type="button"
                onClick={() => setExplainFlag(null)}
                className="px-4 py-2 rounded-xl bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
