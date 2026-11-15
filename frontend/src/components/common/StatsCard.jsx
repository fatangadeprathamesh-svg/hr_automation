import React from 'react';
import GlassCard from './GlassCard';

export default function StatsCard({ title, value, subtitle, icon: Icon, color = 'accent', trend = null }) {
  const colorMap = {
    accent: 'text-[#F26A21] bg-orange-100/60 dark:bg-orange-950/40 border-orange-200/50',
    green: 'text-emerald-600 bg-emerald-100/60 dark:bg-emerald-950/40 border-emerald-200/50',
    amber: 'text-amber-600 bg-amber-100/60 dark:bg-amber-950/40 border-amber-200/50',
    red: 'text-rose-600 bg-rose-100/60 dark:bg-rose-950/40 border-rose-200/50',
    blue: 'text-sky-600 bg-sky-100/60 dark:bg-sky-950/40 border-sky-200/50',
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
