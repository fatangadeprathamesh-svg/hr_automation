import React from 'react';
import { PERSONAS } from '../api';

export default function Navbar({ currentPersona, onSelectPersona }) {
  return (
    <header className="bg-slate-900 text-white shadow-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center font-black text-white text-lg">
            HR
          </div>
          <div>
            <h1 className="font-bold text-sm tracking-tight">Month-End HR Self-Audit Assistant</h1>
            <p className="text-[10px] text-slate-400">Deterministic Compliance & Correction Ledger</p>
          </div>
        </div>

        {/* Persona / Role Switcher for pairwise testing */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 hidden sm:inline">Active Persona:</span>
          <div className="flex bg-slate-800 p-1 rounded-lg border border-slate-700">
            {Object.values(PERSONAS).map((p) => {
              const active = currentPersona.id === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => onSelectPersona(p)}
                  className={`px-3 py-1 rounded text-xs font-semibold transition ${
                    active
                      ? 'bg-brand-600 text-white shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {p.name} ({p.role.toUpperCase()})
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </header>
  );
}
