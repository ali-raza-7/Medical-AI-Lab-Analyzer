import { memo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import type { AnalyzeResponse } from "../../types";

interface AnalysisSummaryProps {
  result: AnalyzeResponse;
}

export const AnalysisSummary = memo(function AnalysisSummary({ result }: AnalysisSummaryProps) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="bg-slate-50 dark:bg-[#1e293b]/30 pb-4">
        <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-[#94a3b8]">
          Analysis Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-px bg-slate-100 dark:bg-[#1e293b] p-0" role="group" aria-label="Analysis summary statistics">
        <div className="bg-white dark:bg-[#0f172a] p-4 text-center">
          <div className="text-2xl font-bold text-slate-900 dark:text-white" aria-live="polite">
            {result.results?.length || 0}
          </div>
          <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 dark:text-[#64748b] mt-1">
            Total Tests
          </div>
        </div>
        <div className="bg-white dark:bg-[#0f172a] p-4 text-center">
          <div className="text-2xl font-bold text-red-600 dark:text-[#ef4444]">
            {result.summary?.high || 0}
          </div>
          <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 dark:text-[#64748b] mt-1">
            Abnormal High
          </div>
        </div>
        <div className="bg-white dark:bg-[#0f172a] p-4 text-center">
          <div className="text-2xl font-bold text-amber-600 dark:text-[#f59e0b]">
            {result.summary?.low || 0}
          </div>
          <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 dark:text-[#64748b] mt-1">
            Abnormal Low
          </div>
        </div>
        <div className="bg-white dark:bg-[#0f172a] p-4 text-center">
          <div className="text-2xl font-bold text-emerald-600 dark:text-[#14b8a6]">
            {result.summary?.normal || 0}
          </div>
          <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 dark:text-[#64748b] mt-1">
            Optimal Range
          </div>
        </div>
      </CardContent>
    </Card>
  );
});
