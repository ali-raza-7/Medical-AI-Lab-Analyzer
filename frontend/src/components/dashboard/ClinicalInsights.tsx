import { memo } from "react";
import { Brain, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import type { AnalyzeResponse } from "../../types";

interface ClinicalInsightsProps {
  result: AnalyzeResponse;
}

export const ClinicalInsights = memo(function ClinicalInsights({ result }: ClinicalInsightsProps) {
  return (
    <Card>
      <CardHeader className="border-b border-slate-100 dark:border-[#1e293b]/50 pb-4">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-[#14b8a6]" aria-hidden="true" />
          <CardTitle className="text-xs font-bold uppercase tracking-widest text-slate-500 dark:text-[#94a3b8]">
            AI Clinical Interpretation
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-6">
        {result.insights?.by_category &&
        Object.keys(result.insights.by_category).length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2" role="list" aria-label="Clinical insights by category">
            {Object.entries(result.insights.by_category).map(([category, flags]) => (
              <div
                key={category}
                className="rounded-xl bg-slate-50 p-4 border border-slate-200 dark:bg-[#020617] dark:border-[#1e293b]"
                role="listitem"
              >
                <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#14b8a6] mb-3">
                  {category}
                </div>
                <div className="space-y-2">
                  {Array.isArray(flags) &&
                    flags.map((flag, i) => (
                      <div
                        key={`${category}-${i}`}
                        className="flex gap-2 text-sm text-slate-600 dark:text-[#cbd5e1]"
                      >
                        <CheckCircle2 className="h-4 w-4 text-[#14b8a6] shrink-0 mt-0.5" aria-hidden="true" />
                        <span>{flag}</span>
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6 text-sm text-slate-400 dark:text-[#64748b]">
            No specific diagnostic patterns identified.
          </div>
        )}
      </CardContent>
    </Card>
  );
});
