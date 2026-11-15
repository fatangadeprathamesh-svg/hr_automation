import React from 'react';
import { AlertOctagon, X } from 'lucide-react';

export default function ErrorBanner({ message, onDismiss = null }) {
  if (!message) return null;

  return (
    <div className="rounded-xl border border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/40 p-4 mb-4 flex items-start justify-between text-rose-800 dark:text-rose-200">
      <div className="flex items-center gap-3">
        <AlertOctagon className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0" />
        <span className="text-sm font-medium">{message}</span>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-rose-500 hover:text-rose-700 dark:hover:text-rose-300 p-1 rounded-lg focus-visible:ring-2 focus-visible:ring-rose-500"
          aria-label="Dismiss error"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
