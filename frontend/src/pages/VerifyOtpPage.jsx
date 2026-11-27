import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ShieldCheck, CheckCircle2, RotateCw, ArrowLeft, ShieldAlert } from 'lucide-react';
import { verifyOtp, resendOtp, getCurrentPersona, getRoleHome } from '../api';
import ErrorBanner from '../components/common/ErrorBanner';
import Footer from '../components/layout/Footer';

export default function VerifyOtpPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const email = searchParams.get('email') || 'alice@company.com';
  const initialDevCode = searchParams.get('devCode') || '123456';

  const [devCodeDisplay, setDevCodeDisplay] = useState(initialDevCode);
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState(null);
  const [shake, setShake] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [resendSeconds, setResendSeconds] = useState(60);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const inputRefs = useRef([]);

  // Countdown timer for resending OTP
  useEffect(() => {
    if (resendSeconds <= 0) return;
    const interval = setInterval(() => {
      setResendSeconds((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [resendSeconds]);

  // Focus first input on mount
  useEffect(() => {
    if (inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, []);

  function handleInputChange(index, value) {
    // Only accept numeric input
    const cleanVal = value.replace(/[^0-9]/g, '');
    if (!cleanVal && value !== '') return;

    const newOtp = [...otp];
    newOtp[index] = cleanVal ? cleanVal[cleanVal.length - 1] : '';
    setOtp(newOtp);
    setError(null);

    // Auto-advance
    if (cleanVal && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit when all 6 digits are entered
    const currentCode = newOtp.join('');
    if (currentCode.length === 6) {
      handleVerify(currentCode);
    }
  }

  function handleKeyDown(index, e) {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  }

  function handlePaste(e) {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/[^0-9]/g, '').slice(0, 6);
    if (!pastedData) return;

    const newOtp = [...otp];
    for (let i = 0; i < 6; i++) {
      newOtp[i] = pastedData[i] || '';
    }
    setOtp(newOtp);
    setError(null);

    // Focus on next available empty box or the last box
    const nextIndex = Math.min(pastedData.length, 5);
    inputRefs.current[nextIndex]?.focus();

    if (pastedData.length === 6) {
      handleVerify(pastedData);
    }
  }

  async function handleVerify(codeToTest) {
    const code = codeToTest || otp.join('');
    if (code.length < 6) {
      setError('Please enter all 6 digits of the verification code.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const res = await verifyOtp({ email, code });

      // Trigger successful continuous green bar animation
      setIsSuccess(true);

      // Redirect after animation completes
      setTimeout(() => {
        const persona = getCurrentPersona();
        navigate(getRoleHome(persona?.role));
      }, 750);
    } catch (err) {
      // Trigger box shake animation on wrong code
      setShake(true);
      setError(err.message || 'Invalid verification code. Please check and try again.');
      setTimeout(() => setShake(false), 500);
      setOtp(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleResend() {
    if (resendSeconds > 0) return;
    setError(null);
    try {
      const res = await resendOtp({ email });
      setResendSeconds(60);
      setOtp(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
      if (res && res.dev_code) {
        setDevCodeDisplay(res.dev_code);
      }
    } catch (err) {
      setError(err.message || 'Failed to resend code.');
    }
  }

  return (
    <div className="min-h-screen app-gradient-bg flex flex-col justify-between items-center p-4 sm:p-6">
      <div className="w-full max-w-md my-auto flex flex-col items-center">
        {/* Brand Header */}
      <div className="mb-6 text-center">
        <div className="w-14 h-14 rounded-2xl bg-[var(--accent)] text-[var(--accent-ink)] flex items-center justify-center mx-auto shadow-lg shadow-[var(--accent)]/20 mb-3">
          <ShieldCheck className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-extrabold text-slate-800 dark:text-white tracking-tight">
          Verify Your Identity
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
          We sent a 6-digit confirmation code to{' '}
          <strong className="text-slate-700 dark:text-slate-200">{email}</strong>
        </p>
      </div>

      {/* Main Glassmorphic Verification Card */}
      <div className="glass-panel w-full max-w-md rounded-3xl p-6 sm:p-8 shadow-2xl relative">
        {/* DEV Mode Prominent Banner */}
        <div className="mb-6 px-4 py-2.5 rounded-xl bg-[var(--accent-bg-subtle)] border border-[var(--border)] flex items-center justify-between text-xs text-[var(--accent-text)] font-semibold">
          <span className="flex items-center gap-1.5">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            DEV mode active
          </span>
          <span className="bg-[var(--accent)] text-[var(--accent-ink)] px-2 py-0.5 rounded-md font-mono text-[11px] font-bold">
            Code: {devCodeDisplay}
          </span>
        </div>

        {/* Error Banner */}
        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        {/* OTP Input Container / Green Merged Success Bar */}
        <div className="my-6">
          {isSuccess ? (
            /* Successful continuous green bar */
            <div className="animate-merge-bar w-full py-4 px-6 rounded-2xl bg-emerald-500 text-white flex items-center justify-center gap-3 shadow-lg shadow-emerald-500/30">
              <CheckCircle2 className="w-6 h-6 animate-bounce" />
              <span className="text-sm font-bold tracking-wide">
                Verification Successful &bull; Redirecting...
              </span>
            </div>
          ) : (
            /* Six individual square boxes with gold focus ring and shake */
            <div
              className={`flex items-center justify-between gap-2 sm:gap-3 ${
                shake ? 'animate-shake' : ''
              }`}
            >
              {otp.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => (inputRefs.current[idx] = el)}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  value={digit}
                  disabled={isSubmitting}
                  onChange={(e) => handleInputChange(idx, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(idx, e)}
                  onPaste={handlePaste}
                  aria-label={`Digit ${idx + 1}`}
                  className="w-12 h-14 sm:w-14 sm:h-16 text-center text-xl sm:text-2xl font-bold font-mono rounded-2xl border border-slate-300 dark:border-slate-700 bg-white/90 dark:bg-slate-800/90 text-slate-800 dark:text-white transition-all duration-150 focus:border-[var(--accent)] focus:ring-4 focus:ring-[var(--accent)]/25 focus:shadow-[0_0_15px_rgba(212,168,75,0.35)] focus:outline-none"
                />
              ))}
            </div>
          )}
        </div>

        {/* Resend Timer & Actions */}
        <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mt-6 pt-4 border-t border-slate-200/60 dark:border-slate-700/60">
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white font-medium focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded-lg p-1"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to login
          </button>

          <button
            type="button"
            disabled={resendSeconds > 0}
            onClick={handleResend}
            className={`flex items-center gap-1 font-semibold ${
              resendSeconds > 0
                ? 'text-slate-400 dark:text-slate-600 cursor-not-allowed'
                : 'text-[var(--accent-text)] hover:opacity-80 cursor-pointer'
            } focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded-lg p-1`}
          >
            <RotateCw className="w-3.5 h-3.5" />
            {resendSeconds > 0 ? `Resend code (${resendSeconds}s)` : 'Resend code'}
          </button>
        </div>
      </div>
      </div>

      {/* Public Footer */}
      <div className="w-full max-w-4xl mx-auto">
        <Footer />
      </div>
    </div>
  );
}
