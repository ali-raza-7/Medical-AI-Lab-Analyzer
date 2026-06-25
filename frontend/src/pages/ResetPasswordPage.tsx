import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';

import { api } from '../api';
import { Lock, CheckCircle, AlertTriangle } from 'lucide-react';

interface Rule {
  label: string;
  test: (v: string) => boolean;
}

const RULES: Rule[] = [
  { label: 'At least 8 characters', test: (v) => v.length >= 8 },
  { label: 'One uppercase letter', test: (v) => /[A-Z]/.test(v) },
  { label: 'One lowercase letter', test: (v) => /[a-z]/.test(v) },
  { label: 'One number', test: (v) => /\d/.test(v) },
  { label: 'One special character', test: (v) => /[!@#$%^&*(),.?":{}|<>_\-]/.test(v) },
];

const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';

  useEffect(() => {
    if (token) {
      window.history.replaceState(null, '', '/reset-password');
    }
  }, []);

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const allMet = RULES.every((r) => r.test(password));
  const passwordsMatch = password === confirm && confirm.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!token) { setError('Invalid or missing reset token.'); return; }
    if (!allMet) { setError('Please meet all password requirements.'); return; }
    if (!passwordsMatch) { setError('Passwords do not match.'); return; }

    setLoading(true);
    try {
      await api.post('/reset-password', { token, new_password: password });
      setDone(true);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } } };
      const detail = axiosErr.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Reset failed. The link may have expired.');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-full max-w-md p-8 space-y-6 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 text-center">
          <div className="mx-auto w-12 h-12 bg-red-100 dark:bg-red-900/30 text-red-600 rounded-full flex items-center justify-center">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-white">Invalid Link</h2>
          <p className="text-sm text-slate-500">This password reset link is invalid or has expired.</p>
          <Link to="/forgot-password" className="inline-block mt-2 text-sm text-emerald-500 hover:underline font-medium">
            Request a new reset link
          </Link>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-full max-w-md p-8 space-y-6 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 text-center">
          <div className="mx-auto w-12 h-12 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 rounded-full flex items-center justify-center">
            <CheckCircle className="h-6 w-6" />
          </div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-white">Password Reset</h2>
          <p className="text-sm text-slate-500">Your password has been updated successfully.</p>
          <Link
            to="/login"
            className="inline-block mt-4 px-6 py-2 bg-emerald-500 text-white rounded-xl font-bold hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/20"
          >
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-full max-w-md p-8 space-y-6 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800">
        <div className="text-center">
          <div className="mx-auto w-12 h-12 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 rounded-full flex items-center justify-center mb-4">
            <Lock className="h-6 w-6" />
          </div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-white">Set New Password</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Must be different from your previous password.</p>
        </div>

        {error && (
          <div className="p-3 text-sm text-red-500 bg-red-100 dark:bg-red-900/30 rounded-lg" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="reset-password" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              New Password
            </label>
            <input
              id="reset-password"
              type="password"
              required
              disabled={loading}
              className="w-full px-4 py-2 mt-1 border border-slate-300 rounded-xl bg-white text-slate-900 placeholder-slate-400 dark:bg-slate-800 dark:border-slate-600 dark:text-white dark:placeholder-slate-500 focus:ring-2 focus:ring-emerald-500 outline-none disabled:opacity-50"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          <div>
            <label htmlFor="reset-confirm" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              Confirm Password
            </label>
            <input
              id="reset-confirm"
              type="password"
              required
              disabled={loading}
              className="w-full px-4 py-2 mt-1 border border-slate-300 rounded-xl bg-white text-slate-900 placeholder-slate-400 dark:bg-slate-800 dark:border-slate-600 dark:text-white dark:placeholder-slate-500 focus:ring-2 focus:ring-emerald-500 outline-none disabled:opacity-50"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="••••••••"
            />
            {confirm.length > 0 && !passwordsMatch && (
              <p className="mt-1 text-xs text-red-500">Passwords do not match</p>
            )}
          </div>

          <ul className="space-y-1.5">
            {RULES.map((rule) => {
              const passed = rule.test(password);
              return (
                <li key={rule.label} className={`flex items-center gap-2 text-xs ${passed ? 'text-emerald-600' : 'text-slate-400'}`}>
                  <span className={`h-3.5 w-3.5 rounded-full border flex items-center justify-center ${passed ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-slate-300 dark:border-slate-600'}`}>
                    {passed && <span className="text-[8px] font-bold">&#10003;</span>}
                  </span>
                  {rule.label}
                </li>
              );
            })}
          </ul>

          <button
            type="submit"
            disabled={loading || !allMet || !passwordsMatch}
            className="w-full py-3 font-semibold text-white bg-emerald-500 rounded-xl hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/30 disabled:opacity-50 flex items-center justify-center"
          >
            {loading ? (
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white" role="status" aria-label="Resetting password" />
            ) : 'Reset Password'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ResetPasswordPage;
