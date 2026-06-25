import axios from "axios";
import type { AnalyzeResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || window.location.origin;
const POLL_INTERVAL = 3000;
const MAX_POLL_ATTEMPTS = 60;

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  withCredentials: true,
  headers: {
    "X-Requested-With": "XMLHttpRequest",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
  },
});

const AUTH_ROUTES = new Set(["/me", "/login", "/signup", "/refresh"]);

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const url = err.config?.url || "";
    if (err.response?.status === 401 && !err.config._retry && !AUTH_ROUTES.has(url)) {
      err.config._retry = true;
      try {
        const refreshRes = await axios.post(`${API_BASE_URL}/refresh`, {}, { withCredentials: true });
        if (refreshRes.data.access_token) {
          err.config.headers.Authorization = `Bearer ${refreshRes.data.access_token}`;
          return api(err.config);
        }
      } catch {
        if (!window.location.pathname.startsWith("/login")) {
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(err);
  },
);

export async function analyzeReport(params: {
  gender: string;
  age: number;
  text?: string;
  file?: File | null;
}): Promise<{ task_id: string }> {
  const fd = new FormData();
  fd.set("gender", params.gender);
  fd.set("age", String(params.age));

  if (params.text) {
    fd.set("text", params.text);
  }
  if (params.file) {
    fd.set("file", params.file);
  }

  const res = await api.post<{ task_id: string }>("/analyze", fd);
  return res.data;
}

export async function waitForResult(
  task_id: string,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  let attempts = 0;

  while (attempts < MAX_POLL_ATTEMPTS) {
    if (signal?.aborted) {
      throw new DOMException("Polling cancelled", "AbortError");
    }

    const res = await api.get<{
      status: string;
      result?: AnalyzeResponse;
      error?: string;
      progress?: string;
    }>(`/status/${task_id}?_=${Date.now()}`);

    if (res.data.status === "complete" && res.data.result) {
      return res.data.result;
    }
    if (res.data.status === "failed" || res.data.status === "not_found") {
      throw new Error(res.data.error || "Analysis failed");
    }

    attempts++;
    await new Promise((r) => setTimeout(r, POLL_INTERVAL));
  }

  throw new Error("Analysis is taking too long. Please try again.");
}
