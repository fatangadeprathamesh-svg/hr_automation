import assert from 'node:assert';
import { SITE_CONFIG } from './src/siteConfig.js';

// Polyfill window and localStorage/sessionStorage for Node environment
class MemoryStorage {
  constructor() {
    this.store = {};
  }
  getItem(key) {
    return this.store[key] !== undefined ? this.store[key] : null;
  }
  setItem(key, value) {
    this.store[key] = String(value);
  }
  removeItem(key) {
    delete this.store[key];
  }
  clear() {
    this.store = {};
  }
}

global.localStorage = new MemoryStorage();
global.sessionStorage = new MemoryStorage();
global.window = {
  dispatchEvent: () => {},
};

// Import consent utilities
const {
  getConsent,
  saveConsent,
  hasConsent,
  clearConsent,
} = await import('./src/utils/cookieConsent.js');

console.log('--- Running Cookie Consent Unit Tests ---');

// Test 1: Initial visit before choice -> banner must be shown (getConsent returns null)
clearConsent();
assert.strictEqual(getConsent(), null, 'Test 1 Failed: getConsent should be null on first visit');
assert.strictEqual(hasConsent('necessary'), true, 'Test 1 Failed: necessary should always be permitted');
assert.strictEqual(hasConsent('preferences'), false, 'Test 1 Failed: preferences should be false before choice');
assert.strictEqual(hasConsent('analytics'), false, 'Test 1 Failed: analytics should be false before choice');
console.log('✓ Test 1: First visit shows banner and loads no optional cookies');

// Test 2: Reject non-essential stores no optional cookies
localStorage.setItem('hr_theme', 'dark'); // User might have had a pre-existing theme
const rejectResult = saveConsent({ preferences: false, analytics: false });
assert.strictEqual(rejectResult.choices.necessary, true);
assert.strictEqual(rejectResult.choices.preferences, false);
assert.strictEqual(rejectResult.choices.analytics, false);

const storedReject = getConsent();
assert.notStrictEqual(storedReject, null, 'Test 2 Failed: consent should be saved');
assert.strictEqual(storedReject.choices.preferences, false, 'Preferences must be false');
assert.strictEqual(storedReject.choices.analytics, false, 'Analytics must be false');
assert.strictEqual(localStorage.getItem('hr_theme'), null, 'Persistent hr_theme in localStorage must be cleared');
assert.strictEqual(sessionStorage.getItem('hr_theme'), 'dark', 'Session theme must be preserved in sessionStorage');
console.log('✓ Test 2: Reject non-essential stores no optional cookies and downgrades theme to session-only');

// Test 3: The banner does not reappear after a choice
assert.notStrictEqual(getConsent(), null, 'Test 3 Failed: getConsent is not null, so banner does not reappear');
console.log('✓ Test 3: Banner does not reappear after choice is recorded');

// Test 4: Accept all stores all three categories
const acceptResult = saveConsent({ preferences: true, analytics: true });
assert.strictEqual(acceptResult.choices.necessary, true);
assert.strictEqual(acceptResult.choices.preferences, true);
assert.strictEqual(acceptResult.choices.analytics, true);

const storedAccept = getConsent();
assert.strictEqual(storedAccept.choices.necessary, true);
assert.strictEqual(storedAccept.choices.preferences, true);
assert.strictEqual(storedAccept.choices.analytics, true);
assert.strictEqual(hasConsent('preferences'), true);
assert.strictEqual(hasConsent('analytics'), true);
console.log('✓ Test 4: Accept all stores all three categories');

// Test 5: The banner reappears when the version changes
const oldConsent = {
  version: '2025.9-outdated',
  timestamp: Date.now(),
  choices: { necessary: true, preferences: true, analytics: true },
};
localStorage.setItem('hr_cookie_consent', JSON.stringify(oldConsent));
assert.strictEqual(getConsent(), null, 'Test 5 Failed: version mismatch must return null so banner reappears');
console.log('✓ Test 5: The banner reappears when policy version changes');

// Test 6: The banner reappears after 12 months (> 365 days)
const thirteenMonthsAgo = Date.now() - (366 * 24 * 60 * 60 * 1000);
const expiredConsent = {
  version: SITE_CONFIG.policyVersion,
  timestamp: thirteenMonthsAgo,
  choices: { necessary: true, preferences: true, analytics: true },
};
localStorage.setItem('hr_cookie_consent', JSON.stringify(expiredConsent));
assert.strictEqual(getConsent(), null, 'Test 6 Failed: expired consent (>12 months) must return null');
console.log('✓ Test 6: The banner reappears after 12 months (365 days)');

console.log('All 6 Cookie Consent Frontend Tests Passed Successfully!');
