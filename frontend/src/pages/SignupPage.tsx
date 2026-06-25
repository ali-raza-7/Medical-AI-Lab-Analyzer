import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../lib/AuthContext';
import { GoogleLoginButton } from '../components/ui/GoogleLoginButton';
import type { GoogleProfile } from '../lib/useGoogleAuth';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

const RULES = [
  { label: 'At least 8 characters', test: (v: string) => v.length >= 8 },
  { label: 'One uppercase letter', test: (v: string) => /[A-Z]/.test(v) },
  { label: 'One lowercase letter', test: (v: string) => /[a-z]/.test(v) },
  { label: 'One number', test: (v: string) => /\d/.test(v) },
  { label: 'One special character', test: (v: string) => /[!@#$%^&*(),.?":{}|<>_\-]/.test(v) },
];

const SignupPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [emailError, setEmailError] = useState('');
  const { login, setUserPicture } = useAuth();
  const navigate = useNavigate();

  const onGoogleSuccess = async (token: string, profile: GoogleProfile) => {
    if (profile.picture) setUserPicture(profile.picture);
    await login(token);
    setSuccess(true);
    setTimeout(() => navigate('/'), 1000);
  };

  const validateEmail = (value: string): string => {
    if (!value.trim()) return 'Email is required';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return 'Please enter a valid email address';
    return '';
  };

  const allRulesMet = RULES.every((r) => r.test(password));
  const passwordValid = password.length === 0 || allRulesMet;

  const handleEmailBlur = () => setEmailError(validateEmail(email));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const errE = validateEmail(email);
    setEmailError(errE);
    if (errE) return;
    if (!allRulesMet) { setError('Please meet all password requirements.'); return; }

    setLoading(true);
    try {
      await api.post('/signup', { email, password });
      setSuccess(true);

      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);
      const res = await api.post('/login', formData);
      await login(res.data.access_token);

      setTimeout(() => navigate('/'), 1500);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } } };
      setError(typeof axiosErr.response?.data?.detail === 'string' ? axiosErr.response.data.detail : 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-full max-w-md p-8 space-y-6 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800">
        <h2 className="text-3xl font-bold text-center text-slate-800 dark:text-white">Create Account</h2>

        {error && (
          <div className="p-3 text-sm text-red-500 bg-red-100 dark:bg-red-900/30 rounded-lg" role="alert">
            {error}
          </div>
        )}
        {success && (
          <div className="p-3 text-sm text-emerald-500 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg" role="status">
            Account created! Redirecting to dashboard...
          </div>
        )}

        {GOOGLE_CLIENT_ID && !success && (
          <>
            <GoogleLoginButton
              clientId={GOOGLE_CLIENT_ID}
              onSuccess={onGoogleSuccess}
              onError={setError}
              mode="signup"
            />
            <div className="relative" role="separator" aria-orientation="horizontal">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200 dark:border-slate-700" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white dark:bg-slate-900 px-3 text-slate-400 font-medium">or continue with email</span>
              </div>
            </div>
          </>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="signup-email" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              Email
            </label>
            <input
              id="signup-email"
              type="email"
              required
              disabled={loading || success}
              className="w-full px-4 py-2 mt-1 border border-slate-300 rounded-xl bg-white text-slate-900 placeholder-slate-400 dark:bg-slate-800 dark:border-slate-600 dark:text-white dark:placeholder-slate-500 focus:ring-2 focus:ring-emerald-500 outline-none disabled:opacity-50"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setEmailError(''); }}
              onBlur={handleEmailBlur}
              placeholder="your@email.com"
              aria-invalid={!!emailError}
              aria-describedby={emailError ? 'signup-email-error' : undefined}
            />
            {emailError && <p id="signup-email-error" className="mt-1 text-xs text-red-500" role="alert">{emailError}</p>}
          </div>
          <div>
            <label htmlFor="signup-password" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              Password
            </label>
            <input
              id="signup-password"
              type="password"
              required
              disabled={loading || success}
              className="w-full px-4 py-2 mt-1 border border-slate-300 rounded-xl bg-white text-slate-900 placeholder-slate-400 dark:bg-slate-800 dark:border-slate-600 dark:text-white dark:placeholder-slate-500 focus:ring-2 focus:ring-emerald-500 outline-none disabled:opacity-50"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onBlur={() => {
                if (password.length > 0 && !allRulesMet) {
                  // just triggers validation display
                }
              }}
              placeholder="••••••••"
              aria-invalid={!passwordValid}
            />
            <ul className="mt-2 space-y-1.5">
              {RULES.map((rule) => {
                const passed = rule.test(password);
                const touched = password.length > 0;
                return (
                  <li key={rule.label} className={`flex items-center gap-2 text-xs ${touched ? (passed ? 'text-emerald-600' : 'text-red-400') : 'text-slate-400'}`}>
                    <span className={`h-3.5 w-3.5 rounded-full border flex items-center justify-center flex-shrink-0 ${
                      touched
                        ? passed
                          ? 'bg-emerald-500 border-emerald-500 text-white'
                          : 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700'
                        : 'border-slate-300 dark:border-slate-600'
                    }`}>
                      {touched && passed && <span className="text-[8px] font-bold">&#10003;</span>}
                      {touched && !passed && <span className="text-[8px]">&#8226;</span>}
                    </span>
                    {rule.label}
                  </li>
                );
              })}
            </ul>
          </div>
          <button
            type="submit"
            disabled={loading || success}
            className="w-full py-3 font-semibold text-white bg-emerald-500 rounded-xl hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/30 disabled:opacity-50 flex items-center justify-center"
          >
            {loading ? (
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white" role="status" aria-label="Creating account" />
            ) : "Sign Up"}
          </button>
        </form>
        <p className="text-sm text-center text-slate-600 dark:text-slate-400">
          Already have an account? <Link to="/login" className="text-emerald-500 hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
};

export default SignupPage;
