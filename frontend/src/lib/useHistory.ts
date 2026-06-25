import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "../api";
import type { AnalyzeResponse } from "../types";
import { useAuth } from "./AuthContext";

export interface HistoryItem {
  id: string;
  file_name: string;
  created_at: string;
  results_json: AnalyzeResponse;
}

export function useHistory() {
  const { user } = useAuth();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const fetchHistory = useCallback(async () => {
    if (!user) {
      setLoading(false);
      setHistory([]);
      return;
    }

    abortRef.current?.abort();
    abortRef.current = new AbortController();

    try {
      const res = await api.get("/history");
      const data = Array.isArray(res.data) ? (res.data as HistoryItem[]) : [];
      setHistory(data);
      setError("");
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      const axiosErr = err as { response?: { data?: { detail?: unknown } } };
      const msg = axiosErr.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Failed to load history.");
      setHistory([]);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchHistory();
    return () => {
      abortRef.current?.abort();
    };
  }, [fetchHistory]);

  return { history, loading, error, refetch: fetchHistory };
}
