import { useState } from "react";
import { analyzeReport } from "../api";
import { AnalyzeResponse, ApiError } from "../types";
import { useAuth } from "./AuthContext";

export function useAnalyzeReport() {
  const { refreshUser } = useAuth();
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

  const handleAnalyze = async () => {
    if (!file && (!text || text.trim() === "")) {
      setError("Input required: Please upload a file or provide report text.");
      return;
    }
    
    console.log("[handleAnalyze] Starting analysis:", {
      has_file: !!file,
      file_name: file?.name,
      has_text: !!text,
      text_length: text?.length || 0,
      text_preview: text?.substring(0, 100),
      gender,
      age,
    });
    
    setError("");
    setLoading(true);
    setResult(null);
    try {
      console.log("[handleAnalyze] Calling analyzeReport...");
      const data = await analyzeReport({ file, text, gender, age });
      console.log("[handleAnalyze] Analysis successful");
      
      if (!data || !Array.isArray(data.results)) {
        throw new Error("Invalid response format from server");
      }
      const detected = data.patient_detected ?? null;
      if (detected) {
        if (detected.gender && !manualGenderOverride) {
          setGender(detected.gender);
        }
        if (typeof detected.age === "number" && !manualAgeOverride) {
          setAge(detected.age);
        }
      }
      setResult(data);
      // Refresh credits after successful analysis
      await refreshUser();
    } catch (err: unknown) {
      console.error("[handleAnalyze] Error:", err);
      let message = "Failed to analyze report";
      
      if (err instanceof Error) {
        message = err.message;
      }
      
      // Axios error handling with improved type safety
      const axiosError = err as any;
      if (axiosError.response?.data?.detail) {
        const detail = axiosError.response.data.detail;
        message = typeof detail === "string" ? detail : JSON.stringify(detail);
      }
      
      console.error("[handleAnalyze] Final error message:", message);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

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
