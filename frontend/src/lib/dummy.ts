import type { AnalyzeResponse, AnalyzeResultItem } from "../types";

export const dummyResults: AnalyzeResultItem[] = [
  {
    resolved_key: "wbc",
    test_name: "WBC",
    value: 12.4,
    unit: "x10^3/µL",
    reference_range_text: "4.0 - 11.0 x10^3/µL",
    reference_low: 4.0,
    reference_high: 11.0,
    reference_unit: "x10^3/µL",
    status: "high",
    confidence: 1.0,
    match_type: "alias",
    explanation:
      "WBC measures infection-fighting cells.\nYour value is above the typical range.\nThis can happen with infection or inflammation.\nIf you feel unwell, consider medical advice.\nPlease consult your doctor.",
  },
  {
    resolved_key: "platelets",
    test_name: "Platelets",
    value: 220,
    unit: "x10^3/µL",
    reference_range_text: "150 - 450 x10^3/µL",
    reference_low: 150,
    reference_high: 450,
    reference_unit: "x10^3/µL",
    status: "normal",
    confidence: 1.0,
    match_type: "alias",
    explanation:
      "Platelets help blood clot.\nYour value is within the typical range.\nThis is usually reassuring.\nKeep following your clinician's guidance.\nPlease consult your doctor.",
  },
  {
    resolved_key: "hemoglobin",
    test_name: "Hemoglobin",
    value: 10.8,
    unit: "g/dL",
    reference_range_text: "12.0 - 15.5 g/dL",
    reference_low: 12.0,
    reference_high: 15.5,
    reference_unit: "g/dL",
    status: "low",
    confidence: 1.0,
    match_type: "alias",
    explanation:
      "Hemoglobin carries oxygen in your blood.\nYour value is below the typical range.\nThis can happen with low iron or blood loss.\nA clinician can guide next steps.\nPlease consult your doctor.",
  },
  {
    resolved_key: "ldl",
    test_name: "LDL",
    value: 138,
    unit: "mg/dL",
    reference_range_text: "0 - 100 mg/dL",
    reference_low: 0,
    reference_high: 100,
    reference_unit: "mg/dL",
    status: "high",
    confidence: 1.0,
    match_type: "alias",
    explanation:
      "LDL is often called 'bad' cholesterol.\nYour value is above the optimal range.\nHigher LDL may raise long‑term heart risk.\nDiscuss targets and lifestyle options with a clinician.\nPlease consult your doctor.",
  },
];

export const dummyResponse: AnalyzeResponse = {
  patient: { gender: "female", age: 32 },
  completeness: { total_parsed: 4, resolved: 4, unresolved: 0, dropped: 0, status: "OK" },
  summary: { total: dummyResults.length, normal: 1, high: 2, low: 1, unknown: 0 },
  insights: {
    by_category: {
      "CBC": ["↓ Hemoglobin"],
      "Lipids": ["↑ LDL"],
    },
    patterns: [
      "Low hemoglobin may suggest anemia. This is not a diagnosis.",
      "High WBC may indicate infection or inflammation. This is not a diagnosis.",
      "High LDL may increase long-term heart risk. Consider discussing lifestyle and targets with a clinician.",
    ],
  },
  results: dummyResults,
  disclaimer: "This is not a medical diagnosis.",
};
