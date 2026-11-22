import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileSearch, ArrowRight, ShieldCheck, Mail, Lock, User, Sparkles } from 'lucide-react';
import { login, googleSignIn } from '../api';
import ErrorBanner from '../components/common/ErrorBanner';
import Footer from '../components/layout/Footer';

export default function LoginPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0); // 0 = Sign in, 1 = Create an account
  const [email, setEmail] = useState('alice@company.com');
  const [password, setPassword] = useState('Password123!');
  const [fullName, setFullName] = useState('Alice Employee');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const googleClientId =
    import.meta.env.VITE_GOOGLE_CLIENT_ID ||
    '486438249549-gopbgo082hs530rll93dmr1p76cdafac.apps.googleusercontent.com';

  // Dynamically load Google Identity Services only when user explicitly clicks "Continue with Google"
  function loadGoogleScript(onReady) {
    if (window.google?.accounts?.id) {
      onReady();
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => onReady();
    script.onerror = () => {
      console.warn('Google Identity Services script failed to load. Using fallback.');
      onReady();
    };
    document.head.appendChild(script);
  }

  async function handleGoogleCredentialResponse(response) {
    setLoading(true);
    setError(null);
    try {
      const res = await googleSignIn({ credential: response.credential });
      if (res.requiresOtp) {
        navigate('/verify-otp', {
          state: {
            email: res.email,
            devCode: res.devCode,
            requiresOtp: true,
          },
        });
      } else {
        const role = res.role || res.persona?.role || 'employee';
        if (role === 'hr_admin' || role === 'hr') navigate('/hr');
        else if (role === 'manager') navigate('/manager');
        else navigate('/employee');
      }
    } catch (err) {
      setError(err.message || 'Google sign-in failed');
    } finally {
      setLoading(false);
    }
  }

  function handleCustomGoogleClick() {
    setLoading(true);
    setError(null);
    loadGoogleScript(() => {
      if (window.google?.accounts?.id && googleClientId) {
        try {
          window.google.accounts.id.initialize({
            client_id: googleClientId,
            callback: handleGoogleCredentialResponse,
            auto_select: false,
          });
          window.google.accounts.id.prompt();
          setLoading(false);
          return;
        } catch (e) {
          console.warn('GIS prompt notice:', e);
        }
      }
      // DEV fallback token for fast automated / offline testing
      handleGoogleCredentialResponse({
        credential: `MOCK_GOOGLE_TOKEN_FOR_${email || 'alice@company.com'}`,
      });
    });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await login({
        email,
        password,
        fullName: activeTab === 1 ? fullName : '',
        isSignUp: activeTab === 1,
      });

      // Pass devCode if returned for immediate testing visibility
      const devParam = res.dev_code ? `&devCode=${res.dev_code}` : '';
      navigate(`/verify?email=${encodeURIComponent(email)}${devParam}`);
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e, tabIndex) {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      setActiveTab(tabIndex === 0 ? 1 : 0);
    }
  }

  return (
    <div className="min-h-screen app-gradient-bg flex flex-col justify-between items-center p-4 sm:p-6">
      <div className="w-full max-w-md my-auto flex flex-col items-center">
        {/* Brand Header */}
      <div className="mb-6 text-center">
        <div className="w-14 h-14 rounded-2xl bg-[var(--accent)] text-[var(--accent-ink)] flex items-center justify-center mx-auto shadow-lg shadow-[var(--accent)]/20 mb-3">
          <FileSearch className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-extrabold text-slate-800 dark:text-white tracking-tight">
          HR Self-Audit Assistant
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Automated month-end compliance &bull; Deterministic rules &bull; Immutable audit ledger
        </p>
      </div>

      {/* Main Glassmorphic Auth Card */}
      <div className="glass-panel w-full max-w-md rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        {/* Sliding Gold Blade Navigation */}
        <div className="relative mb-6">
          {/* Background track for tabs */}
          <div
            className="flex relative p-1 bg-slate-200/60 dark:bg-slate-800/60 rounded-2xl"
            role="tablist"
            aria-label="Authentication mode"
          >
            {/* Sliding gold blade (Desktop / Tablets) */}
            <div
              className="absolute top-1 bottom-1 rounded-xl bg-[var(--accent)] shadow-md shadow-[var(--accent)]/20 transition-transform duration-300 ease-out hidden sm:block"
              style={{
                width: 'calc(50% - 4px)',
                transform: activeTab === 0 ? 'translateX(0%)' : 'translateX(100%)',
              }}
              aria-hidden="true"
            />

            {/* Tab 1: Sign in */}
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 0}
              tabIndex={0}
              onClick={() => setActiveTab(0)}
              onKeyDown={(e) => handleKeyDown(e, 0)}
              className={`flex-1 py-2.5 text-xs font-bold rounded-xl relative z-10 transition-colors text-center focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none ${
                activeTab === 0
                  ? 'text-[var(--accent-ink)] sm:text-[var(--accent-ink)] bg-[var(--accent)] sm:bg-transparent shadow-sm sm:shadow-none'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              Sign in
            </button>

            {/* Tab 2: Create an account */}
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 1}
              tabIndex={0}
              onClick={() => setActiveTab(1)}
              onKeyDown={(e) => handleKeyDown(e, 1)}
              className={`flex-1 py-2.5 text-xs font-bold rounded-xl relative z-10 transition-colors text-center focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none ${
                activeTab === 1
                  ? 'text-[var(--accent-ink)] sm:text-[var(--accent-ink)] bg-[var(--accent)] sm:bg-transparent shadow-sm sm:shadow-none'
                  : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              Create an account
            </button>
          </div>
        </div>

        {/* Error notification */}
        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        {/* Auth Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {activeTab === 1 && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Full name
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Alice Employee"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-sm text-slate-800 dark:text-white placeholder-slate-400 focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Work email address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="alice@company.com"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-sm text-slate-800 dark:text-white placeholder-slate-400 focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-sm text-slate-800 dark:text-white placeholder-slate-400 focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none"
              />
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="btn-accent w-full mt-2 py-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 shadow-lg disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none transition-all duration-150"
          >
            {loading ? (
              <span>Verifying credentials...</span>
            ) : (
              <>
                <span>{activeTab === 0 ? 'Continue with email' : 'Create account'}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-4">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-200 dark:border-slate-700" />
          </div>
          <div className="relative flex justify-center text-[11px] uppercase">
            <span className="bg-white/80 dark:bg-slate-800/80 px-2 text-slate-400 font-medium">
              or continue with
            </span>
          </div>
        </div>

        {/* Google Sign-in Container & Button */}
        <div className="w-full flex flex-col items-center justify-center">
          <div id="google-signin-btn-container" className="w-full flex justify-center"></div>

          <div id="google-fallback-btn" className="w-full">
            <button
              type="button"
              onClick={handleCustomGoogleClick}
              disabled={loading}
              className="w-full py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-semibold text-xs flex items-center justify-center gap-2.5 shadow-sm transition-all duration-150 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
              <span>Sign in with Google</span>
            </button>
          </div>
        </div>

        {/* Persona quick select hints for testing */}
        <div className="mt-6 pt-5 border-t border-slate-200/60 dark:border-slate-700/60">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
            Quick Persona Pre-fills
          </span>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => {
                setEmail('alice@company.com');
                setPassword('Password123!');
                setFullName('Alice Employee');
              }}
              className="py-1.5 px-2 rounded-lg text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-[var(--accent-bg-subtle)] hover:text-[var(--accent-text)] hover:border-[var(--accent-border-subtle)] transition-colors border border-slate-200 dark:border-slate-700"
            >
              Alice (Emp)
            </button>
            <button
              type="button"
              onClick={() => {
                setEmail('bob@company.com');
                setPassword('Password123!');
                setFullName('Bob Manager');
              }}
              className="py-1.5 px-2 rounded-lg text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-[var(--accent-bg-subtle)] hover:text-[var(--accent-text)] hover:border-[var(--accent-border-subtle)] transition-colors border border-slate-200 dark:border-slate-700"
            >
              Bob (Mgr)
            </button>
            <button
              type="button"
              onClick={() => {
                setEmail('carol@company.com');
                setPassword('Password123!');
                setFullName('Carol HR');
              }}
              className="py-1.5 px-2 rounded-lg text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-[var(--accent-bg-subtle)] hover:text-[var(--accent-text)] hover:border-[var(--accent-border-subtle)] transition-colors border border-slate-200 dark:border-slate-700"
            >
              Carol (HR)
            </button>
          </div>
        </div>
      </div>

        <p className="text-center text-xs text-slate-400 dark:text-slate-500 mt-6">
          Protected by bcrypt password hashing, 10m OTP email verification, and session rate limiting.
        </p>
      </div>

      {/* Public Footer */}
      <div className="w-full max-w-4xl mx-auto">
        <Footer />
      </div>
    </div>
  );
}
