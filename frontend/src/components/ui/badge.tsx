import * as React from "react";
import { cn } from "../../lib/utils";

type Variant = "normal" | "high" | "low" | "unknown" | "info" | "outline";

export function Badge({
  className,
  variant = "info",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  const v: Record<Variant, string> = {
    normal: "bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-[#14b8a6]/10 dark:text-[#14b8a6] dark:ring-[#14b8a6]/20",
    high: "bg-red-50 text-red-700 ring-red-200 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20",
    low: "bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/20",
    unknown: "bg-slate-50 text-slate-600 ring-slate-200 dark:bg-slate-500/10 dark:text-slate-400 dark:ring-slate-500/20",
    info: "bg-blue-50 text-blue-700 ring-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:ring-blue-500/20",
    outline: "bg-transparent text-slate-600 ring-slate-200 dark:text-[#64748b] dark:ring-[#1e293b]",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-tight ring-1",
        v[variant],
        className,
      )}
      role="status"
      aria-label={`Status: ${variant}`}
      {...props}
    />
  );
}
