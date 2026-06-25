import { useState, useRef, useEffect, useCallback } from "react";
import { api, analyzeReport, waitForResult } from "../api";
import type { AnalyzeResponse } from "../types";
import { useAuth } from "./AuthContext";

export function useAnalyzeReport() {
  const { refreshUser } = useAuth();
  const abortRef = useRef<AbortController | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [gender, setGender] = useState("male");
  const [age, setAge] = useState(30);
  const [manualAgeOverride, setManualAgeOverride] = useState(false);
  const [manualGenderOverride, setManualGenderOverride] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!file && (!text || text.trim() === "")) {
      setError("Input required: Please upload a file or provide report text.");
      return;
    }

    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setError("");
    setLoading(true);
    setResult(null);
    try {
      const health = await api.get<{ status: string }>("/worker/health");
      if (health.data.status === "offline") {
        throw new Error("Analysis service is offline. Please contact support.");
      }

      const { task_id } = await analyzeReport({ file, text, gender, age });
      const data = await waitForResult(task_id, abortRef.current?.signal);

      if (!data || !Array.isArray(data.results)) {
        throw new Error("Invalid response format from server");
      }
      const info = data.patient_info ?? data.patient_detected ?? null;
      if (info) {
        if (info.gender && !manualGenderOverride) {
          setGender(info.gender);
        }
        if (typeof info.age === "number" && !manualAgeOverride) {
          setAge(info.age);
        }
      }
      setResult(data);
      await refreshUser();
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      let message = "Failed to analyze report";
      if (err instanceof Error) {
        message = err.message;
      }
      const axiosError = err as { response?: { data?: { detail?: unknown } } };
      if (axiosError.response?.data?.detail) {
        const detail = axiosError.response.data.detail;
        message = typeof detail === "string" ? detail : JSON.stringify(detail);
      }
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [file, text, gender, age, manualAgeOverride, manualGenderOverride, refreshUser]);

  return {
    file, setFile,
    text, setText,
    gender, setGender,
    age, setAge,
    manualAgeOverride, setManualAgeOverride,
    manualGenderOverride, setManualGenderOverride,
    dragOver, setDragOver,
    loading,
    error,
    result,
    handleAnalyze
  };
}
