import React from 'react';
import { Link } from 'react-router-dom';
import { Cookie, ShieldCheck, Heart } from 'lucide-react';
import { SITE_CONFIG } from '../../siteConfig';
import { openCookiePreferences } from '../../utils/cookieConsent';

export default function Footer({ className = '' }) {
  return (
    <footer
      className={`mt-12 pt-6 pb-6 border-t border-slate-200/70 dark:border-slate-800/70 text-xs text-slate-500 dark:text-slate-400 w-full transition-colors ${className}`}
      role="contentinfo"
      aria-label="Site footer"
    >
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Left: Copyright & Prototype Notice */}
        <div className="flex flex-col items-center md:items-start gap-1 text-center md:text-left">
          <p className="font-medium text-slate-700 dark:text-slate-300">
            &copy; {SITE_CONFIG.year} {SITE_CONFIG.ownerName}. All rights reserved.
          </p>
          <p className="text-[11px] text-slate-400 dark:text-slate-500 flex items-center gap-1">
            <span>{SITE_CONFIG.hackathonNote}</span>
          </p>
        </div>

        {/* Right: Legal Links & Cookie Settings */}
        <nav
          className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs"
          aria-label="Legal and cookie navigation"
        >
          <Link
            to="/privacy"
            className="hover:text-[#F26A21] dark:hover:text-[#F26A21] transition-colors focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none rounded-md px-1 py-0.5"
          >
            Privacy Policy
          </Link>
          <span className="text-slate-300 dark:text-slate-700" aria-hidden="true">&bull;</span>
          <Link
            to="/terms"
            className="hover:text-[#F26A21] dark:hover:text-[#F26A21] transition-colors focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none rounded-md px-1 py-0.5"
          >
            Terms of Use
          </Link>
          <span className="text-slate-300 dark:text-slate-700" aria-hidden="true">&bull;</span>
          <Link
            to="/cookies"
            className="hover:text-[#F26A21] dark:hover:text-[#F26A21] transition-colors focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none rounded-md px-1 py-0.5"
          >
            Cookie Policy
          </Link>
          <span className="text-slate-300 dark:text-slate-700" aria-hidden="true">&bull;</span>
          <Link
            to="/contact"
            className="hover:text-[#F26A21] dark:hover:text-[#F26A21] transition-colors focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none rounded-md px-1 py-0.5"
          >
            Contact
          </Link>
          <span className="text-slate-300 dark:text-slate-700" aria-hidden="true">&bull;</span>
          <button
            type="button"
            onClick={openCookiePreferences}
            className="inline-flex items-center gap-1 font-medium text-[#F26A21] hover:text-[#dc5612] transition-colors focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none rounded-md px-1 py-0.5"
            aria-label="Open cookie preferences modal"
          >
            <Cookie className="w-3.5 h-3.5" />
            Cookie settings
          </button>
        </nav>
      </div>
    </footer>
  );
}
