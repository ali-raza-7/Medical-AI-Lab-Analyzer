import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { AnalyzeResponse } from "../../types";

interface BiomarkerChartProps {
  result: AnalyzeResponse;
  resolvedTheme: "light" | "dark";
}

export function BiomarkerChart({ result, resolvedTheme }: BiomarkerChartProps) {
  const chartData = result.results
    .filter((r) => typeof r.value === "number" && !isNaN(r.value))
    .slice(0, 8)
    .map((r) => ({
      name: r.test_name.length > 10 ? r.test_name.slice(0, 10) + "\u2026" : r.test_name,
      value: r.value,
    }));

  if (chartData.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-[#94a3b8]">
          Normalized Biomarker Scaling
        </CardTitle>
      </CardHeader>
      <CardContent className="h-64 pt-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="4 6"
              stroke={
                resolvedTheme === "dark"
                  ? "rgba(148,163,184,0.1)"
                  : "rgba(148,163,184,0.2)"
              }
              vertical={false}
            />
            <XAxis
              dataKey="name"
              tickLine={false}
              axisLine={false}
              fontSize={10}
              tick={{ fill: resolvedTheme === "dark" ? "#64748b" : "#94a3b8" }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              fontSize={10}
              tick={{ fill: resolvedTheme === "dark" ? "#64748b" : "#94a3b8" }}
            />
            <Tooltip
              cursor={{
                fill:
                  resolvedTheme === "dark"
                    ? "rgba(20,184,166,0.05)"
                    : "rgba(20,184,166,0.02)",
              }}
              contentStyle={{
                borderRadius: 12,
                border:
                  resolvedTheme === "dark" ? "1px solid #1e293b" : "1px solid #e2e8f0",
                background: resolvedTheme === "dark" ? "#0f172a" : "#ffffff",
                boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
              }}
              itemStyle={{
                color: resolvedTheme === "dark" ? "#f1f5f9" : "#0f172a",
                fontSize: 12,
              }}
            />
            <Bar dataKey="value" fill="#14b8a6" radius={[4, 4, 0, 0]} barSize={28} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
