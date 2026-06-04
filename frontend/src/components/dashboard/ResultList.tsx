import { Badge } from "../ui/badge";
import { ResultItem } from "./ResultItem";
import { AnalyzeResponse } from "../../types";

interface ResultListProps {
  result: AnalyzeResponse;
}

export function ResultList({ result }: ResultListProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500 dark:text-[#94a3b8]">
          Detailed Diagnostic Results
        </h3>
        <Badge variant="outline">{result.results.length} Tests Parsed</Badge>
      </div>

      <div className="grid gap-3">
        {result.results.map((r, idx) => (
          <ResultItem key={idx} result={r} index={idx} />
        ))}
      </div>
    </div>
  );
}
