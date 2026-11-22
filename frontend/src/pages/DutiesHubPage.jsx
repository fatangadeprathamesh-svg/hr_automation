import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  fetchDutiesHub,
  getCurrentPersona,
} from '../api';
import GlassCard from '../components/common/GlassCard';
import SkeletonLoader from '../components/common/SkeletonLoader';
import ErrorBanner from '../components/common/ErrorBanner';
import {
  Briefcase,
  Bot,
  UserCheck,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Lock,
  ChevronRight,
  Sparkles,
  ShieldCheck,
  Scale,
  Banknote,
  ShieldAlert,
  AlertOctagon,
  UserPlus,
  CalendarCheck,
  UserMinus,
  BookOpen,
  Award,
} from 'lucide-react';

const ICON_MAP = {
  Banknote: Banknote,
  Scale: Scale,
  ShieldAlert: ShieldAlert,
  AlertOctagon: AlertOctagon,
  UserPlus: UserPlus,
  UserCheck: UserCheck,
  CalendarCheck: CalendarCheck,
  UserMinus: UserMinus,
  BookOpen: BookOpen,
  Award: Award,
};

export default function DutiesHubPage() {
  const navigate = useNavigate();
  const [duties, setDuties] = useState([]);
  const [actorInfo, setActorInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const persona = getCurrentPersona();

  useEffect(() => {
    loadHubData();
  }, [persona?.id]);

  async function loadHubData() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchDutiesHub();
      setDuties(res.duties || []);
      setActorInfo(res.actor || {});
    } catch (err) {
      setError(err.message || 'Failed to load HR Duties Hub.');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <SkeletonLoader rows={8} />;
  }

  const totalPrepared = duties.reduce((acc, d) => acc + (d.prepared_by_bot || 0), 0);
  const totalAwaiting = duties.reduce((acc, d) => acc + (d.awaiting_approval || 0), 0);
  const totalOverdue = duties.reduce((acc, d) => acc + (d.overdue_count || 0), 0);

  return (
    <div className="space-y-6">
      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      {/* Header Banner: Bot vs Human Operating Philosophy */}
      <div className="glass-panel rounded-2xl p-6 sm:p-7 relative overflow-hidden">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="p-2.5 rounded-xl bg-[var(--accent-bg-subtle)] text-[var(--accent-text)] border border-[var(--accent-border-subtle)]">
                <Briefcase className="w-6 h-6" />
              </span>
              <div>
                <h1 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white tracking-tight">
                  HR Duties Hub
                </h1>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Core Enterprise Functions with Strict Bot Automation & Human Approval Separation
                </p>
              </div>
            </div>

            <div className="mt-3.5 inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-xs text-slate-700 dark:text-slate-300 font-medium border border-slate-200 dark:border-slate-700">
              <Bot className="w-4 h-4 text-[var(--accent-text)]" />
              <span>Bot Prepares & Automates</span>
              <span className="text-slate-400 dark:text-slate-500">&bull;</span>
              <UserCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span>Human Approves & Decides</span>
              <span className="text-slate-400 dark:text-slate-500">&bull;</span>
              <span className="text-[11px] text-amber-600 dark:text-amber-400 font-semibold">Maker-Checker Enforced</span>
            </div>
          </div>

          {/* Quick Aggregate Stats */}
          <div className="grid grid-cols-3 gap-2.5 w-full md:w-auto">
            <div className="p-3 rounded-xl bg-white/80 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-center">
              <span className="text-[10px] font-bold text-slate-400 uppercase block">Bot Prepared</span>
              <span className="text-xl font-extrabold text-[var(--accent-text)]">{totalPrepared}</span>
            </div>
            <div className="p-3 rounded-xl bg-white/80 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-center">
              <span className="text-[10px] font-bold text-slate-400 uppercase block">Awaiting Approval</span>
              <span className="text-xl font-extrabold text-amber-600 dark:text-amber-400">{totalAwaiting}</span>
            </div>
            <div className="p-3 rounded-xl bg-white/80 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-center">
              <span className="text-[10px] font-bold text-slate-400 uppercase block">Overdue</span>
              <span className="text-xl font-extrabold text-rose-600 dark:text-rose-400">{totalOverdue}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 10 Duty Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-5">
        {duties.map((duty) => {
          const Icon = ICON_MAP[duty.icon] || Briefcase;
          const isPosh = duty.key === 'posh';
          const isLeave = duty.key === 'attendance_leave';

          return (
            <GlassCard
              key={duty.key}
              onClick={() => navigate(`/duties/${duty.key}`)}
              className="group cursor-pointer hover:border-[var(--accent)]/60 transition-all duration-200 flex flex-col justify-between"
            >
              <div>
                {/* Top Badge Strip */}
                <div className="flex items-center justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2">
                    <span className="p-2 rounded-xl bg-[var(--accent-bg-subtle)] text-[var(--accent-text)] border border-[var(--accent-border-subtle)]">
                      <Icon className="w-5 h-5" />
                    </span>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                        {duty.category}
                      </span>
                      <h3 className="text-base font-bold text-slate-900 dark:text-white group-hover:text-[var(--accent-text)] transition-colors leading-tight">
                        {duty.name}
                      </h3>
                    </div>
                  </div>

                  {isPosh ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                      <Lock className="w-3 h-3" />
                      Confidential IC
                    </span>
                  ) : isLeave ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                      <Sparkles className="w-3 h-3" />
                      Auto-Approval Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      Human Gate Required
                    </span>
                  )}
                </div>

                {/* Description */}
                <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2 mb-4 leading-relaxed">
                  {duty.description}
                </p>

                {/* Bot-vs-Human Split Breakdown */}
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60 space-y-2 text-[11px] mb-4">
                  <div className="flex items-start gap-1.5 text-slate-700 dark:text-slate-200">
                    <Bot className="w-3.5 h-3.5 text-[var(--accent-text)] shrink-0 mt-0.5" />
                    <span className="line-clamp-1">
                      <strong>Bot:</strong> {duty.bot_actions[0]}
                    </span>
                  </div>
                  <div className="flex items-start gap-1.5 text-slate-700 dark:text-slate-200">
                    <UserCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                    <span className="line-clamp-1">
                      <strong>Human:</strong> {duty.human_gate}
                    </span>
                  </div>
                </div>
              </div>

              {/* Bottom Action Footer with Live Counters */}
              <div className="pt-3 border-t border-slate-200/60 dark:border-slate-700/60 flex items-center justify-between">
                <div className="flex items-center gap-3 text-xs">
                  <div className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
                    <span className="text-[10px] uppercase font-semibold">Prepared:</span>
                    <span className="font-bold text-slate-900 dark:text-white">{duty.prepared_by_bot}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-[10px] uppercase font-semibold text-slate-500 dark:text-slate-400">Queue:</span>
                    <span className={`font-bold ${duty.awaiting_approval > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400'}`}>
                      {duty.awaiting_approval}
                    </span>
                  </div>
                  {duty.overdue_count > 0 && (
                    <div className="flex items-center gap-1 text-rose-600 dark:text-rose-400 font-bold">
                      <AlertTriangle className="w-3 h-3" />
                      <span>{duty.overdue_count} overdue</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-1 text-xs font-bold text-[var(--accent-text)] group-hover:translate-x-1 transition-transform">
                  <span>Open</span>
                  <ChevronRight className="w-4 h-4" />
                </div>
              </div>
            </GlassCard>
          );
        })}
      </div>
    </div>
  );
}
