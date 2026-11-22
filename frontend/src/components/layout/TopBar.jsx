import React, { useState, useEffect } from 'react';
import { Sun, Moon, ShieldAlert, ChevronDown, Check } from 'lucide-react';
import { getCurrentPersona, setPersona, PERSONAS, getSavedTheme, saveTheme } from '../../api';

export default function TopBar({ title = 'HR Self-Audit Assistant', onPersonaChange = null }) {
  const [theme, setTheme] = useState(getSavedTheme());
  const [persona, setCurrent] = useState(getCurrentPersona());
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    saveTheme(theme);
  }, [theme]);

  // Close dropdown on Escape key
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape' && menuOpen) {
        setMenuOpen(false);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [menuOpen]);

  function toggleTheme() {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    saveTheme(next);
  }

  function handleSelectPersona(p) {
    setPersona(p);
    setCurrent(p);
    setMenuOpen(false);
    if (onPersonaChange) onPersonaChange(p);
  }

  return (
    <header className="relative z-30 glass-panel rounded-2xl px-6 py-3.5 mb-6 flex items-center justify-between shadow-sm">
      {/* Title & DEV Mode Banner */}
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold text-slate-800 dark:text-white tracking-tight">
          {title}
        </h1>
        <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[var(--accent-bg-subtle)] text-[var(--accent-text)] border border-[var(--accent-border-subtle)]">
          <ShieldAlert className="w-3 h-3" />
          DEV mode active
        </span>
      </div>

      {/* Controls: Persona Switcher + Theme Toggle */}
      <div className="flex items-center gap-3">
        {/* Persona Switcher Dropdown */}
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className={`flex items-center gap-2.5 px-3 py-1.5 rounded-xl border transition-all text-xs font-medium focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none ${
              menuOpen
                ? 'border-[var(--accent)] bg-white dark:bg-slate-800 shadow-md ring-2 ring-[var(--accent)]/20'
                : 'border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 hover:bg-white dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 shadow-sm'
            }`}
            aria-expanded={menuOpen}
            aria-label="Switch active test persona"
          >
            <div className="w-6 h-6 rounded-full bg-[var(--accent)] text-[var(--accent-ink)] flex items-center justify-center font-bold text-[10px] shrink-0 shadow-sm shadow-[var(--accent-glow)]">
              {persona.id.substring(0, 3)}
            </div>
            <div className="text-left hidden sm:block">
              <span className="block font-semibold leading-tight text-slate-900 dark:text-white">{persona.name}</span>
              <span className="block text-[10px] text-slate-500 dark:text-slate-400 capitalize">{persona.role.replace('_', ' ')}</span>
            </div>
            <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${menuOpen ? 'rotate-180 text-[var(--accent-text)]' : ''}`} />
          </button>

          {menuOpen && (
            <>
              {/* Invisible Click-away Backdrop Layer */}
              <div
                className="fixed inset-0 z-40"
                onClick={() => setMenuOpen(false)}
                aria-hidden="true"
              />

              {/* Opaque Solid Dropdown Menu */}
              <div className="absolute right-0 mt-2.5 w-64 bg-white dark:bg-slate-900 rounded-2xl shadow-2xl py-2 z-50 border border-slate-200 dark:border-slate-700 ring-1 ring-black/5 dark:ring-white/10 animate-in fade-in zoom-in-95 duration-100">
                <div className="px-4 py-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                  <span>Switch Test Persona</span>
                  <span className="text-[9px] font-normal lowercase text-slate-400">role preview</span>
                </div>
                <div className="py-1">
                  {Object.values(PERSONAS).map((p) => {
                    const isSelected = persona.id === p.id;
                    return (
                      <button
                        key={p.id}
                        onClick={() => handleSelectPersona(p)}
                        className={`w-full text-left px-3.5 py-2.5 text-xs flex items-center justify-between transition-colors ${
                          isSelected
                            ? 'bg-[var(--accent-bg-subtle)] text-[var(--accent-text)] font-semibold'
                            : 'text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <div className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-[10px] shrink-0 ${
                            isSelected
                              ? 'bg-[var(--accent)] text-[var(--accent-ink)] shadow-sm'
                              : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                          }`}>
                            {p.id.substring(0, 3)}
                          </div>
                          <div>
                            <span className="font-semibold block leading-tight text-slate-900 dark:text-white">
                              {p.name}
                            </span>
                            <span className="text-[10px] text-slate-500 dark:text-slate-400 capitalize">
                              {p.role.replace('_', ' ')} &bull; {p.department}
                            </span>
                          </div>
                        </div>
                        {isSelected && <Check className="w-4 h-4 text-[var(--accent-text)] shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Theme Sun/Moon Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-white/80 dark:hover:bg-slate-800 transition-colors border border-slate-200 dark:border-slate-700 focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none shadow-sm"
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4 text-amber-400" />}
        </button>
      </div>
    </header>
  );
}
