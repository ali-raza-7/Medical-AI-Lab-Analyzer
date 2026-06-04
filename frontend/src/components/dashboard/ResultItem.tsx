import { motion } from "framer-motion";
import { AlertCircle } from "lucide-react";
import { Badge } from "../ui/badge";
import { AnalyzeResultItem } from "../../types";

interface ResultItemProps {
  result: AnalyzeResultItem;
  index: number;
}

function badgeVariant(status: string): "normal" | "high" | "low" | "unknown" {
  const s = status.toLowerCase();
  if (s === "normal") return "normal";
  if (s === "high") return "high";
  if (s === "low") return "low";
  return "unknown";
}

export function ResultItem({ result, index }: ResultItemProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="group rounded-xl border border-slate-200 bg-white p-5 transition hover:border-slate-300 hover:shadow-md dark:border-[#1e293b] dark:bg-[#0f172a] dark:hover:border-[#334155] dark:hover:shadow-lg"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="text-sm font-bold text-slate-900 group-hover:text-[#14b8a6] transition-colors dark:text-white">
            {result.test_name}
          </div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-[#64748b]">
            Reference:{" "}
            <span className="text-slate-500 dark:text-[#94a3b8]">
              {result.reference_range_text || "Unspecified"}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-lg font-bold text-slate-900 leading-none dark:text-white">
              {result.value}
            </div>
            <div className="text-[10px] font-bold uppercase text-slate-400 dark:text-[#64748b] mt-1">
              {result.unit}
            </div>
          </div>
          <Badge variant={badgeVariant(result.status)}>{result.status}</Badge>
        </div>
      </div>

      {(result.explanation || result.clinical_insight) && (
        <div className="mt-4 border-t border-slate-100 pt-4 grid gap-4 lg:grid-cols-2 dark:border-[#1e293b]">
          {result.explanation && (
            <div className="space-y-1">
              <div className="text-[9px] font-bold uppercase tracking-widest text-[#14b8a6]">
                Clinical Context
              </div>
              <p className="text-xs leading-relaxed text-slate-500 dark:text-[#94a3b8]">
                {result.explanation}
              </p>
            </div>
          )}
          {result.clinical_insight && typeof result.clinical_insight === "object" && (
            <div className="space-y-2">
              <div className="text-[9px] font-bold uppercase tracking-widest text-[#14b8a6]">
                AI Diagnostic Signal
              </div>
              {result.clinical_insight.summary && (
                <p className="text-xs text-slate-800 dark:text-white/90 leading-relaxed italic">
                  "{result.clinical_insight.summary}"
                </p>
              )}
              {result.clinical_insight.severity_comment && (
                <div className="flex items-center gap-1.5 text-[10px] font-bold text-red-500 dark:text-red-400">
                  <AlertCircle className="h-3 w-3" />
                  {result.clinical_insight.severity_comment}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
