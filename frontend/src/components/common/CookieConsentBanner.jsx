import React, { useState, useEffect } from 'react';
import { Cookie, ShieldCheck, Settings } from 'lucide-react';
import { SITE_CONFIG } from '../../siteConfig';
import { getConsent, saveConsent, openCookiePreferences } from '../../utils/cookieConsent';
import CookiePreferencesModal from './CookiePreferencesModal';

export default function CookieConsentBanner() {
  const [showBanner, setShowBanner] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    // Check if consent has already been recorded and is valid
    const current = getConsent();
    if (!current) {
      setShowBanner(true);
    }

    // Listen for custom open event (e.g. from footer "Cookie settings")
    function handleOpenModal() {
      setIsModalOpen(true);
    }

    // Listen for consent changes
    function handleConsentChange(e) {
      if (e.detail) {
        setShowBanner(false);
      } else {
        setShowBanner(true);
      }
    }

    window.addEventListener('hr_open_cookie_modal', handleOpenModal);
    window.addEventListener('hr_consent_change', handleConsentChange);

    return () => {
      window.removeEventListener('hr_open_cookie_modal', handleOpenModal);
      window.removeEventListener('hr_consent_change', handleConsentChange);
    };
  }, []);

  function handleAcceptAll() {
    saveConsent({ preferences: true, analytics: true });
    setShowBanner(false);
  }

  function handleRejectNonEssential() {
    saveConsent({ preferences: false, analytics: false });
    setShowBanner(false);
  }

  function handleCustomize() {
    setIsModalOpen(true);
  }

  return (
    <>
      {/* Non-blocking bottom banner on first visit */}
      {showBanner && (
        <aside
          role="region"
          aria-label="Cookie and Privacy Consent"
          className="fixed bottom-4 left-4 right-4 sm:left-6 sm:right-6 md:left-auto md:right-8 md:max-w-2xl z-40 animate-in fade-in slide-in-from-bottom-5 duration-300"
        >
          <div className="glass-panel p-5 sm:p-6 rounded-3xl bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl border border-slate-200/90 dark:border-slate-700/90 shadow-2xl ring-1 ring-black/5 dark:ring-white/10">
            <div className="flex items-start gap-3.5">
              <div className="w-9 h-9 rounded-2xl bg-orange-100 dark:bg-orange-950/60 text-[#F26A21] flex items-center justify-center shrink-0 border border-orange-200/50 dark:border-orange-800/50">
                <Cookie className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                    Cookie &amp; Privacy Consent
                  </h3>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                    DPDP Act 2023 Compliant
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-1.5 leading-relaxed">
                  We use cookies and local storage to keep your session secure and, with your permission, remember theme preferences and test personas. We never use third-party advertising cookies or sell data.
                </p>

                {/* 3 Equally Prominent Buttons (No Dark Patterns) */}
                <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  <button
                    type="button"
                    onClick={handleAcceptAll}
                    className="w-full py-2 px-3 rounded-xl text-xs font-semibold text-slate-800 dark:text-white bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 transition-colors focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none text-center shadow-sm"
                  >
                    Accept all
                  </button>

                  <button
                    type="button"
                    onClick={handleRejectNonEssential}
                    className="w-full py-2 px-3 rounded-xl text-xs font-semibold text-slate-800 dark:text-white bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 transition-colors focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none text-center shadow-sm"
                  >
                    Reject non-essential
                  </button>

                  <button
                    type="button"
                    onClick={handleCustomize}
                    className="w-full py-2 px-3 rounded-xl text-xs font-semibold text-[#F26A21] bg-orange-50 hover:bg-orange-100 dark:bg-orange-950/40 dark:hover:bg-orange-900/50 border border-orange-200 dark:border-orange-800/60 transition-colors focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none text-center flex items-center justify-center gap-1.5 shadow-sm"
                  >
                    <Settings className="w-3.5 h-3.5" />
                    Customize
                  </button>
                </div>
              </div>
            </div>
          </div>
        </aside>
      )}

      {/* Accessible Preferences Modal */}
      <CookiePreferencesModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </>
  );
}
