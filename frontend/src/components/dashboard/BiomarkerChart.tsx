import { memo, useState, useCallback, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { RangeBarModal } from "./RangeBarModal";
import type { AnalyzeResponse, AnalyzeResultItem, LabStatus } from "../../types";

// Props
interface BiomarkerChartProps {
  result: AnalyzeResponse;
  resolvedTheme: "light" | "dark";
}

// Internal entry shape
interface ChartEntry {
  original: AnalyzeResultItem;
  name: string;
  pct: number;          // normalized %, may exceed 100
  displayPct: string;   // label shown on the bar  e.g. "68%" or "150%"
  barPct: number;       // clamped 0–100 for the visible fill width
  color: string;
  trackColor: string;
  status: LabStatus;
}

// Helpers

/** Exact same calculation as the original BiomarkerChart */
function calcPct(r: AnalyzeResultItem): number {
  if (r.reference_high != null && r.reference_high > 0) {
    return (r.value / r.reference_high) * 100;
  } else if (r.reference_low != null && r.reference_low > 0) {
    return (r.value / (r.reference_low * 2)) * 100;
  }
  return 50;
}

function statusColors(status: LabStatus, pct: number): { fill: string; track: string } {
  if (status === "high" || pct > 100) {
    return { fill: "#ef4444", track: "rgba(239,68,68,0.12)" };
  }
  if (status === "low") {
    return { fill: "#64748b", track: "rgba(100,116,139,0.12)" };
  }
  if (pct >= 90) {
    return { fill: "#f97316", track: "rgba(249,115,22,0.12)" };
  }
  if (status === "normal") {
    return { fill: "#22c55e", track: "rgba(34,197,94,0.12)" };
  }
  return { fill: "#94a3b8", track: "rgba(148,163,184,0.12)" };
}

// Animated Bar Row
interface BarRowProps {
  entry: ChartEntry;
  index: number;
  onClick: (entry: ChartEntry) => void;
  isDark: boolean;
}

const BarRow = memo(function BarRow({ entry, index, onClick, isDark }: BarRowProps) {
  const [width, setWidth] = useState(0);
  const [hovered, setHovered] = useState(false);
  const [tooltipVisible, setTooltipVisible] = useState(false);
  const rowRef = useRef<HTMLDivElement>(null);

  // Staggered entrance animation
  useEffect(() => {
    const timer = setTimeout(() => {
      setWidth(entry.barPct);
    }, 80 + index * 40);
    return () => clearTimeout(timer);
  }, [entry.barPct, index]);

  const nameLabelColor = isDark ? "#e2e8f0" : "#1e293b";
  const pctLabelColor = isDark ? "#cbd5e1" : "#475569";
  const tooltipBg = isDark ? "#0f172a" : "#ffffff";
  const tooltipBorder = isDark ? "#1e293b" : "#e2e8f0";

  return (
    <div
      ref={rowRef}
      className="relative group"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      {/* Tooltip */}
      {tooltipVisible && (
        <div
          className="absolute z-50 rounded-xl px-3 py-2.5 text-xs shadow-xl pointer-events-none left-4 right-auto sm:left-[200px]"
          style={{
            background: tooltipBg,
            border: `1px solid ${tooltipBorder}`,
            bottom: "calc(100% + 8px)",
            minWidth: "180px",
          }}
        >
          <p
            className="font-bold mb-1 text-sm"
            style={{ color: isDark ? "#f1f5f9" : "#0f172a" }}
          >
            {entry.original.test_name}
          </p>
          <p style={{ color: pctLabelColor }}>
            Value:{" "}
            <span className="font-semibold">
              {entry.original.value} {entry.original.unit}
            </span>
          </p>
          <p style={{ color: pctLabelColor }}>
            Reference:{" "}
            <span className="font-semibold">
              {entry.original.reference_range_text || "N/A"}
            </span>
          </p>
          <p
            className="mt-1 font-bold uppercase text-[10px] tracking-wider"
            style={{ color: entry.color }}
          >
            {entry.original.status}
          </p>
          <p
            className="text-[10px] mt-0.5"
            style={{ color: isDark ? "#64748b" : "#94a3b8" }}
          >
            Click for detailed range view
          </p>
        </div>
      )}

      <div
        className="flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-3 py-[7px] px-2 rounded-lg cursor-pointer transition-all duration-150"
        style={{
          background: hovered
            ? isDark
              ? "rgba(30,41,59,0.6)"
              : "rgba(241,245,249,0.8)"
            : "transparent",
        }}
        onClick={() => onClick(entry)}
        onMouseEnter={() => { setHovered(true); setTooltipVisible(true); }}
        onMouseLeave={() => { setHovered(false); setTooltipVisible(false); }}
        onFocus={() => setTooltipVisible(true)}
        onBlur={() => setTooltipVisible(false)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick(entry);
          }
        }}
        aria-label={`${entry.original.test_name}: ${entry.displayPct} of reference range, status ${entry.original.status}`}
      >
        {/* Biomarker name column */}
        <div
          className="flex justify-between items-center w-full sm:w-[160px] sm:min-w-[100px] flex-shrink-0 sm:text-right"
        >
          <span
            className="text-[12px] font-medium leading-tight block truncate"
            style={{ color: nameLabelColor }}
            title={entry.original.test_name}
          >
            {entry.name}
          </span>
          <span
            className="sm:hidden font-bold tabular-nums text-[12px]"
            style={{ color: entry.color }}
          >
            {entry.displayPct}
          </span>
        </div>

        {/* Bar track */}
        <div
          className="flex-1 relative h-[18px] rounded-full overflow-visible"
          style={{ background: entry.trackColor, minWidth: 0 }}
        >
          {/* Guide lines at 25 / 50 / 75 / 100 % */}
          {[25, 50, 75, 100].map((mark) => (
            <div
              key={mark}
              className="absolute top-0 bottom-0 w-px pointer-events-none"
              style={{
                left: `${mark}%`,
                background: isDark
                  ? "rgba(148,163,184,0.15)"
                  : "rgba(100,116,139,0.15)",
                zIndex: 1,
              }}
            />
          ))}

          {/* Filled portion — animated width */}
          <div
            className="absolute inset-y-0 left-0 rounded-full"
            style={{
              width: `${width}%`,
              background: entry.color,
              transition: "width 700ms cubic-bezier(0.34, 1.56, 0.64, 1)",
              boxShadow:
                hovered
                  ? `0 0 10px ${entry.color}55`
                  : `0 0 4px ${entry.color}30`,
              zIndex: 2,
            }}
          />

          {/* Overflow glow cap when pct > 100 */}
          {entry.pct > 100 && (
            <div
              className="absolute inset-y-0 right-0 w-2 rounded-r-full pointer-events-none"
              style={{
                background: `linear-gradient(to right, transparent, ${entry.color}80)`,
                zIndex: 3,
              }}
            />
          )}
        </div>

        {/* Percentage label */}
        <div
          className="hidden sm:block flex-shrink-0 text-right font-bold tabular-nums text-[12px]"
          style={{
            width: "44px",
            color: entry.color,
          }}
        >
          {entry.displayPct}
        </div>
      </div>
    </div>
  );
});

// Guide line header
function GuideHeader({ isDark }: { isDark: boolean }) {
  const labelColor = isDark ? "#475569" : "#94a3b8";
  return (
    <div className="flex items-center gap-3 mb-1 select-none px-2" aria-hidden="true">
      {/* spacer for name column */}
      <div className="hidden sm:block flex-shrink-0" style={{ width: "160px", minWidth: "100px" }} />
      {/* guide labels row */}
      <div className="flex-1 relative h-4" style={{ minWidth: 0 }}>
        {[0, 25, 50, 75, 100].map((mark) => (
          <span
            key={mark}
            className="absolute -translate-x-1/2 text-[9px] font-medium"
            style={{
              left: `${mark}%`,
              color: labelColor,
              top: 0,
              lineHeight: 1,
            }}
          >
            {mark}%
          </span>
        ))}
      </div>
      {/* spacer for pct label column */}
      <div className="hidden sm:block flex-shrink-0" style={{ width: "44px" }} />
    </div>
  );
}

// Legend
function Legend({ isDark }: { isDark: boolean }) {
  const mutedColor = isDark ? "#475569" : "#94a3b8";
  const items = [
    { color: "#22c55e", label: "Normal" },
    { color: "#f97316", label: "Near threshold (≥90%)" },
    { color: "#ef4444", label: "Above normal (>100%)" },
    { color: "#64748b", label: "Below normal" },
  ];
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-4 pt-3 border-t border-slate-100 dark:border-[#1e293b]">
      {items.map(({ color, label }) => (
        <div key={label} className="flex items-center gap-1.5">
          <span
            className="inline-block h-2 w-2 rounded-full flex-shrink-0"
            style={{ background: color }}
          />
          <span className="text-[10px] font-medium" style={{ color: mutedColor }}>
            {label}
          </span>
        </div>
      ))}
    </div>
  );
}

// Main component
export const BiomarkerChart = memo(function BiomarkerChart({
  result,
  resolvedTheme,
}: BiomarkerChartProps) {
  const [selected, setSelected] = useState<AnalyzeResultItem | null>(null);
  const isDark = resolvedTheme === "dark";

  // Build entries — identical calculation to original, just new shape
  const chartData: ChartEntry[] = result.results
    .filter((r) => typeof r.value === "number" && !Number.isNaN(r.value))
    .map((r) => {
      const pct = Math.min(calcPct(r), 200); // cap at 200 for extreme outliers
      const barPct = Math.min(pct, 100);     // clamp visible bar at 100
      const { fill, track } = statusColors(r.status, pct);
      return {
        original: r,
        name: r.test_name,                  // full name — no truncation in data
        pct,
        displayPct: `${Math.round(pct)}%`,
        barPct,
        color: fill,
        trackColor: track,
        status: r.status,
      };
    });

  const handleClick = useCallback(
    (entry: ChartEntry) => setSelected(entry.original),
    []
  );

  // Empty state
  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-[#94a3b8]">
            Normalized Biomarker Scaling
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-400 dark:text-[#64748b] text-center py-8">
            No biomarker data available.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Chart
  return (
    <>
      <Card>
        <CardHeader className="pb-1">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-[#94a3b8]">
              Normalized Biomarker Scaling
            </CardTitle>
            <span className="text-[10px] font-medium text-slate-400 dark:text-[#64748b]">
              {chartData.length} biomarker{chartData.length !== 1 ? "s" : ""}
              {" · "}% of reference upper limit · click any row for details
            </span>
          </div>
        </CardHeader>

        <CardContent className="pt-2 pb-4">
          {/* Guide header */}
          <GuideHeader isDark={isDark} />

          {/* Hairline separator */}
          <div
            className="mb-1 ml-2 mr-2 sm:ml-[180px] sm:mr-[64px]"
            style={{
              height: "1px",
              background: isDark
                ? "rgba(148,163,184,0.08)"
                : "rgba(148,163,184,0.15)",
            }}
          />

          {/* Bar rows */}
          <div className="flex flex-col">
            {chartData.map((entry, idx) => (
              <BarRow
                key={entry.original.resolved_key ?? entry.original.test_name + idx}
                entry={entry}
                index={idx}
                onClick={handleClick}
                isDark={isDark}
              />
            ))}
          </div>

          {/* Legend */}
          <Legend isDark={isDark} />
        </CardContent>
      </Card>

      {/* Detail modal — unchanged */}
      {selected && (
        <RangeBarModal result={selected} onClose={() => setSelected(null)} />
      )}
    </>
  );
});
