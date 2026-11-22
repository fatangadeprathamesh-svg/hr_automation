import React from 'react';
import StatusPill from './StatusPill';
import { HelpCircle, ChevronRight, Edit3 } from 'lucide-react';

/**
 * FlagsTable component.
 * Stays SOLID white/dark-slate (not glass) per design system specification.
 */
export default function FlagsTable({ flags = [], onSelectFlag = null, onExplainAI = null }) {
  if (!flags || flags.length === 0) {
    return null;
  }

  return (
    <div className="solid-surface rounded-2xl overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80 text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              <th className="py-3.5 px-4 sm:px-6">Status / Severity</th>
              <th className="py-3.5 px-4">Audit Rule & Issue</th>
              <th className="py-3.5 px-4 hidden sm:table-cell">Event Date</th>
              <th className="py-3.5 px-4 hidden md:table-cell">Forensic Evidence</th>
              <th className="py-3.5 px-4 sm:px-6 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-xs text-slate-700 dark:text-slate-200">
            {flags.map((flag) => {
              const isBlocking = flag.severity === 'BLOCKING';
              return (
                <tr
                  key={flag.id}
                  className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors"
                >
                  <td className="py-4 px-4 sm:px-6 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <StatusPill status={flag.status} size="sm" />
                      {isBlocking && (
                        <span className="text-[10px] font-bold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900 px-1.5 py-0.5 rounded">
                          BLOCKER
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <span className="block font-bold text-slate-900 dark:text-white">
                      {flag.title || flag.rule_name}
                    </span>
                    <span className="block text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1">
                      {flag.description}
                    </span>
                  </td>
                  <td className="py-4 px-4 font-mono text-[11px] text-slate-500 dark:text-slate-400 hidden sm:table-cell whitespace-nowrap">
                    {flag.date}
                  </td>
                  <td className="py-4 px-4 font-mono text-[11px] text-slate-600 dark:text-slate-300 hidden md:table-cell max-w-xs truncate">
                    {flag.evidence}
                  </td>
                  <td className="py-4 px-4 sm:px-6 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-2">
                      {onExplainAI && (
                        <button
                          type="button"
                          onClick={() => onExplainAI(flag)}
                          className="px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-[var(--accent)] hover:text-[var(--accent-text)] text-[11px] font-semibold flex items-center gap-1 transition-colors"
                          title="View plain-English rule explainer"
                        >
                          <HelpCircle className="w-3.5 h-3.5" />
                          <span>Explain</span>
                        </button>
                      )}
                      {onSelectFlag && flag.status !== 'Resolved' && (
                        <button
                          type="button"
                          onClick={() => onSelectFlag(flag)}
                          className="px-3 py-1 rounded-lg bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] border border-[var(--accent-border)] text-[11px] font-bold flex items-center gap-1 shadow-sm shadow-[var(--accent-glow)] transition-colors"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                          <span>Correct</span>
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
