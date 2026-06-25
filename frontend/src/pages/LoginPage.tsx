import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../lib/AuthContext';
import { api } from '../api';
import { GoogleLoginButton } from '../components/ui/GoogleLoginButton';
import type { GoogleProfile } from '../lib/useGoogleAuth';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const { login, setUserPicture } = useAuth();
  const navigate = useNavigate();

  const onGoogleSuccess = async (token: string, profile: GoogleProfile) => {
    if (profile.picture) setUserPicture(profile.picture);
    await login(token);
    navigate('/');
  };

  const validateEmail = (value: string): string => {
    if (!value.trim()) return 'Email is required';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return 'Please enter a valid email address';
    return '';
  };

  const validatePassword = (value: string): string => {
    if (!value.trim()) return 'Password is required';
    return '';
  };

  const getErrorMessage = (raw: string): string => {
    if (raw.includes('Invalid email or password')) return 'Invalid email or password';
    if (raw.includes('verify your email')) return 'Please verify your email before logging in';
    if (raw.includes('locked')) return 'Account temporarily locked due to too many failed attempts. Try again later.';
    if (raw.includes('rate limit')) return 'Too many login attempts. Please wait a moment.';
    return raw;
  };

  const handleEmailBlur = () => setEmailError(validateEmail(email));
  const handlePasswordBlur = () => setPasswordError(validatePassword(password));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const errE = validateEmail(email);
    const errP = validatePassword(password);
    setEmailError(errE);
    setPasswordError(errP);
    if (errE || errP) return;

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);
      const res = await api.post('/login', formData);
      if (!res.data.access_token) {
        throw new Error('No token received from server');
      }
      await login(res.data.access_token);
      navigate('/');
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } } };
      const detail = axiosErr.response?.data?.detail;
      setError(getErrorMessage(typeof detail === 'string' ? detail : 'Login failed. Please check your credentials.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-full max-w-md p-8 space-y-6 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800">
        <h2 className="text-3xl font-bold text-center text-slate-800 dark:text-white">Welcome Back</h2>

        {error && (
          <div className="p-3 text-sm text-red-500 bg-red-100 dark:bg-red-900/30 rounded-lg" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="login-email" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              required
              disabled={loading}
              className="w-full px-4 py-2 mt-1 border border-slate-300 rounded-xl bg-white text-slate-900 placeholder-slate-400 dark:bg-slate-800 dark:border-slate-600 dark:text-white dark:placeholder-slate-500 focus:ring-2 focus:ring-emerald-500 outline-none disabled:opacity-50"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setEmailError(''); }}
              onBlur={handleEmailBlur}
              placeholder="your@email.com"
              aria-invalid={!!emailError}
              aria-describedby={emailError ? 'login-email-error' : undefined}
            />
            {emailError && <p id="login-email-error" className="mt-1 text-xs text-red-500" role="alert">{emailError}</p>}
          </div>
          <div>
            <label htmlFor="login-password" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              Password
            </label>
            <input
              id="login-password"
              type="password"
              required
              disabled={loading}
              className="w-full px-4 py-2 mt-1 border border-slate-300 rounded-xl bg-white text-slate-900 placeholder-slate-400 dark:bg-slate-800 dark:border-slate-600 dark:text-white dark:placeholder-slate-500 focus:ring-2 focus:ring-emerald-500 outline-none disabled:opacity-50"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setPasswordError(''); }}
              onBlur={handlePasswordBlur}
              placeholder="••••••••"
              aria-invalid={!!passwordError}
              aria-describedby={passwordError ? 'login-password-error' : undefined}
            />
            {passwordError && <p id="login-password-error" className="mt-1 text-xs text-red-500" role="alert">{passwordError}</p>}
          </div>
          <div className="flex justify-end">
            <Link to="/forgot-password" className="text-xs text-emerald-500 hover:text-emerald-600 font-medium">
              Forgot Password?
            </Link>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 font-semibold text-white bg-emerald-500 rounded-xl hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/30 disabled:opacity-50 flex items-center justify-center"
            aria-label="Sign in to your account"
          >
            {loading ? (
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white" role="status" aria-label="Signing in" />
            ) : 'Sign In'}
          </button>
        </form>

        {GOOGLE_CLIENT_ID && (
          <>
            <div className="relative" role="separator" aria-orientation="horizontal">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200 dark:border-slate-700" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white dark:bg-slate-900 px-3 text-slate-400 font-medium">or sign in with Google</span>
              </div>
            </div>
            <GoogleLoginButton
              clientId={GOOGLE_CLIENT_ID}
              onSuccess={onGoogleSuccess}
              onError={setError}
              mode="signin"
            />
          </>
        )}

        <p className="text-sm text-center text-slate-600 dark:text-slate-400">
          Don't have an account? <Link to="/signup" className="text-emerald-500 hover:underline">Sign up</Link>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
