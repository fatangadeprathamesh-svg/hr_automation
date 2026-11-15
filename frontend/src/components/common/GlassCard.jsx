import React from 'react';

/**
 * Reusable GlassCard component.
 * Uses backdrop blur with 60-75% opacity and graceful solid fallback.
 */
export default function GlassCard({ children, className = '', padding = 'p-6', onClick = null }) {
  return (
    <div
      onClick={onClick}
      className={`glass-panel rounded-2xl transition-all duration-200 ${padding} ${className}`}
    >
      {children}
    </div>
  );
}
