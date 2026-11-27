import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileSearch,
  ArrowRight,
  ShieldCheck,
  Mail,
  Lock,
  User,
  Sparkles,
  Eye,
  EyeOff,
  CheckCircle2,
  Shield,
  Layers,
  Zap,
} from 'lucide-react';
import { login, googleSignIn, getRoleHome } from '../api';
import ErrorBanner from '../components/common/ErrorBanner';
import Footer from '../components/layout/Footer';

export default function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState('signin'); // 'signin' | 'signup'
  const [email, setEmail] = useState('alice@company.com');
  const [password, setPassword] = useState('Password123!');
  const [showPassword, setShowPassword] = useState(false);
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
        navigate('/verify', {
          state: {
            email: res.email,
            devCode: res.devCode,
            requiresOtp: true,
          },
        });
      } else {
        const role = res.role || res.persona?.role || 'employee';
        navigate(getRoleHome(role));
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
        fullName: mode === 'signup' ? fullName : '',
        isSignUp: mode === 'signup',
      });

      // Pass devCode if returned for immediate testing visibility
      const devParam = res.dev_code ? `&devCode=${res.dev_code}` : '';
      navigate(`/verify?email=${encodeURIComponent(email)}${devParam}`);
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check credentials.');
    } finally {
      setLoading(false);
      setShowPassword(false);
    }
  }

  return (
    <div className="min-h-screen app-gradient-bg flex flex-col justify-between items-center p-3 sm:p-6 md:p-8">
      {/* Top DEV Mode Pill */}
      <header className="w-full max-w-5xl flex items-center justify-between py-2 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-[var(--accent)] text-[var(--accent-ink)] flex items-center justify-center font-bold shadow-md shadow-[var(--accent-glow)]">
            <FileSearch className="w-4 h-4" />
          </div>
          <span className="font-bold text-slate-800 dark:text-white text-sm tracking-tight">
            HR Self-Audit Assistant
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[var(--accent-bg-subtle)] text-[var(--accent-text)] border border-[var(--accent-border-subtle)]">
            <ShieldCheck className="w-3 h-3" />
            DEV mode active
          </span>
        </div>
      </header>

      {/* Main Container: Blade Diagonal Transition on Desktop (>=900px), Stacked on Mobile (<900px) */}
      <main className="w-full max-w-5xl my-auto py-4 flex justify-center">
        <div
          data-mode={mode}
          className="blade-card w-full rounded-3xl shadow-2xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-[#14171C] overflow-hidden relative min-h-[580px] flex flex-col md:flex-row"
        >
          {/* =========================================================================
              MOBILE STRIP (< 900px): Clean brand banner with compact mode switcher
             ========================================================================= */}
          <div className="md:hidden bg-gradient-to-r from-[#14171C] via-[#1B1F26] to-[#14171C] p-6 text-white text-center border-b border-slate-800">
            <div className="w-12 h-12 rounded-2xl bg-[var(--accent)] text-[var(--accent-ink)] flex items-center justify-center mx-auto mb-3 shadow-md shadow-[var(--accent-glow)]">
              <FileSearch className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-extrabold tracking-tight">
              {mode === 'signin' ? 'Welcome Back' : 'Create an Account'}
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto">
              Automated deterministic month-end compliance & audit ledger.
            </p>
            {/* Mobile Mode Switcher Tabs */}
            <div className="flex p-1 bg-slate-900/90 rounded-2xl mt-4 max-w-xs mx-auto border border-slate-700/60">
              <button
                type="button"
                onClick={() => setMode('signin')}
                className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all ${
                  mode === 'signin'
                    ? 'bg-[var(--accent)] text-[var(--accent-ink)] shadow-md'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => setMode('signup')}
                className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all ${
                  mode === 'signup'
                    ? 'bg-[var(--accent)] text-[var(--accent-ink)] shadow-md'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Sign Up
              </button>
            </div>
          </div>

          {/* =========================================================================
              DESKTOP BLADE PANE 1: SKEWED BRAND PANE (Swaps smoothly via transform)
             ========================================================================= */}
          <div
            className={`blade-pane-brand hidden md:flex absolute top-0 bottom-0 w-[46%] z-20 overflow-hidden items-center justify-center ${
              mode === 'signin'
                ? 'right-0 border-l border-[var(--accent)]/40 shadow-[-10px_0_30px_rgba(0,0,0,0.4)]'
                : 'left-0 border-r border-[var(--accent)]/40 shadow-[10px_0_30px_rgba(0,0,0,0.4)]'
            }`}
            style={{
              background: 'linear-gradient(145deg, #12151B 0%, #1A202C 55%, #10141A 100%)',
            }}
          >
            {/* Ice Blue Glow Orb in background */}
            <div
              className="absolute w-72 h-72 rounded-full blur-3xl pointer-events-none opacity-20"
              style={{
                background: 'radial-gradient(circle, #5B9BF3 0%, transparent 70%)',
                top: mode === 'signin' ? '20%' : '50%',
                right: mode === 'signin' ? '10%' : '40%',
              }}
              aria-hidden="true"
            />

            {/* Skewed seam accent glow line */}
            <div
              className={`absolute top-0 bottom-0 w-1 bg-[var(--accent)] opacity-70 shadow-[0_0_15px_var(--accent)] ${
                mode === 'signin' ? 'left-0' : 'right-0'
              }`}
              aria-hidden="true"
            />

            {/* Brand pane content (upright, counter-skewed for readability) */}
            <div className="relative z-10 px-8 py-10 text-white flex flex-col justify-between h-full max-w-sm">
              <div>
                <div className="w-12 h-12 rounded-2xl bg-[var(--accent)] text-[var(--accent-ink)] flex items-center justify-center shadow-lg shadow-[var(--accent-glow)] mb-4">
                  <FileSearch className="w-6 h-6" />
                </div>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[var(--accent-text)]">
                  Enterprise Audit Platform
                </span>
                <h2 className="text-2xl font-extrabold tracking-tight mt-1 text-white leading-tight">
                  {mode === 'signin'
                    ? 'Audit readiness at your fingertips.'
                    : 'Join the deterministic compliance network.'}
                </h2>
                <p className="text-xs text-slate-300 mt-2.5 leading-relaxed">
                  Real-time statutory verification across timesheets, missing punches, leave conflicts, and expense claims.
                </p>

                <div className="mt-6 space-y-2.5 text-xs text-slate-300">
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>8 deterministic statutory rules</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>SHA-256 tamper-evident ledger</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Strict role scoping & 403 enforcement</span>
                  </div>
                </div>
              </div>

              {/* Mode switch button inside Brand Pane */}
              <div className="pt-6 border-t border-slate-700/60">
                <p className="text-xs text-slate-400 mb-2">
                  {mode === 'signin' ? "Don't have an account yet?" : 'Already have an enterprise account?'}
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setError(null);
                    setMode(mode === 'signin' ? 'signup' : 'signin');
                  }}
                  className="w-full py-2.5 px-4 rounded-xl border border-[var(--accent-border-subtle)] bg-[var(--accent-bg-subtle)] text-[var(--accent-text)] hover:bg-[var(--accent)] hover:text-[var(--accent-ink)] text-xs font-bold transition-all duration-200 flex items-center justify-center gap-2 shadow-sm"
                >
                  <span>{mode === 'signin' ? 'Create an Account' : 'Sign in to Account'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* =========================================================================
              DESKTOP & MOBILE FORM PANE: Forms for Sign In & Create Account
             ========================================================================= */}
          <div
            className={`blade-pane-form flex-1 p-6 sm:p-10 flex flex-col justify-center transition-all ${
              mode === 'signin' ? 'md:mr-[46%]' : 'md:ml-[46%]'
            }`}
          >
            <div className="max-w-md w-full mx-auto space-y-5">
              {/* Desktop Header switcher pill */}
              <div className="hidden md:flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
                    {mode === 'signin' ? 'Sign in to your account' : 'Create an enterprise account'}
                  </h1>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Enter your work email and password to proceed.
                  </p>
                </div>
                {/* Desktop Tab Switcher */}
                <div className="flex p-0.5 bg-slate-100 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700">
                  <button
                    type="button"
                    onClick={() => {
                      setError(null);
                      setMode('signin');
                    }}
                    className={`px-3 py-1 text-xs font-bold rounded-lg transition-all ${
                      mode === 'signin'
                        ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                        : 'text-slate-500 hover:text-slate-900 dark:text-slate-400'
                    }`}
                  >
                    Sign In
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setError(null);
                      setMode('signup');
                    }}
                    className={`px-3 py-1 text-xs font-bold rounded-lg transition-all ${
                      mode === 'signup'
                        ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                        : 'text-slate-500 hover:text-slate-900 dark:text-slate-400'
                    }`}
                  >
                    Sign Up
                  </button>
                </div>
              </div>

              {/* Error Banner */}
              <ErrorBanner message={error} onDismiss={() => setError(null)} />

              {/* Form Component */}
              <form onSubmit={handleSubmit} className="space-y-4">
                {mode === 'signup' && (
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
                  <label
                    htmlFor="login-password-input"
                    className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5"
                  >
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                    <input
                      id="login-password-input"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full pl-10 pr-11 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-sm text-slate-800 dark:text-white placeholder-slate-400 focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none"
                    />
                    <button
                      type="button"
                      tabIndex={0}
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      aria-pressed={showPassword}
                      className="absolute right-3 top-2.5 p-1 rounded-lg text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none transition-colors"
                    >
                      {showPassword ? (
                        <EyeOff className="w-4 h-4 text-slate-600 dark:text-slate-300" aria-hidden="true" />
                      ) : (
                        <Eye className="w-4 h-4 text-slate-600 dark:text-slate-300" aria-hidden="true" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Submit Action */}
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-accent w-full mt-2 py-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 shadow-lg disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[var(--accent)] focus-visible:outline-none transition-all duration-150"
                >
                  {loading ? (
                    <span>Verifying credentials...</span>
                  ) : (
                    <>
                      <span>{mode === 'signin' ? 'Sign in with Password' : 'Create Account'}</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>

              {/* Divider */}
              <div className="relative my-3">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-200 dark:border-slate-700/80" />
                </div>
                <div className="relative flex justify-center text-[10px] uppercase">
                  <span className="bg-white dark:bg-[#14171C] px-2 text-slate-400 font-semibold tracking-wider">
                    or continue with
                  </span>
                </div>
              </div>

              {/* Google Sign-in */}
              <div className="w-full">
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
                  <span>Continue with Google</span>
                </button>
              </div>

              {/* Quick Persona Pre-fills */}
              <div className="pt-3 border-t border-slate-200/60 dark:border-slate-800/60">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                  Quick Persona Pre-fills (Testing)
                </span>
                <div className="grid grid-cols-4 gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      setEmail('alice@company.com');
                      setPassword('Password123!');
                      setFullName('Alice Employee');
                      setMode('signin');
                    }}
                    className="py-1.5 px-1.5 rounded-lg text-[10px] sm:text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-[var(--accent-bg-subtle)] hover:text-[var(--accent-text)] transition-colors border border-slate-200 dark:border-slate-700 text-center"
                  >
                    Alice (Emp)
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setEmail('bob@company.com');
                      setPassword('Password123!');
                      setFullName('Bob Manager');
                      setMode('signin');
                    }}
                    className="py-1.5 px-1.5 rounded-lg text-[10px] sm:text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-[var(--accent-bg-subtle)] hover:text-[var(--accent-text)] transition-colors border border-slate-200 dark:border-slate-700 text-center"
                  >
                    Bob (Mgr)
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setEmail('carol@company.com');
                      setPassword('Password123!');
                      setFullName('Carol HR');
                      setMode('signin');
                    }}
                    className="py-1.5 px-1.5 rounded-lg text-[10px] sm:text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-[var(--accent-bg-subtle)] hover:text-[var(--accent-text)] transition-colors border border-slate-200 dark:border-slate-700 text-center"
                  >
                    Carol (HR)
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setEmail('irene@company.com');
                      setPassword('Password123!');
                      setFullName('Irene IC');
                      setMode('signin');
                    }}
                    className="py-1.5 px-1.5 rounded-lg text-[10px] sm:text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-[var(--accent-bg-subtle)] hover:text-[var(--accent-text)] transition-colors border border-slate-200 dark:border-slate-700 text-center"
                  >
                    Irene (IC)
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Public Footer */}
      <footer className="w-full max-w-5xl py-2">
        <Footer />
      </footer>
    </div>
  );
}
