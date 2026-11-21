import React, { useEffect, useState } from 'react';

/**
 * Animated ReadinessRing component with glassmorphic backing.
 * Animates smoothly as issues are fixed (e.g., 78% to 100%).
 */
export default function ReadinessRing({ percentage = 78, size = 180, strokeWidth = 14, label = 'Audit Readiness' }) {
  const [animatedValue, setAnimatedValue] = useState(0);

  useEffect(() => {
    // Smooth number animation
    let start = 0;
    const duration = 800;
    const stepTime = 16;
    const steps = duration / stepTime;
    const increment = (percentage - start) / steps;

    const timer = setInterval(() => {
      start += increment;
      if ((increment > 0 && start >= percentage) || (increment < 0 && start <= percentage)) {
        setAnimatedValue(percentage);
        clearInterval(timer);
      } else {
        setAnimatedValue(Math.round(start));
      }
    }, stepTime);

    return () => clearInterval(timer);
  }, [percentage]);

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (animatedValue / 100) * circumference;

  // Status color: Accent #F26A21 when in progress, Emerald #10B981 when 100% complete
  const strokeColor = percentage === 100 ? '#10B981' : percentage >= 80 ? '#F26A21' : '#F59E0B';

  return (
    <div className="relative inline-flex flex-col items-center justify-center p-4">
      {/* Glassmorphic backdrop container for ring */}
      <div
        className="glass-panel rounded-full flex items-center justify-center shadow-lg transition-transform hover:scale-[1.02]"
        style={{ width: size + 24, height: size + 24 }}
      >
        <svg width={size} height={size} className="transform -rotate-90">
          {/* Background track circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-slate-200/70 dark:text-slate-700/50"
            fill="transparent"
          />
          {/* Animated progress ring */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            className="transition-all duration-700 ease-out"
          />
        </svg>

        {/* Center label inside ring */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
          <span className="text-3xl font-extrabold text-slate-800 dark:text-white tracking-tight">
            {animatedValue}%
          </span>
          <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mt-0.5">
            {percentage === 100 ? 'Ready to Submit' : 'Needs Review'}
          </span>
        </div>
      </div>

      <span className="mt-3 text-xs font-semibold text-slate-600 dark:text-slate-300">
        {label}
      </span>
    </div>
  );
}
