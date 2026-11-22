import React from 'react';
import GlassCard from './GlassCard';

export default function StatsCard({ title, value, subtitle, icon: Icon, color = 'accent', trend = null }) {
  const colorMap = {
    accent: 'text-[var(--accent-text)] bg-[var(--accent-bg-subtle)] border-[var(--accent-border-subtle)]',
    green: 'text-[var(--status-success)] bg-[var(--status-success-bg)] border-[var(--status-success-border)]',
    amber: 'text-[var(--status-warning)] bg-[var(--status-warning-bg)] border-[var(--status-warning-border)]',
    red: 'text-[var(--status-error)] bg-[var(--status-error-bg)] border-[var(--status-error-border)]',
    blue: 'text-[var(--status-info)] bg-[var(--status-info-bg)] border-[var(--status-info-border)]',
  };

  const badgeStyle = colorMap[color] || colorMap.accent;

  return (
    <GlassCard className="flex flex-col justify-between hover:shadow-xl transition-all duration-200">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          {title}
        </span>
        {Icon && (
          <div className={`p-2.5 rounded-xl border ${badgeStyle}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      <div className="mt-4 flex items-baseline gap-2">
        <span className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          {value}
        </span>
        {trend && (
          <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400 flex items-center">
            {trend}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          {subtitle}
        </p>
      )}
    </GlassCard>
  );
}
