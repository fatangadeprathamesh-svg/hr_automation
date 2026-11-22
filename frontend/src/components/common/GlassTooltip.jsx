import React from 'react';

/**
 * Custom Glassmorphic Tooltip for Recharts.
 * Adheres to the blur and subtle border design system.
 */
export default function GlassTooltip({ active, payload, label, unit = '' }) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  return (
    <div className="glass-panel px-3.5 py-2.5 rounded-xl shadow-xl border border-white/60 dark:border-white/10 text-xs">
      {label && (
        <span className="block font-bold text-slate-800 dark:text-white mb-1">
          {label}
        </span>
      )}
      <div className="space-y-1">
        {payload.map((entry, index) => (
          <div key={`item-${index}`} className="flex items-center gap-2">
            <span
              className="w-2.5 h-2.5 rounded-full inline-block"
              style={{ backgroundColor: entry.color || entry.fill || 'var(--accent)' }}
            />
            <span className="text-slate-500 dark:text-slate-400 capitalize">
              {entry.name || 'Value'}:
            </span>
            <span className="font-mono font-bold text-slate-800 dark:text-white">
              {entry.value}
              {unit}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
