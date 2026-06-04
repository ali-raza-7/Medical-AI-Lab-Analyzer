import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../lib/AuthContext';

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: any) => void;
          renderButton: (element: HTMLElement, config: any) => void;
          prompt: () => void;
        };
      };
    };
  }
}

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

const SignupPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleGoogleCallback = useCallback(async (response: any) => {
    setGoogleLoading(true);
    setError('');
    try {
      const res = await api.post('/auth/google', { credential: response.credential });
      await login(res.data.access_token);
      setSuccess(true);
      setTimeout(() => navigate('/'), 1000);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Google sign-up failed. Please try email signup.');
    } finally {
      setGoogleLoading(false);
    }
  }, [login, navigate]);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;

    const existingScript = document.getElementById('google-gsi-script');
    if (existingScript) {
      initializeGoogle();
      return;
    }

    const script = document.createElement('script');
    script.id = 'google-gsi-script';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => initializeGoogle();
    document.body.appendChild(script);

    function initializeGoogle() {
      if (!window.google) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleCallback,
      });
      const btnContainer = document.getElementById('google-signup-btn');
      if (btnContainer) {
        window.google.accounts.id.renderButton(btnContainer, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          width: '100%',
          text: 'signup_with',
          shape: 'pill',
          logo_alignment: 'left',
        });
      }
    }
  }, [handleGoogleCallback]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    // Frontend validation
    if (!email || !email.trim()) {
      setError('Email is required');
      return;
    }
    if (!email.includes('@') || !email.includes('.')) {
      setError('Please enter a valid email address');
      return;
    }
    if (!password || !password.trim()) {
      setError('Password is required');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }
    
    setLoading(true);
    try {
      await api.post('/signup', { email, password });
      setSuccess(true);
      
      // Auto login after signup
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);
      const res = await api.post('/login', formData);
      await login(res.data.access_token);
      
      setTimeout(() => navigate('/'), 1500);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-full max-w-md p-8 space-y-6 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800">
        <h2 className="text-3xl font-bold text-center text-slate-800 dark:text-white">Create Account</h2>
        {error && <div className="p-3 text-sm text-red-500 bg-red-100 dark:bg-red-900/30 rounded-lg">{error}</div>}
        {success && <div className="p-3 text-sm text-emerald-500 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">Account created! Redirecting to dashboard...</div>}

        {/* Google Sign Up */}
        {GOOGLE_CLIENT_ID && !success && (
          <>
            <div className="flex flex-col items-center gap-3">
              {googleLoading ? (
                <div className="w-full flex items-center justify-center py-3 gap-2 text-sm text-slate-500 bg-slate-50 dark:bg-slate-800 rounded-xl">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-500/20 border-t-emerald-500" />
                  Signing up with Google...
                </div>
              ) : (
                <div id="google-signup-btn" className="w-full flex justify-center" />
              )}
            </div>
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200 dark:border-slate-700" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white dark:bg-slate-900 px-3 text-slate-400 font-medium">or continue with email</span>
              </div>
            </div>
          </>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Email</label>
            <input
              type="email"
              required
              disabled={loading || success}
              className="w-full px-4 py-2 mt-1 border border-slate-300 rounded-xl bg-white text-slate-900 placeholder-slate-400 dark:bg-slate-800 dark:border-slate-600 dark:text-white dark:placeholder-slate-500 focus:ring-2 focus:ring-emerald-500 outline-none disabled:opacity-50"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Password</label>
            <input
              type="password"
              required
              disabled={loading || success}
              className="w-full px-4 py-2 mt-1 border border-slate-300 rounded-xl bg-white text-slate-900 placeholder-slate-400 dark:bg-slate-800 dark:border-slate-600 dark:text-white dark:placeholder-slate-500 focus:ring-2 focus:ring-emerald-500 outline-none disabled:opacity-50"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={loading || success}
            className="w-full py-3 font-semibold text-white bg-emerald-500 rounded-xl hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/30 disabled:opacity-50 flex items-center justify-center"
          >
            {loading ? <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white" /> : "Sign Up"}
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
