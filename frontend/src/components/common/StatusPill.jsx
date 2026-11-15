import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, Clock, ShieldAlert } from 'lucide-react';

/**
 * StatusPill adhering to strict design system:
 * Green / Amber / Red ONLY for status.
 */
export default function StatusPill({ status, size = 'md' }) {
  const norm = (status || '').toLowerCase().replace(/_/g, ' ');

  let config = {
    bg: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
    icon: CheckCircle2,
    text: status || 'Resolved',
  };

  if (norm.includes('blocking') || norm.includes('fail') || norm.includes('rejected')) {
    config = {
      bg: 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800',
      icon: ShieldAlert,
      text: status || 'Blocking',
    };
  } else if (norm.includes('warning') || norm.includes('awaiting') || norm.includes('pending') || norm.includes('open')) {
    config = {
      bg: 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800',
      icon: norm.includes('awaiting') || norm.includes('pending') ? Clock : AlertTriangle,
      text: status || 'Warning',
    };
  } else if (norm.includes('resolved') || norm.includes('pass') || norm.includes('approved') || norm.includes('submitted')) {
    config = {
      bg: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
      icon: CheckCircle2,
      text: status || 'Resolved',
    };
  }

  const Icon = config.icon;
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-medium';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${config.bg} ${sizeClasses} font-medium tracking-wide`}
    >
      <Icon className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      <span>{config.text}</span>
    </span>
  );
}
