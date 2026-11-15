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
    <header className="glass-panel rounded-2xl px-6 py-3.5 mb-6 flex items-center justify-between shadow-sm">
      {/* Title & DEV Mode Banner */}
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold text-slate-800 dark:text-white tracking-tight">
          {title}
        </h1>
        <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-orange-100 dark:bg-orange-950/60 text-[#F26A21] border border-orange-200/60 dark:border-orange-800/60">
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
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-slate-800/70 text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
            aria-expanded={menuOpen}
            aria-label="Switch active test persona"
          >
            <div className="w-6 h-6 rounded-full bg-[#F26A21] text-white flex items-center justify-center font-bold text-[10px]">
              {persona.id.substring(0, 3)}
            </div>
            <div className="text-left hidden sm:block">
              <span className="block font-semibold leading-tight">{persona.name}</span>
              <span className="block text-[10px] text-slate-400 capitalize">{persona.role.replace('_', ' ')}</span>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 mt-2 w-52 glass-panel rounded-xl shadow-xl py-1 z-50 border border-slate-200 dark:border-slate-700">
              <div className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 dark:border-slate-800">
                Switch Test Persona
              </div>
              {Object.values(PERSONAS).map((p) => (
                <button
                  key={p.id}
                  onClick={() => handleSelectPersona(p)}
                  className="w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-orange-50 dark:hover:bg-slate-800/80 transition-colors"
                >
                  <div>
                    <span className="font-semibold text-slate-800 dark:text-slate-200 block">{p.name}</span>
                    <span className="text-[10px] text-slate-400 capitalize">{p.role.replace('_', ' ')} &bull; {p.id}</span>
                  </div>
                  {persona.id === p.id && <Check className="w-4 h-4 text-[#F26A21]" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Theme Sun/Moon Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-white/70 dark:hover:bg-slate-800 transition-colors border border-slate-200 dark:border-slate-700 focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4 text-amber-400" />}
        </button>
      </div>
    </header>
  );
}
