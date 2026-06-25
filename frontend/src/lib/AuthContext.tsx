import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || window.location.origin;
const plainApi = axios.create({ baseURL: API_BASE_URL, withCredentials: true, timeout: 10000, headers: { "X-Requested-With": "XMLHttpRequest" } });

interface User {
  id: string;
  email: string;
  credits: number;
  picture?: string;
}

const PICTURE_STORAGE_KEY = "user_picture";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  setUserPicture: (url: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [checked, setChecked] = useState(false);

  const fetchUser = async () => {
    try {
      const res = await plainApi.get('/me');
      const storedPicture = localStorage.getItem(PICTURE_STORAGE_KEY);
      setUser({ ...res.data, picture: storedPicture || undefined });
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
      setChecked(true);
    }
  };

  useEffect(() => {
    if (!checked) fetchUser();
  }, [checked]);

  const login = async (token: string) => {
    setLoading(true);
    try {
      await fetchUser();
    } finally {
      setLoading(false);
    }
  };

  const setUserPicture = (url: string) => {
    localStorage.setItem(PICTURE_STORAGE_KEY, url);
    setUser((prev) => (prev ? { ...prev, picture: url } : prev));
  };

  const logout = async () => {
    try {
      await plainApi.post('/logout');
    } catch {
      // proceed anyway
    }
    localStorage.removeItem(PICTURE_STORAGE_KEY);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser: fetchUser, setUserPicture }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
