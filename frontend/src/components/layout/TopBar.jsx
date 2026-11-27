import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sun, Moon, ShieldAlert, ChevronDown, Check } from 'lucide-react';
import { getCurrentPersona, setPersona, PERSONAS, getSavedTheme, saveTheme, checkBackendHealth, getRoleHome, subscribeApiError } from '../../api';

export default function TopBar({ title = 'HR Self-Audit Assistant', onPersonaChange = null }) {
  const navigate = useNavigate();
  const [theme, setTheme] = useState(getSavedTheme());
  const [persona, setCurrent] = useState(getCurrentPersona());
  const [menuOpen, setMenuOpen] = useState(false);
  const [backendStatus, setBackendStatus] = useState({ checked: false, online: false });
  const [recentError, setRecentError] = useState(null);

  useEffect(() => {
    saveTheme(theme);
  }, [theme]);

  // Subscribe to recent API failures
  useEffect(() => {
    const unsubscribe = subscribeApiError((err) => {
      setRecentError(err);
      setTimeout(() => {
        setRecentError(null);
      }, 15000);
    });
    return unsubscribe;
  }, []);

  // Check backend health on mount and periodically
  useEffect(() => {
    let active = true;
    async function checkHealth() {
      const res = await checkBackendHealth();
      if (active) {
        setBackendStatus({ checked: true, online: res.online, ...res });
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

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
    navigate(getRoleHome(p.role));
  }

  const getInitials = (p) => {
    if (p?.name) {
      return p.name.split(' ').map((n) => n[0]).join('').substring(0, 2).toUpperCase();
    }
    return (p?.id || 'HR').substring(0, 2);
  };

  const uniquePersonas = Array.from(new Map(Object.values(PERSONAS).map((p) => [p.id, p])).values());

  return (
    <header className="relative z-30 glass-panel rounded-2xl px-6 py-3.5 mb-6 flex items-center justify-between shadow-sm">
      {/* Title & DEV Mode Banner */}
      <div className="flex items-center gap-2.5 sm:gap-3 flex-wrap">
        <h1 className="text-lg font-bold text-slate-800 dark:text-white tracking-tight">
          {title}
        </h1>
        <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[var(--accent-bg-subtle)] text-[var(--accent-text)] border border-[var(--accent-border-subtle)]">
          <ShieldAlert className="w-3 h-3" />
          DEV mode active
        </span>

        {/* Backend Online/Offline & Request Error Status Indicator */}
        <span
          title={
            !backendStatus.online
              ? 'Backend is Offline (Cannot reach http://127.0.0.1:8000/api/health)'
              : recentError
              ? `Backend is online but recently reported an error: ${recentError.message}`
              : `Backend is Online at 127.0.0.1:8000 (Database: ${backendStatus.db || 'connected'})`
          }
          className={`hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border transition-all ${
            !backendStatus.online
              ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'
              : recentError
              ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
              : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              !backendStatus.online
                ? 'bg-rose-500'
                : recentError
                ? 'bg-amber-500 animate-pulse'
                : 'bg-emerald-500 animate-pulse'
            }`}
          />
          <span>
            {!backendStatus.online
              ? 'Backend Offline'
              : recentError
              ? 'Backend Issues'
              : 'Backend Online'}
          </span>
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
            <div className="w-7 h-7 rounded-full bg-[var(--accent)] text-[var(--accent-ink)] flex items-center justify-center font-bold text-[11px] shrink-0 shadow-sm shadow-[var(--accent-glow)]">
              {getInitials(persona)}
            </div>
            <div className="text-left hidden sm:block">
              <span className="block font-semibold leading-tight text-slate-900 dark:text-white">
                {persona?.name || 'User'} <span className="font-mono text-[10px] text-[var(--accent-text)] font-bold">({persona?.id || ''})</span>
              </span>
              <span className="block text-[10px] text-slate-500 dark:text-slate-400 capitalize">
                {(persona?.role || 'employee').replace('_', ' ')}
              </span>
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
                  {uniquePersonas.map((p) => {
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
                            {getInitials(p)}
                          </div>
                          <div>
                            <span className="font-semibold block leading-tight text-slate-900 dark:text-white">
                              {p.name} <span className="font-mono text-[10px] text-[var(--accent-text)]">({p.id})</span>
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
