import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileSearch, ArrowRight, ShieldCheck, Mail, Lock, User, Sparkles } from 'lucide-react';
import { login } from '../api';
import ErrorBanner from '../components/common/ErrorBanner';

export default function LoginPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0); // 0 = Sign in, 1 = Create an account
  const [email, setEmail] = useState('alice@company.com');
  const [password, setPassword] = useState('devpassword123');
  const [fullName, setFullName] = useState('Alice Employee');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await login({
        email,
        password,
        isSignUp: activeTab === 1,
      });

      // Navigate to OTP verification page
      navigate(`/verify?email=${encodeURIComponent(email)}`);
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
    <div className="min-h-screen app-gradient-bg flex flex-col items-center justify-center p-4">
      {/* Brand Header */}
      <div className="mb-6 text-center">
        <div className="w-14 h-14 rounded-2xl bg-[#F26A21] flex items-center justify-center text-white mx-auto shadow-lg shadow-orange-500/30 mb-3">
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
        {/* Sliding Orange Blade Navigation */}
        <div className="relative mb-6">
          {/* Background track for tabs */}
          <div
            className="flex relative p-1 bg-slate-200/60 dark:bg-slate-800/60 rounded-2xl"
            role="tablist"
            aria-label="Authentication mode"
          >
            {/* Sliding orange blade (Desktop / Tablets) */}
            <div
              className="absolute top-1 bottom-1 rounded-xl bg-[#F26A21] shadow-md shadow-orange-500/30 transition-transform duration-300 ease-out hidden sm:block"
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
              className={`flex-1 py-2.5 text-xs font-bold rounded-xl relative z-10 transition-colors text-center focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none ${
                activeTab === 0
                  ? 'text-white sm:text-white bg-[#F26A21] sm:bg-transparent shadow-sm sm:shadow-none'
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
              className={`flex-1 py-2.5 text-xs font-bold rounded-xl relative z-10 transition-colors text-center focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none ${
                activeTab === 1
                  ? 'text-white sm:text-white bg-[#F26A21] sm:bg-transparent shadow-sm sm:shadow-none'
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
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-sm text-slate-800 dark:text-white placeholder-slate-400 focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
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
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-sm text-slate-800 dark:text-white placeholder-slate-400 focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
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
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 text-sm text-slate-800 dark:text-white placeholder-slate-400 focus-visible:ring-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
              />
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-3 rounded-xl bg-[#F26A21] hover:bg-[#dc5612] text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-orange-500/25 transition-all duration-150 disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#F26A21] focus-visible:outline-none"
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
                setFullName('Alice Employee');
              }}
              className="py-1.5 px-2 rounded-lg text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-orange-50 dark:hover:bg-slate-700 transition-colors border border-slate-200 dark:border-slate-700"
            >
              Alice (Emp)
            </button>
            <button
              type="button"
              onClick={() => {
                setEmail('bob@company.com');
                setFullName('Bob Manager');
              }}
              className="py-1.5 px-2 rounded-lg text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-orange-50 dark:hover:bg-slate-700 transition-colors border border-slate-200 dark:border-slate-700"
            >
              Bob (Mgr)
            </button>
            <button
              type="button"
              onClick={() => {
                setEmail('carol@company.com');
                setFullName('Carol HR');
              }}
              className="py-1.5 px-2 rounded-lg text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-orange-50 dark:hover:bg-slate-700 transition-colors border border-slate-200 dark:border-slate-700"
            >
              Carol (HR)
            </button>
          </div>
        </div>
      </div>

      <p className="text-center text-xs text-slate-400 dark:text-slate-500 mt-6">
        Protected by Argon2id password hashing and session rate limiting.
      </p>
    </div>
  );
}
