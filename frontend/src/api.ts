import axios from "axios";
import { AnalyzeResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || window.location.origin;

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 180000,
});

// Add request interceptor to attach token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function analyzeReport(params: {
  gender: string;
  age: number;
  text?: string;
  file?: File | null;
}): Promise<AnalyzeResponse> {
  const fd = new FormData();
  fd.set("gender", params.gender);
  fd.set("age", String(params.age));
  
  console.log("[analyzeReport] Building FormData:", {
    gender: params.gender,
    age: params.age,
    has_text: !!params.text,
    text_length: params.text?.length || 0,
    text_preview: params.text?.substring(0, 100),
    has_file: !!params.file,
    file_name: params.file?.name,
  });
  
  if (params.text) {
    fd.set("text", params.text);
    console.log("[analyzeReport] Added text to FormData");
  }
  if (params.file) {
    fd.set("file", params.file);
    console.log("[analyzeReport] Added file to FormData");
  }

  // IMPORTANT: do NOT set Content-Type manually for FormData in the browser.
  // The browser/axios must add the multipart boundary; manual header often triggers
  // a failing preflight and/or a body the server can't parse.
  console.log("[analyzeReport] Sending POST request to /analyze");
  const res = await api.post<AnalyzeResponse>("/analyze", fd);
  console.log("[analyzeReport] Response received:", res.status);
  return res.data;
}
