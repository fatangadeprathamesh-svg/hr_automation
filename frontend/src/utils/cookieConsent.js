import { SITE_CONFIG } from '../siteConfig.js';
import { API_BASE } from '../api.js';

const CONSENT_STORAGE_KEY = 'hr_cookie_consent';
const ANONYMOUS_ID_KEY = 'hr_anonymous_id';
const TWELVE_MONTHS_MS = 365 * 24 * 60 * 60 * 1000;

/**
 * Returns a stable, anonymous client UUID stored in localStorage.
 * Strictly used for consent audit trail under the DPDP Act 2023.
 */
export function getAnonymousId() {
  let anonId = localStorage.getItem(ANONYMOUS_ID_KEY);
  if (!anonId) {
    anonId = 'anon-' + Math.random().toString(36).substring(2, 11) + '-' + Date.now().toString(36);
    try {
      localStorage.setItem(ANONYMOUS_ID_KEY, anonId);
    } catch (_) {}
  }
  return anonId;
}

/**
 * Reads stored consent from localStorage.
 * Returns null if not set, expired (>12 months), or policy version has changed.
 */
export function getConsent() {
  try {
    const raw = localStorage.getItem(CONSENT_STORAGE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw);
    if (!parsed || !parsed.choices) return null;

    // Check version match
    if (parsed.version !== SITE_CONFIG.policyVersion) {
      return null;
    }

    // Check 12-month expiry
    if (Date.now() - parsed.timestamp > TWELVE_MONTHS_MS) {
      return null;
    }

    return parsed;
  } catch (e) {
    return null;
  }
}

/**
 * Save cookie consent choices locally and asynchronously log proof to the backend.
 */
export function saveConsent(choices) {
  const payload = {
    version: SITE_CONFIG.policyVersion,
    timestamp: Date.now(),
    choices: {
      necessary: true,
      preferences: Boolean(choices.preferences),
      analytics: Boolean(choices.analytics),
    },
  };

  try {
    localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(payload));
  } catch (_) {}

  // Apply preference rules: if preferences consent is revoked, purge persisted theme from localStorage
  if (!payload.choices.preferences) {
    const currentTheme = localStorage.getItem('hr_theme');
    if (currentTheme) {
      sessionStorage.setItem('hr_theme', currentTheme);
      localStorage.removeItem('hr_theme');
    }
  }

  // Notify active listeners
  window.dispatchEvent(new CustomEvent('hr_consent_change', { detail: payload }));

  // Asynchronously record proof on backend
  try {
    const anonId = getAnonymousId();
    fetch(`${API_BASE}/api/consent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        anonymous_id: anonId,
        policy_version: payload.version,
        choices: payload.choices,
      }),
    }).catch((err) => {
      console.warn('Backend consent logging notice:', err);
    });
  } catch (_) {}

  return payload;
}

/**
 * Check whether a category has active consent.
 */
export function hasConsent(category) {
  if (category === 'necessary') return true;
  const consent = getConsent();
  if (!consent) return false;
  return Boolean(consent.choices && consent.choices[category]);
}

/**
 * Reopen preferences modal from anywhere (e.g. footer button).
 */
export function openCookiePreferences() {
  window.dispatchEvent(new CustomEvent('hr_open_cookie_modal'));
}

/**
 * Clear consent (useful for testing and reset buttons).
 */
export function clearConsent() {
  localStorage.removeItem(CONSENT_STORAGE_KEY);
  window.dispatchEvent(new CustomEvent('hr_consent_change', { detail: null }));
}
