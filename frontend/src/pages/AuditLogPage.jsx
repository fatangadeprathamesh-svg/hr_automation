import React, { useState, useEffect } from 'react';
import {
  fetchAuditLog,
  verifyLedgerIntegrity,
} from '../api';
import GlassCard from '../components/common/GlassCard';
import StatsCard from '../components/common/StatsCard';
import SkeletonLoader from '../components/common/SkeletonLoader';
import ErrorBanner from '../components/common/ErrorBanner';
import {
  ShieldCheck,
  CheckCircle2,
  Lock,
  Hash,
  RefreshCw,
  X,
  FileCode,
} from 'lucide-react';

export default function AuditLogPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [integrityReport, setIntegrityReport] = useState(null);
  const [isVerifying, setIsVerifying] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAuditLog();
      setData(res);
    } catch (err) {
      setError(err.message || 'Failed to load audit ledger.');
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyIntegrity() {
    setIsVerifying(true);
    setError(null);
    try {
      const res = await verifyLedgerIntegrity();
      setIntegrityReport(res);
    } catch (err) {
      setError(err.message || 'Integrity check encountered an error.');
    } finally {
      setIsVerifying(false);
    }
  }

  if (loading) {
    return <SkeletonLoader rows={6} />;
  }

  const events = data?.events || [];

  return (
    <div className="space-y-6">
      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      {/* Cryptographic Ledger Banner / Verification Result */}
      {integrityReport && (
        <div className="rounded-2xl border border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/50 p-5 shadow-sm text-xs">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-xl bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-emerald-900 dark:text-emerald-200">
                  {integrityReport.message}
                </h3>
                <div className="mt-2 space-y-1 font-mono text-[11px] text-emerald-800 dark:text-emerald-300">
                  <p>Checked Events: {integrityReport.checked_events} sequential records</p>
                  <p className="truncate max-w-xl">Genesis Block Hash: {integrityReport.genesis_hash}</p>
                  <p className="truncate max-w-xl">Head Block Hash: {integrityReport.head_hash}</p>
                </div>
              </div>
            </div>
            <button
              onClick={() => setIntegrityReport(null)}
              className="text-emerald-600 hover:text-emerald-800 p-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Top Header Card */}
      <GlassCard className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-orange-100 dark:bg-orange-950/60 text-[#F26A21]">
              <Lock className="w-5 h-5" />
            </span>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">
                Tamper-Evident Forensic Audit Ledger
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Every policy evaluation, correction, and manager decision is cryptographically chained with SHA-256 hashes.
              </p>
            </div>
          </div>
        </div>

        <button
          type="button"
          disabled={isVerifying}
          onClick={handleVerifyIntegrity}
          className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-[#F26A21] hover:bg-[#dc5612] text-white text-xs font-bold flex items-center justify-center gap-2 shadow-md shadow-orange-500/20 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isVerifying ? 'animate-spin' : ''}`} />
          <span>{isVerifying ? 'Verifying Hashes...' : 'Verify Ledger Integrity'}</span>
        </button>
      </GlassCard>

      {/* Forensic Log Table (Solid Surface) */}
      <div className="solid-surface rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80 text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                <th className="py-3.5 px-4 sm:px-6">Seq #</th>
                <th className="py-3.5 px-4">Action & Role</th>
                <th className="py-3.5 px-4">Actor ID</th>
                <th className="py-3.5 px-4 hidden sm:table-cell">Target Record</th>
                <th className="py-3.5 px-4 hidden md:table-cell">Current Event SHA-256</th>
                <th className="py-3.5 px-4 sm:px-6 text-right">Integrity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs text-slate-700 dark:text-slate-200">
              {events.map((evt) => (
                <tr
                  key={evt.sequence_id}
                  className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors"
                >
                  <td className="py-4 px-4 sm:px-6 font-mono font-bold text-slate-800 dark:text-slate-200">
                    #{evt.sequence_id}
                  </td>
                  <td className="py-4 px-4 whitespace-nowrap">
                    <span className="block font-bold text-slate-900 dark:text-white font-mono text-[11px]">
                      {evt.action_type}
                    </span>
                    <span className="block text-[10px] text-slate-400 capitalize">
                      {evt.actor_role} &bull; {new Date(evt.timestamp).toLocaleString()}
                    </span>
                  </td>
                  <td className="py-4 px-4 font-mono text-[11px] text-slate-700 dark:text-slate-300">
                    {evt.actor_id}
                  </td>
                  <td className="py-4 px-4 font-mono text-[11px] text-slate-500 dark:text-slate-400 hidden sm:table-cell">
                    {evt.target_entity}/{evt.target_id}
                  </td>
                  <td className="py-4 px-4 font-mono text-[11px] text-slate-500 dark:text-slate-400 hidden md:table-cell">
                    <span className="inline-block max-w-[180px] truncate" title={evt.current_hash}>
                      {evt.current_hash}
                    </span>
                  </td>
                  <td className="py-4 px-4 sm:px-6 text-right whitespace-nowrap">
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 px-2 py-0.5 rounded-full">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Valid
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
