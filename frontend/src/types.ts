/** Structured clinical insight — fields may be absent for normal results. */
export interface ClinicalInsight {
  summary?: string;
  severity?: string;
  severity_comment?: string;
  possible_causes?: string[];
  suggested_next_steps?: string[];
  age_related_risk?: string;
  gender_related_risk?: string;
}

export type LabStatus = "low" | "normal" | "high" | "unknown" | "REVIEW_REQUIRED";

/**
 * Every result item returned by /analyze.
 * Reference range is ALWAYS flat scalars — never a nested object.
 */
export type AnalyzeResultItem = {
  /** Canonical test key used internally (e.g. "hemoglobin"). */
  resolved_key?: string | null;
  test_name: string;
  value: number;
  unit: string;
  status: LabStatus;
  /** Pre-formatted string ready to display, e.g. "13.5 - 17.5 g/dL" */
  reference_range_text: string;
  /** Raw numeric lower bound (may be null if unknown). */
  reference_low?: number | null;
  /** Raw numeric upper bound (may be null if unknown). */
  reference_high?: number | null;
  /** Unit string for the reference range. */
  reference_unit?: string | null;
  /** Confidence score 0–1 for the test resolution. */
  confidence: number;
  match_type: "alias" | "fuzzy" | "none";
  /** Groq-generated explanation string (empty string when not available). */
  explanation: string;
  /** Structured clinical insight object — null for normal results. */
  clinical_insight?: ClinicalInsight | null;
};

export interface InsightsByCategory {
  [category: string]: string[];
}

export interface Insights {
  by_category?: InsightsByCategory;
  patterns?: string[];
}

export interface CompletenessInfo {
  total_parsed: number;
  resolved: number;
  unresolved: number;
  dropped: number;
  status: "OK" | "INCOMPLETE";
}

export type AnalyzeResponse = {
  patient?: { gender: string; age: number };
  patient_detected?: {
    gender?: string | null;
    age?: number | null;
    gender_confidence?: string;
    age_confidence?: string;
  };
  completeness?: CompletenessInfo;
  summary?: { total: number; normal: number; high: number; low: number; unknown?: number };
  insights?: Insights;
  results: AnalyzeResultItem[];
  disclaimer?: string;
};

export interface ApiError {
  message: string;
  detail?: string | any;
  status?: number;
}
