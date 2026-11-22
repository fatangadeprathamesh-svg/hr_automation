import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  fetchDutyDetail,
  fetchDutyTasks,
  decideDutyTask,
  triggerDutyBotRun,
  submitDutyLeaveRequest,
  submitPoshComplaint,
  fetchPoshAnnualReport,
  searchPolicies,
  getCurrentPersona,
  API_BASE,
} from '../api';
import GlassCard from '../components/common/GlassCard';
import SkeletonLoader from '../components/common/SkeletonLoader';
import ErrorBanner from '../components/common/ErrorBanner';
import {
  ArrowLeft,
  Bot,
  UserCheck,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Sparkles,
  Lock,
  Download,
  Printer,
  Calendar,
  AlertTriangle,
  Search,
  FileText,
  Clock,
  ShieldCheck,
  Banknote,
  Scale,
  ShieldAlert,
  AlertOctagon,
  UserPlus,
  CalendarCheck,
  UserMinus,
  BookOpen,
  Award,
  Send,
  HelpCircle,
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

export default function DutyDetailPage() {
  const { dutyKey } = useParams();
  const navigate = useNavigate();
  const persona = getCurrentPersona();

  const [detail, setDetail] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [activeTab, setActiveTab] = useState('queue'); // queue | bot | records
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [botRunning, setBotRunning] = useState(false);
  const [botRunResult, setBotRunResult] = useState(null);

  // Decision Modal State
  const [decidingTask, setDecidingTask] = useState(null);
  const [decisionAction, setDecisionAction] = useState('approved');
  const [decisionNote, setDecisionNote] = useState('');
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);

  // Duty 7 Interactive Leave Request State
  const [leaveType, setLeaveType] = useState('casual');
  const [leaveDays, setLeaveDays] = useState(1.0);
  const [leaveReason, setLeaveReason] = useState('Personal obligation');
  const [leaveSubmitting, setLeaveSubmitting] = useState(false);
  const [leaveFeedback, setLeaveFeedback] = useState(null);

  // Duty 9 Interactive Policy Search State
  const [policyQuery, setPolicyQuery] = useState('');
  const [policyResults, setPolicyResults] = useState(null);
  const [policySearching, setPolicySearching] = useState(false);

  // Duty 3 POSH Annual Report State
  const [poshReport, setPoshReport] = useState(null);

  useEffect(() => {
    loadData();
  }, [dutyKey, persona?.id]);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [detRes, taskRes] = await Promise.all([
        fetchDutyDetail(dutyKey),
        fetchDutyTasks(dutyKey),
      ]);
      setDetail(detRes);
      setTasks(taskRes.tasks || []);

      if (dutyKey === 'posh') {
        const rep = await fetchPoshAnnualReport();
        setPoshReport(rep);
      }
    } catch (err) {
      setError(err.message || 'Failed to load duty workspace.');
    } finally {
      setLoading(false);
    }
  }

  async function handleTriggerBot() {
    setBotRunning(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await triggerDutyBotRun(dutyKey);
      setBotRunResult(res);
      setSuccessMsg(res.human_gate_message || 'Bot automation completed successfully.');
      await loadData();
    } catch (err) {
      setError(err.message || 'Failed to execute bot action.');
    } finally {
      setBotRunning(false);
    }
  }

  async function handleConfirmDecision() {
    if (!decidingTask) return;
    setIsSubmittingDecision(true);
    setError(null);
    try {
      await decideDutyTask(
        dutyKey,
        decidingTask.id,
        decisionAction,
        decisionNote,
        decidingTask.version
      );
      setSuccessMsg(`Task successfully marked as ${decisionAction}.`);
      setDecidingTask(null);
      setDecisionNote('');
      await loadData();
    } catch (err) {
      setError(err.message || 'Decision submission failed.');
    } finally {
      setIsSubmittingDecision(false);
    }
  }

  async function handleSimulateLeave(e) {
    e.preventDefault();
    setLeaveSubmitting(true);
    setLeaveFeedback(null);
    setError(null);
    try {
      const todayStr = new Date().toISOString().split('T')[0];
      const res = await submitDutyLeaveRequest({
        leave_type: leaveType,
        start_date: todayStr,
        end_date: todayStr,
        days_requested: parseFloat(leaveDays),
        reason: leaveReason,
      });
      setLeaveFeedback(res);
      await loadData();
    } catch (err) {
      setError(err.message || 'Leave simulation failed.');
    } finally {
      setLeaveSubmitting(false);
    }
  }

  async function handleSearchPolicy(e) {
    e.preventDefault();
    if (!policyQuery.trim()) return;
    setPolicySearching(true);
    try {
      const res = await searchPolicies(policyQuery.trim());
      setPolicyResults(res.matches || []);
    } catch (err) {
      setError(err.message || 'Policy search failed.');
    } finally {
      setPolicySearching(false);
    }
  }

  if (loading) {
    return <SkeletonLoader rows={8} />;
  }

  const config = detail?.config || {};
  const metrics = detail?.metrics || {};
  const isPosh = dutyKey === 'posh';
  const isLeave = dutyKey === 'attendance_leave';
  const isRestrictedPosh = detail?.is_restricted_posh;
  const Icon = ICON_MAP[config.icon] || Briefcase;

  const queueTasks = tasks.filter((t) => t.status === 'awaiting_approval');
  const recordTasks = tasks.filter((t) => t.status !== 'awaiting_approval');

  return (
    <div className="space-y-6">
      {/* Top Back & Navigation Button */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/duties')}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-800/70 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Duties Hub</span>
        </button>

        <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
          Duty Key: <span className="font-semibold text-slate-900 dark:text-white">{dutyKey}</span>
        </span>
      </div>

      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      {successMsg && (
        <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40 p-4 flex items-center justify-between text-emerald-800 dark:text-emerald-200 text-xs font-semibold">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-600 hover:text-emerald-800">
            &times;
          </button>
        </div>
      )}

      {/* Main Duty Header Card */}
      <GlassCard className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-6 sm:p-7">
        <div className="flex items-start gap-3.5">
          <span className="p-3 rounded-2xl bg-[var(--accent-bg-subtle)] text-[var(--accent-text)] border border-[var(--accent-border-subtle)] shrink-0">
            <Icon className="w-7 h-7" />
          </span>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white tracking-tight">
                {config.name}
              </h1>
              <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                {config.category}
              </span>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 max-w-2xl leading-relaxed">
              {config.description}
            </p>
          </div>
        </div>

        {/* Live Counters */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="p-3 rounded-xl bg-white/70 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 text-center min-w-[90px]">
            <span className="text-[10px] font-bold text-slate-400 uppercase block">In Queue</span>
            <span className="text-xl font-extrabold text-amber-600 dark:text-amber-400">{metrics.awaiting_approval}</span>
          </div>
          <div className="p-3 rounded-xl bg-white/70 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 text-center min-w-[90px]">
            <span className="text-[10px] font-bold text-slate-400 uppercase block">Bot Prepared</span>
            <span className="text-xl font-extrabold text-[var(--accent-text)]">{metrics.prepared_by_bot}</span>
          </div>
        </div>
      </GlassCard>

      {/* MANDATORY STRIP: Bot Prepared / Human Approves */}
      <div className="glass-panel rounded-2xl px-5 py-3.5 border-l-4 border-l-[var(--accent)] flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 font-bold text-slate-800 dark:text-white">
            <Bot className="w-4 h-4 text-[var(--accent-text)]" />
            <span>Bot Prepares:</span>
            <span className="font-normal text-slate-600 dark:text-slate-300">
              {config.bot_actions?.[0] || 'Automated data aggregation'}
            </span>
          </div>
          <span className="hidden sm:inline text-slate-300 dark:text-slate-700">|</span>
          <div className="flex items-center gap-1.5 font-bold text-slate-800 dark:text-white">
            <UserCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Human Approves:</span>
            <span className="font-normal text-slate-600 dark:text-slate-300">
              {config.human_gate}
            </span>
          </div>
        </div>

        {isLeave && (
          <span className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/60 px-2.5 py-1 rounded-full border border-emerald-200 dark:border-emerald-800 flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5" />
            Auto-Approval active for compliant leaves (&le; 2d, coverage &ge; 70%)
          </span>
        )}
      </div>

      {/* POSH Confidential Restriction Notice if Non-IC Member */}
      {isRestrictedPosh && (
        <div className="rounded-2xl border border-purple-300 dark:border-purple-800 bg-purple-50 dark:bg-purple-950/40 p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="p-2.5 rounded-xl bg-purple-200 dark:bg-purple-900 text-purple-700 dark:text-purple-300 shrink-0">
              <Lock className="w-5 h-5" />
            </span>
            <div>
              <h3 className="text-sm font-bold text-purple-900 dark:text-purple-100">
                Access Restricted: Internal Committee Clearance Required
              </h3>
              <p className="text-xs text-purple-700 dark:text-purple-300 mt-0.5 max-w-xl">
                POSH complaint intake, inquiry proceedings, and respondent testimony are strictly confidential.
                Encrypted at rest with zero complaint text exposed to non-IC members or audit ledgers.
              </p>
            </div>
          </div>
          <div className="text-xs text-purple-700 dark:text-purple-300 font-semibold bg-purple-100 dark:bg-purple-900/60 px-3 py-1.5 rounded-xl border border-purple-300 dark:border-purple-700 shrink-0">
            Switch persona to Irene IC Member in top bar to inspect
          </div>
        </div>
      )}

      {/* Tabs Header */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('queue')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'queue'
              ? 'bg-[var(--accent)] text-[var(--accent-ink)] font-bold shadow-md shadow-[var(--accent-glow)]'
              : 'text-slate-600 dark:text-slate-300 hover:bg-white/60 dark:hover:bg-slate-800'
          }`}
        >
          <Clock className="w-4 h-4" />
          <span>Approval Queue</span>
          <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${activeTab === 'queue' ? 'bg-black/20 text-black' : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200'}`}>
            {queueTasks.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('bot')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'bot'
              ? 'bg-[var(--accent)] text-[var(--accent-ink)] font-bold shadow-md shadow-[var(--accent-glow)]'
              : 'text-slate-600 dark:text-slate-300 hover:bg-white/60 dark:hover:bg-slate-800'
          }`}
        >
          <Bot className="w-4 h-4" />
          <span>Bot Activity</span>
        </button>

        <button
          onClick={() => setActiveTab('records')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'records'
              ? 'bg-[var(--accent)] text-[var(--accent-ink)] font-bold shadow-md shadow-[var(--accent-glow)]'
              : 'text-slate-600 dark:text-slate-300 hover:bg-white/60 dark:hover:bg-slate-800'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Records & Artifacts</span>
          <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${activeTab === 'records' ? 'bg-black/20 text-black' : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200'}`}>
            {recordTasks.length}
          </span>
        </button>
      </div>

      {/* TAB 1: APPROVAL QUEUE */}
      {activeTab === 'queue' && (
        <div className="space-y-4">
          {queueTasks.length === 0 ? (
            <GlassCard className="text-center py-12 text-slate-500 dark:text-slate-400">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2 opacity-80" />
              <h4 className="text-sm font-bold text-slate-900 dark:text-white">Approval Queue Clear</h4>
              <p className="text-xs mt-1">There are no pending items awaiting human approval for this duty.</p>
            </GlassCard>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {queueTasks.map((task) => {
                const isMaker = task.is_maker || (task.prepared_by === persona.id);
                return (
                  <GlassCard key={task.id} className="p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div className="space-y-1.5 max-w-2xl">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 uppercase">
                          Awaiting Decision
                        </span>
                        <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                          {task.title}
                        </h4>
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                        <span>Prepared by: <strong className="text-slate-700 dark:text-slate-200 font-mono">{task.prepared_by}</strong></span>
                        <span>&bull;</span>
                        <span>Due: <strong className="text-slate-700 dark:text-slate-200 font-mono">{task.due_date || 'Standard'}</strong></span>
                        <span>&bull;</span>
                        <span>Version: <strong className="text-slate-700 dark:text-slate-200 font-mono">v{task.version}</strong></span>
                      </div>

                      {/* Payload Snapshot */}
                      {task.payload && Object.keys(task.payload).length > 0 && (
                        <div className="mt-2 p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/50 dark:border-slate-800 text-[11px] font-mono text-slate-600 dark:text-slate-300 overflow-x-auto max-h-28">
                          <pre>{JSON.stringify(task.payload, null, 2)}</pre>
                        </div>
                      )}
                    </div>

                    {/* Actions: Maker-checker guard */}
                    <div className="flex flex-col sm:flex-row items-end sm:items-center gap-2 shrink-0">
                      {isMaker ? (
                        <div className="text-right">
                          <span className="px-2.5 py-1 rounded-lg bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 text-[11px] font-bold border border-rose-200 dark:border-rose-900 block">
                            Maker-Checker Guard Active
                          </span>
                          <span className="text-[10px] text-slate-400 mt-0.5 block">
                            You prepared this task and cannot self-approve it.
                          </span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => {
                              setDecidingTask(task);
                              setDecisionAction('approved');
                            }}
                            className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center gap-1.5 shadow-sm shadow-emerald-600/20 transition-colors"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Approve</span>
                          </button>
                          <button
                            onClick={() => {
                              setDecidingTask(task);
                              setDecisionAction('returned');
                            }}
                            className="px-3 py-1.5 rounded-xl border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 font-semibold text-xs flex items-center gap-1 transition-colors"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                            <span>Return</span>
                          </button>
                          <button
                            onClick={() => {
                              setDecidingTask(task);
                              setDecisionAction('rejected');
                            }}
                            className="px-3 py-1.5 rounded-xl bg-rose-100 dark:bg-rose-950/60 hover:bg-rose-200 text-rose-700 dark:text-rose-300 font-semibold text-xs flex items-center gap-1 transition-colors"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            <span>Reject</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </GlassCard>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: BOT ACTIVITY */}
      {activeTab === 'bot' && (
        <div className="space-y-5">
          <GlassCard className="p-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Bot className="w-5 h-5 text-[var(--accent-text)]" />
                  <span>Bot Automated Capabilities for {config.name}</span>
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  The bot executes deterministic routines, generates draft artifacts, and queues items for human approval.
                </p>
              </div>

              <button
                type="button"
                disabled={botRunning}
                onClick={handleTriggerBot}
                className="px-4 py-2 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] border border-[var(--accent-border)] font-bold text-xs flex items-center gap-2 shadow-lg shadow-[var(--accent-glow)] transition-all shrink-0 cursor-pointer"
              >
                <Sparkles className={`w-4 h-4 ${botRunning ? 'animate-spin' : ''}`} />
                <span>{botRunning ? 'Executing Bot Automation...' : 'Run Bot Automation & Prep'}</span>
              </button>
            </div>

            {/* List of actions */}
            <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
              {config.bot_actions?.map((action, idx) => (
                <div key={idx} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/50 dark:border-slate-700/50 flex items-start gap-2 text-xs text-slate-700 dark:text-slate-300">
                  <span className="w-5 h-5 rounded-full bg-[var(--accent-bg-subtle)] text-[var(--accent-text)] border border-[var(--accent-border-subtle)] flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">
                    {idx + 1}
                  </span>
                  <span>{action}</span>
                </div>
              ))}
            </div>

            {/* Latest run result */}
            {botRunResult && (
              <div className="mt-5 p-4 rounded-xl bg-slate-900 text-slate-100 font-mono text-xs overflow-x-auto">
                <span className="text-[var(--accent-text)] font-bold block mb-1">&gt; Bot Execution Output:</span>
                <pre>{JSON.stringify(botRunResult, null, 2)}</pre>
              </div>
            )}
          </GlassCard>
        </div>
      )}

      {/* TAB 3: RECORDS & ARTIFACTS */}
      {activeTab === 'records' && (
        <div className="space-y-6">
          {/* Duty 1: Payroll Artifacts */}
          {dutyKey === 'payroll_statutory' && (
            <GlassCard className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    Payroll Artifacts & Statutory Registers
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Download challans summary CSV or inspect printable HTML payslips.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <a
                    href={`${API_BASE}/api/duties/payroll_statutory/payslip/${persona.id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-800/70 hover:bg-white text-xs font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5 transition-colors"
                  >
                    <Printer className="w-4 h-4 text-[var(--accent-text)]" />
                    <span>Print My Payslip</span>
                  </a>
                  <a
                    href={`${API_BASE}/api/duties/payroll_statutory/challans-csv`}
                    className="px-3 py-1.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] border border-[var(--accent-border)] text-xs font-bold flex items-center gap-1.5 shadow-sm transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    <span>Challans CSV</span>
                  </a>
                </div>
              </div>
            </GlassCard>
          )}

          {/* Duty 2: Labour Compliance Registers */}
          {dutyKey === 'labour_compliance' && (
            <GlassCard className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    Statutory Labour Registers
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Export Form B (Wages Register) or Form D (Muster Roll) matching state regulations.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <a
                    href={`${API_BASE}/api/duties/labour_compliance/registers-csv?register_type=form_b_wages`}
                    className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-800/70 hover:bg-white text-xs font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5 transition-colors"
                  >
                    <Download className="w-4 h-4 text-[var(--accent-text)]" />
                    <span>Form B Wages (CSV)</span>
                  </a>
                  <a
                    href={`${API_BASE}/api/duties/labour_compliance/registers-csv?register_type=form_d_muster`}
                    className="px-3 py-1.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] border border-[var(--accent-border)] text-xs font-bold flex items-center gap-1.5 shadow-sm transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    <span>Form D Muster (CSV)</span>
                  </a>
                </div>
              </div>
            </GlassCard>
          )}

          {/* Duty 3: POSH Annual Return */}
          {dutyKey === 'posh' && poshReport && (
            <GlassCard className="p-6 space-y-4">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                  <span>Annual Statutory Return Summary ({poshReport.report_year})</span>
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Compiled strictly from aggregate incident counts per POSH Act 2013. Zero individual identities.
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-center">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Received</span>
                  <span className="text-xl font-extrabold text-slate-900 dark:text-white">{poshReport.aggregate_counts?.complaints_received}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-center">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Disposed</span>
                  <span className="text-xl font-extrabold text-emerald-600">{poshReport.aggregate_counts?.complaints_disposed}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-center">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Pending</span>
                  <span className="text-xl font-extrabold text-amber-600">{poshReport.aggregate_counts?.complaints_pending_total}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-center">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Sensitized</span>
                  <span className="text-xl font-extrabold text-[var(--accent-text)]">{poshReport.aggregate_counts?.employees_sensitized}</span>
                </div>
              </div>
            </GlassCard>
          )}

          {/* Duty 7: Attendance & Live Auto-Approval Simulation */}
          {dutyKey === 'attendance_leave' && (
            <GlassCard className="p-6 space-y-4">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-[var(--accent-text)]" />
                  <span>Test Leave Policy Auto-Approval Engine</span>
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Submit a leave request. Compliant requests (&le; 2 days, coverage &ge; 70%, sufficient balance) are auto-approved instantly!
                </p>
              </div>

              <form onSubmit={handleSimulateLeave} className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
                <div>
                  <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 block mb-1">Leave Type</label>
                  <select
                    value={leaveType}
                    onChange={(e) => setLeaveType(e.target.value)}
                    className="w-full text-xs p-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  >
                    <option value="casual">Casual Leave</option>
                    <option value="sick">Sick Leave</option>
                    <option value="earned">Earned Leave</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 block mb-1">Days Requested</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    max="10"
                    value={leaveDays}
                    onChange={(e) => setLeaveDays(e.target.value)}
                    className="w-full text-xs p-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-mono"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 block mb-1">Reason</label>
                  <input
                    type="text"
                    value={leaveReason}
                    onChange={(e) => setLeaveReason(e.target.value)}
                    className="w-full text-xs p-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                </div>

                <button
                  type="submit"
                  disabled={leaveSubmitting}
                  className="w-full p-2 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] border border-[var(--accent-border)] text-xs font-bold transition-all shadow-md shadow-[var(--accent-glow)] flex items-center justify-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{leaveSubmitting ? 'Evaluating...' : 'Submit & Test'}</span>
                </button>
              </form>

              {leaveFeedback && (
                <div className={`p-4 rounded-xl border text-xs ${
                  leaveFeedback.auto_approved
                    ? 'border-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-200'
                    : 'border-amber-300 bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-200'
                }`}>
                  <div className="flex items-center gap-2 font-bold">
                    {leaveFeedback.auto_approved ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                    )}
                    <span>{leaveFeedback.auto_approved ? 'AUTO-APPROVED BY POLICY ENGINE' : 'ROUTED TO MANAGER AS EXCEPTION'}</span>
                  </div>
                  <p className="mt-1">{leaveFeedback.message}</p>
                </div>
              )}
            </GlassCard>
          )}

          {/* Duty 9: Deterministic Policy Search */}
          {dutyKey === 'policies_records' && (
            <GlassCard className="p-6 space-y-4">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Search className="w-5 h-5 text-[var(--accent-text)]" />
                  <span>Deterministic Policy Library Search (No External AI)</span>
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Instant keyword search across published policies. Zero external model latency or cost.
                </p>
              </div>

              <form onSubmit={handleSearchPolicy} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Search policies (e.g., casual leave, harassment, 70% coverage)..."
                  value={policyQuery}
                  onChange={(e) => setPolicyQuery(e.target.value)}
                  className="flex-1 text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                />
                <button
                  type="submit"
                  disabled={policySearching}
                  className="px-4 py-2.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] border border-[var(--accent-border)] text-xs font-bold transition-all shadow-sm flex items-center gap-1.5"
                >
                  <Search className="w-4 h-4" />
                  <span>Search</span>
                </button>
              </form>

              {policyResults && (
                <div className="space-y-2 mt-3">
                  <span className="text-xs font-semibold text-slate-500">
                    Found {policyResults.length} matching sections:
                  </span>
                  {policyResults.map((m, idx) => (
                    <div key={idx} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700 text-xs">
                      <span className="font-bold text-slate-900 dark:text-white block">{m.title} ({m.version})</span>
                      <p className="text-slate-600 dark:text-slate-300 mt-0.5 font-mono text-[11px]">{m.snippet}</p>
                    </div>
                  ))}
                </div>
              )}
            </GlassCard>
          )}

          {/* General Completed Records Table */}
          <div className="solid-surface rounded-2xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 font-bold text-xs text-slate-800 dark:text-white uppercase tracking-wider">
              Approved & Completed Duty Records
            </div>
            {recordTasks.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500 dark:text-slate-400">
                No finalized records yet for this duty.
              </div>
            ) : (
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80 text-[11px] font-bold text-slate-500 uppercase">
                    <th className="py-3 px-4">Title</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Approved By</th>
                    <th className="py-3 px-4">Decision Note</th>
                    <th className="py-3 px-4">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-200">
                  {recordTasks.map((t) => (
                    <tr key={t.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40">
                      <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-white">{t.title}</td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          t.status === 'approved' ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700' : 'bg-rose-100 text-rose-700'
                        }`}>
                          {t.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-[11px]">{t.approver_id || 'System'}</td>
                      <td className="py-3.5 px-4 max-w-xs truncate">{t.decision_note || '-'}</td>
                      <td className="py-3.5 px-4 text-slate-400">{t.decided_at?.split('T')[0] || t.created_at?.split('T')[0]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Decision Confirmation Modal */}
      {decidingTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 w-full max-w-md rounded-2xl p-6 shadow-2xl relative">
            <h3 className="text-base font-bold text-slate-900 dark:text-white capitalize flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-[var(--accent-text)]" />
              <span>Confirm {decisionAction}</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              You are applying a human gate decision for: <strong>{decidingTask.title}</strong>
            </p>

            <div className="mt-4 space-y-2">
              <label className="text-[11px] font-bold text-slate-600 dark:text-slate-300 block">
                Decision Note / Justification (Logged to Tamper-Evident Ledger):
              </label>
              <textarea
                rows={3}
                value={decisionNote}
                onChange={(e) => setDecisionNote(e.target.value)}
                placeholder="Enter mandatory review note or confirmation details..."
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              />
            </div>

            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setDecidingTask(null)}
                className="px-3.5 py-1.5 rounded-xl border border-slate-300 dark:border-slate-700 hover:bg-slate-100 text-xs font-semibold text-slate-700 dark:text-slate-200"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isSubmittingDecision}
                onClick={handleConfirmDecision}
                className="px-4 py-1.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] border border-[var(--accent-border)] text-xs font-bold transition-all shadow-md shadow-[var(--accent-glow)] cursor-pointer"
              >
                {isSubmittingDecision ? 'Recording in Ledger...' : 'Confirm Decision'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
