import { UploadCloud, AlertCircle, Activity, FileText, ImageIcon } from "lucide-react";
import { Button } from "../ui/button";
import { cn } from "../../lib/utils";

interface AnalysisUploaderProps {
  file: File | null;
  setFile: (file: File | null) => void;
  text: string;
  setText: (text: string) => void;
  dragOver: boolean;
  setDragOver: (val: boolean) => void;
  loading: boolean;
  error: string;
  handleAnalyze: () => void;
}

export function AnalysisUploader({
  file,
  setFile,
  text,
  setText,
  dragOver,
  setDragOver,
  loading,
  error,
  handleAnalyze,
}: AnalysisUploaderProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label htmlFor="file-upload" className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-[#64748b]">
          Diagnostic Input
        </label>
        <div
          onDragEnter={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files?.[0]; if (f) setFile(f); }}
          className={cn(
            "relative flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-6 transition-all",
            dragOver
              ? "border-[#14b8a6] bg-[#14b8a6]/5"
              : "border-slate-200 bg-slate-50 hover:border-slate-300 dark:border-[#1e293b] dark:bg-[#020617] dark:hover:border-[#334155]",
          )}
          role="button"
          tabIndex={0}
          aria-label="Upload report file"
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') document.getElementById('file-upload')?.click(); }}
        >
          {file ? (
            file.name.endsWith(".pdf") ? (
              <FileText className={cn("h-8 w-8 transition-colors", "text-[#14b8a6]")} />
            ) : (
              <ImageIcon className={cn("h-8 w-8 transition-colors", "text-[#14b8a6]")} />
            )
          ) : (
            <UploadCloud className="h-8 w-8 text-slate-300 dark:text-[#64748b]" />
          )}
          <div className="text-center">
            <div className="text-xs font-medium text-slate-900 dark:text-white">
              {file ? file.name : "Upload Report"}
            </div>
            <div className="mt-1 text-[10px] text-slate-400 dark:text-[#64748b]">
              {file
                ? file.name.endsWith(".pdf")
                  ? "PDF text + embedded images will be extracted"
                  : "OCR engine will extract clinical data"
                : "PNG, JPG, WEBP, PDF, HEIC"}
            </div>
          </div>
          <input
            id="file-upload"
            type="file"
            accept=".png,.jpg,.jpeg,.webp,.bmp,.tiff,.tif,.pdf,.heic,.heif"
            className="absolute inset-0 opacity-0 cursor-pointer"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            aria-label="Choose report file"
          />
        </div>
      </div>

      <div className="space-y-2">
        <label htmlFor="clinical-text" className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-[#64748b]">
          Clinical Text Override
        </label>
        <textarea
          id="clinical-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste raw laboratory data here..."
          className="h-24 w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-[#14b8a6] focus:ring-1 focus:ring-[#14b8a6]/20 dark:border-[#1e293b] dark:bg-[#020617] dark:text-white"
        />
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg bg-red-500/10 p-3 text-xs text-red-600 border border-red-200 dark:text-red-400 dark:border-red-500/20" role="alert">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <Button
        variant="clinical"
        size="lg"
        className="w-full"
        onClick={handleAnalyze}
        disabled={loading}
        aria-label={loading ? "Analyzing report..." : "Start analysis"}
      >
        {loading ? (
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white" role="status" aria-label="Analyzing" />
        ) : (
          <>
            <Activity className="mr-2 h-4 w-4" />
            Initialize Analysis
          </>
        )}
      </Button>
    </div>
  );
}
