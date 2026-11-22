import React, { useState, useEffect, useRef } from 'react';
import { X, ShieldCheck, Lock, Sliders, Check } from 'lucide-react';
import { SITE_CONFIG } from '../../siteConfig';
import { getConsent, saveConsent } from '../../utils/cookieConsent';

export default function CookiePreferencesModal({ isOpen, onClose }) {
  const [preferences, setPreferences] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const modalRef = useRef(null);
  const closeBtnRef = useRef(null);

  // Sync state with current consent when opened
  useEffect(() => {
    if (isOpen) {
      const consent = getConsent();
      if (consent?.choices) {
        setPreferences(Boolean(consent.choices.preferences));
        setAnalytics(Boolean(consent.choices.analytics));
      } else {
        setPreferences(false);
        setAnalytics(false);
      }
      // Focus modal close button for keyboard accessibility
      setTimeout(() => closeBtnRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Handle Escape key to close
  useEffect(() => {
    function handleKeyDown(e) {
      if (!isOpen) return;
      if (e.key === 'Escape') {
        onClose();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  function handleSave() {
    saveConsent({ preferences, analytics });
    onClose();
  }

  function handleAcceptAll() {
    saveConsent({ preferences: true, analytics: true });
    onClose();
  }

  function handleRejectNonEssential() {
    saveConsent({ preferences: false, analytics: false });
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cookie-preferences-title"
      aria-describedby="cookie-preferences-desc"
    >
      <div
        ref={modalRef}
        className="glass-panel w-full max-w-xl max-h-[90vh] overflow-y-auto rounded-3xl p-6 sm:p-8 shadow-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 relative focus:outline-none"
        tabIndex="-1"
      >
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-[var(--accent-bg-subtle)] text-[var(--accent-text)] flex items-center justify-center border border-[var(--accent-border-subtle)]">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h2
                id="cookie-preferences-title"
                className="text-lg font-bold text-slate-900 dark:text-white"
              >
                Cookie &amp; Privacy Preferences
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Policy Version {SITE_CONFIG.policyVersion} &bull; Updated {SITE_CONFIG.lastUpdated}
              </p>
            </div>
          </div>
          <button
            ref={closeBtnRef}
            onClick={onClose}
            aria-label="Close preferences modal"
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Intro */}
        <p id="cookie-preferences-desc" className="text-xs text-slate-600 dark:text-slate-300 mt-4 leading-relaxed">
          We use first-party browser storage to ensure site security and enable optional personalization.
          Under India's <strong>Digital Personal Data Protection Act 2023 (DPDP Act)</strong>, you have full control over
          non-essential preferences. We do not use third-party tracking or advertising cookies.
        </p>

        {/* Categories List */}
        <div className="mt-5 space-y-4">
          {/* Strictly Necessary */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <h3 className="text-sm font-semibold text-slate-800 dark:text-white">
                  {SITE_CONFIG.cookieCategories.necessary.name}
                </h3>
              </div>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                <Lock className="w-3 h-3" />
                Always Active
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 leading-relaxed">
              {SITE_CONFIG.cookieCategories.necessary.description}
            </p>
          </div>

          {/* Preferences */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-800 dark:text-white">
                  {SITE_CONFIG.cookieCategories.preferences.name}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">
                  {SITE_CONFIG.cookieCategories.preferences.description}
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={preferences}
                onClick={() => setPreferences(!preferences)}
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                  preferences ? 'bg-[var(--accent)]' : 'bg-slate-300 dark:bg-slate-700'
                }`}
              >
                <span className="sr-only">Toggle preferences cookies</span>
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
                    preferences ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Analytics */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-800 dark:text-white">
                  {SITE_CONFIG.cookieCategories.analytics.name}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">
                  {SITE_CONFIG.cookieCategories.analytics.description}
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={analytics}
                onClick={() => setAnalytics(!analytics)}
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                  analytics ? 'bg-[var(--accent)]' : 'bg-slate-300 dark:bg-slate-700'
                }`}
              >
                <span className="sr-only">Toggle analytics cookies</span>
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
                    analytics ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 pt-5 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              type="button"
              onClick={handleRejectNonEssential}
              className="flex-1 sm:flex-initial px-4 py-2 text-xs font-semibold rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none"
            >
              Reject non-essential
            </button>
            <button
              type="button"
              onClick={handleAcceptAll}
              className="flex-1 sm:flex-initial px-4 py-2 text-xs font-semibold rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none"
            >
              Accept all
            </button>
          </div>

          <button
            type="button"
            onClick={handleSave}
            className="w-full sm:w-auto px-5 py-2 text-xs font-bold rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-[var(--accent-ink)] border border-[var(--accent-border)] shadow-md shadow-[var(--accent-glow)] transition-all focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none flex items-center justify-center gap-1.5"
          >
            <Check className="w-3.5 h-3.5" />
            Save preferences
          </button>
        </div>
      </div>
    </div>
  );
}
