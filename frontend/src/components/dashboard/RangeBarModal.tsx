import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import type { AnalyzeResultItem } from "../../types";

interface RangeBarModalProps {
  result: AnalyzeResultItem;
  onClose: () => void;
}

function statusColor(status: string): string {
  const s = status.toLowerCase();
  if (s === "low") return "#ef4444";
  if (s === "high") return "#ef4444";
  if (s === "normal") return "#22c55e";
  return "#94a3b8";
}

function clamp(val: number, min: number, max: number): number {
  return Math.min(Math.max(val, min), max);
}

export function RangeBarModal({ result, onClose }: RangeBarModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const low = result.reference_low;
  const high = result.reference_high;
  const val = result.value;
  const refUnit = result.reference_unit || result.unit;

  const hasRange = low != null && high != null && low < high;

  const barLow = hasRange ? low! : 0;
  const barHigh = hasRange ? high! : 1;
  const range = barHigh - barLow;

  const pctLow = hasRange ? 0 : 33;
  const pctHigh = hasRange ? 100 : 66;
  const pctVal = hasRange
    ? ((clamp(val, barLow - range * 0.3, barHigh + range * 0.3) - (barLow - range * 0.3)) / (range * 1.6)) * 100
    : 50;

  const isLow = result.status.toLowerCase() === "low";
  const isHigh = result.status.toLowerCase() === "high";

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-label={`Reference range for ${result.test_name}`}
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl dark:bg-[#0f172a] dark:border dark:border-[#1e293b] mx-4 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">
            {result.test_name}
          </h3>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-[#1e293b] dark:hover:text-white"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="text-center mb-6">
          <span className="text-4xl font-bold text-slate-900 dark:text-white">
            {val}
          </span>
          <span className="ml-2 text-sm font-medium text-slate-400 dark:text-[#64748b]">
            {result.unit}
          </span>
        </div>

        {hasRange && (
          <div className="space-y-2 mb-5">
            <div className="relative h-4 w-full">
              <div className="absolute inset-0 rounded-full bg-gradient-to-r from-red-400 via-green-500 to-red-400" />

              <div
                className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 z-10 flex items-center justify-center"
                style={{ left: `${pctVal}%` }}
              >
                <div className="h-4 w-1 rounded-full bg-white shadow-md" />
                <div className="absolute -bottom-5 text-[10px] font-bold text-slate-600 dark:text-[#94a3b8] whitespace-nowrap">
                  Your Value
                </div>
              </div>
            </div>

            <div className="flex justify-between text-[11px] font-medium text-slate-500 dark:text-[#64748b]">
              <span>{low}</span>
              <span>{high}</span>
            </div>
            <div className="flex justify-between text-[10px] text-slate-400 dark:text-[#64748b]">
              <span>{refUnit}</span>
              <span>{refUnit}</span>
            </div>
          </div>
        )}

        {result.reference_range_text && (
          <div className="text-center text-sm text-slate-500 dark:text-[#94a3b8] mb-4">
            Reference Range:{" "}
            <span className="font-semibold text-slate-700 dark:text-white">
              {result.reference_range_text}
            </span>
          </div>
        )}

        <div className="flex justify-center">
          <span
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold"
            style={{
              backgroundColor: `${statusColor(result.status)}15`,
              color: statusColor(result.status),
            }}
          >
            <span
              className="h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: statusColor(result.status) }}
            />
            {result.status}
          </span>
        </div>
      </div>
    </div>
  );
}
