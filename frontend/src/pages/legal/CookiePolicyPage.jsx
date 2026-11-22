import React from 'react';
import { Cookie, ShieldCheck, Sliders, CheckCircle2, Lock, RefreshCw } from 'lucide-react';
import LegalLayout from './LegalLayout';
import { SITE_CONFIG } from '../../siteConfig';
import { openCookiePreferences } from '../../utils/cookieConsent';

export default function CookiePolicyPage() {
  return (
    <LegalLayout
      title="Cookie Policy"
      subtitle="How Month-End HR Self-Audit Assistant uses cookies and local browser storage to manage sessions and preferences."
    >
      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <Cookie className="w-5 h-5 text-[#F26A21]" />
          1. What Are Cookies &amp; Local Storage?
        </h2>
        <p className="text-slate-600 dark:text-slate-300">
          Cookies and local storage are small data files placed on your browser when you visit a website. They are used to
          maintain active login sessions, remember user interface settings, and ensure the cryptographic integrity of client requests.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <Sliders className="w-5 h-5 text-[#F26A21]" />
          2. Categories of Storage We Use
        </h2>
        <p className="text-slate-600 dark:text-slate-300 mb-3">
          We only utilize first-party storage strictly required for system operation or explicitly consented by you:
        </p>

        <div className="space-y-3 text-xs">
          {/* Necessary */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <div className="flex items-center justify-between mb-1.5">
              <strong className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                {SITE_CONFIG.cookieCategories.necessary.name}
              </strong>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                Mandatory / Always Active
              </span>
            </div>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed mb-2">
              {SITE_CONFIG.cookieCategories.necessary.description}
            </p>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
              Keys: <code>hr_auth_token</code>, <code>hr_cookie_consent</code>, <code>hr_anonymous_id</code>
            </div>
          </div>

          {/* Preferences */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <div className="flex items-center justify-between mb-1.5">
              <strong className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
                <Sliders className="w-4 h-4 text-[#F26A21]" />
                {SITE_CONFIG.cookieCategories.preferences.name}
              </strong>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-600">
                Optional
              </span>
            </div>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed mb-2">
              {SITE_CONFIG.cookieCategories.preferences.description}
            </p>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
              Keys: <code>hr_theme</code>, <code>hr_current_persona</code>
            </div>
          </div>

          {/* Analytics */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <div className="flex items-center justify-between mb-1.5">
              <strong className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-sky-600 dark:text-sky-400" />
                {SITE_CONFIG.cookieCategories.analytics.name}
              </strong>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-600">
                Optional
              </span>
            </div>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed mb-2">
              {SITE_CONFIG.cookieCategories.analytics.description}
            </p>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <Lock className="w-5 h-5 text-[#F26A21]" />
          3. Third-Party Scripts &amp; Google Sign-In
        </h2>
        <p className="text-slate-600 dark:text-slate-300">
          We do not embed third-party advertising, remarketing, or tracking pixels. The Google Identity Services script
          (<code>accounts.google.com/gsi/client</code>) is <strong>never loaded on page load</strong>; it is fetched only
          on-demand if and when you explicitly click the "Sign in with Google" button.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-2">
          <RefreshCw className="w-5 h-5 text-[#F26A21]" />
          4. Managing &amp; Withdrawing Consent
        </h2>
        <p className="text-slate-600 dark:text-slate-300 mb-4">
          Your consent preferences are valid for 12 months or until the policy version updates. You can change your choices
          or withdraw consent at any time by clicking the button below or using the "Cookie settings" link in the footer.
        </p>
        <div>
          <button
            type="button"
            onClick={openCookiePreferences}
            className="px-5 py-2.5 rounded-xl text-xs font-bold bg-[#F26A21] hover:bg-[#dc5612] text-white shadow-md shadow-orange-500/25 transition-all focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none inline-flex items-center gap-2"
          >
            <Sliders className="w-4 h-4" />
            Open Cookie Preferences Modal
          </button>
        </div>
      </section>
    </LegalLayout>
  );
}
