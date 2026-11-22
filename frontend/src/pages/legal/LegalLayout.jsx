import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Sun, Moon, AlertTriangle, ShieldCheck, FileText, FileSearch } from 'lucide-react';
import { SITE_CONFIG } from '../../siteConfig';
import { getSavedTheme, saveTheme } from '../../api';
import Footer from '../../components/layout/Footer';

export default function LegalLayout({ title, subtitle, children }) {
  const navigate = useNavigate();
  const [theme, setTheme] = useState(getSavedTheme());

  function toggleTheme() {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    saveTheme(next);
  }

  return (
    <div className="min-h-screen app-gradient-bg flex flex-col justify-between">
      {/* Top Navigation Bar */}
      <header className="w-full border-b border-slate-200/80 dark:border-slate-800/80 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="p-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
              title="Go back"
              aria-label="Go back to previous page"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <Link to="/employee" className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-[#F26A21] flex items-center justify-center text-white shadow-sm shadow-orange-500/30">
                <FileSearch className="w-4 h-4" />
              </div>
              <span className="font-bold text-sm text-slate-900 dark:text-white hidden sm:inline">
                {SITE_CONFIG.productName}
              </span>
            </Link>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={toggleTheme}
              className="p-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-slate-700 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
              title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
              aria-label="Toggle theme"
            >
              {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4 text-amber-400" />}
            </button>
            <Link
              to="/login"
              className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-[#F26A21] hover:bg-[#dc5612] text-white shadow-sm shadow-orange-500/20 transition-all focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
            >
              Sign In
            </Link>
          </div>
        </div>
      </header>

      {/* Main Legal Content Container */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8">
        {/* Visible Legal Disclaimer Notice */}
        <div className="mb-6 p-4 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/70 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-800 dark:text-amber-200">
            <strong className="font-semibold block mb-0.5">Notice &amp; Disclaimer:</strong>
            Template text, not legal advice; get legal review before production use. All employee profiles,
            attendance events, and financial figures displayed in this application are fictitious demo data
            created for the Homingo Hack Days 2026 prototype.
          </div>
        </div>

        {/* Page Header */}
        <div className="glass-panel p-6 sm:p-8 rounded-3xl bg-white/80 dark:bg-slate-900/80 border border-slate-200/80 dark:border-slate-800/80 shadow-sm mb-6">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-orange-100 dark:bg-orange-950/60 text-[#F26A21] border border-orange-200/60 dark:border-orange-800/60">
              <ShieldCheck className="w-3.5 h-3.5" />
              Policy Version {SITE_CONFIG.policyVersion}
            </span>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Last updated: {SITE_CONFIG.lastUpdated}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white mt-4 tracking-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="text-sm text-slate-600 dark:text-slate-300 mt-2 leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>

        {/* Content Body */}
        <article className="glass-panel p-6 sm:p-10 rounded-3xl bg-white/90 dark:bg-slate-900/90 border border-slate-200/80 dark:border-slate-800/80 shadow-sm text-slate-800 dark:text-slate-200 space-y-6 text-sm leading-relaxed">
          {children}
        </article>
      </main>

      {/* Global Footer */}
      <div className="max-w-5xl mx-auto w-full px-4 sm:px-6">
        <Footer />
      </div>
    </div>
  );
}
