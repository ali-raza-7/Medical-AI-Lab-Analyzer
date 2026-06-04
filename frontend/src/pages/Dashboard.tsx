import { FileText, Lock, Sparkles, LogIn } from "lucide-react";
import { Card, CardContent } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { useTheme } from "../lib/theme";
import { useAnalyzeReport } from "../lib/hooks";
import { useAuth } from "../lib/AuthContext";
import { Link } from "react-router-dom";

// Sub-components
import { PatientMetadataCard } from "../components/dashboard/PatientMetadataCard";
import { AnalysisUploader } from "../components/dashboard/AnalysisUploader";
import { AnalysisSummary } from "../components/dashboard/AnalysisSummary";
import { ClinicalInsights } from "../components/dashboard/ClinicalInsights";
import { BiomarkerChart } from "../components/dashboard/BiomarkerChart";
import { ResultList } from "../components/dashboard/ResultList";

export default function Dashboard() {
  const { user } = useAuth();
  const {
    file, setFile,
    text, setText,
    gender, setGender,
    age, setAge,
    setManualAgeOverride,
    setManualGenderOverride,
    dragOver, setDragOver,
    loading,
    error,
    result,
    handleAnalyze
  } = useAnalyzeReport();

  const { resolvedTheme } = useTheme();

  const isOutOfCredits = user && user.credits <= 0;
  const showAuthPrompt = error && error.includes("Free analysis used");

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-500">
      <div className="flex flex-col gap-1 mb-2">
        <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          Clinical Intelligence Dashboard
        </h2>
        <p className="text-sm text-slate-500 dark:text-[#94a3b8]">
          Precision analysis for laboratory diagnostic reports.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[400px,1fr]">
        <div className="space-y-6">
          <PatientMetadataCard
            age={age}
            gender={gender}
            setAge={setAge}
            setGender={setGender}
            setManualAgeOverride={setManualAgeOverride}
            setManualGenderOverride={setManualGenderOverride}
          />

          <Card>
            <CardContent className="pt-6">
              {showAuthPrompt ? (
                <div className="p-6 text-center space-y-4 animate-in zoom-in-95 duration-300">
                  <div className="mx-auto w-12 h-12 bg-amber-100 dark:bg-amber-900/30 text-amber-600 rounded-full flex items-center justify-center">
                    <Lock className="h-6 w-6" />
                  </div>
                  <h3 className="font-bold text-slate-900 dark:text-white">Free Limit Reached</h3>
                  <p className="text-sm text-slate-500">Sign up now to get 5 free credits and unlock your full analysis history.</p>
                  <Link to="/signup">
                    <button className="w-full mt-2 py-3 bg-emerald-500 text-white rounded-xl font-bold hover:bg-emerald-600 transition-all shadow-lg shadow-emerald-500/20">
                      Sign Up for Free
                    </button>
                  </Link>
                  <p className="text-[10px] text-slate-400">Already have an account? <Link to="/login" className="text-emerald-500 hover:underline">Sign In</Link></p>
                </div>
              ) : isOutOfCredits ? (
                <div className="p-6 text-center space-y-4 animate-in zoom-in-95 duration-300">
                   <div className="mx-auto w-12 h-12 bg-amber-100 dark:bg-amber-900/30 text-amber-600 rounded-full flex items-center justify-center">
                    <Sparkles className="h-6 w-6" />
                  </div>
                  <h3 className="font-bold text-slate-900 dark:text-white">Out of Credits</h3>
                  <p className="text-sm text-slate-500">You've used all your analysis credits. Top up to continue using the AI assistant.</p>
                  <button className="w-full py-3 bg-amber-500 text-white rounded-xl font-bold hover:bg-amber-600 transition-all shadow-lg shadow-amber-500/20">
                    Buy Credits
                  </button>
                </div>
              ) : (
                <AnalysisUploader
                  file={file}
                  setFile={setFile}
                  text={text}
                  setText={setText}
                  dragOver={dragOver}
                  setDragOver={setDragOver}
                  loading={loading}
                  error={error}
                  handleAnalyze={handleAnalyze}
                />
              )}
            </CardContent>
          </Card>

          {result && <AnalysisSummary result={result} />}
        </div>

        <div className="space-y-6">
          {!result && !loading && (
            <div className="flex h-full min-h-[400px] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white p-12 text-center dark:border-[#1e293b] dark:bg-[#0f172a]/50">
              <div className="rounded-full bg-slate-50 p-4 mb-4 dark:bg-[#1e293b]">
                <FileText className="h-8 w-8 text-slate-300 dark:text-[#64748b]" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                {user ? "Ready for Analysis" : "Analyze for Free"}
              </h3>
              <p className="mt-2 text-sm text-slate-500 dark:text-[#64748b] max-w-sm">
                {user 
                  ? "Upload a report to use 1 of your credits for a full AI diagnostic evaluation." 
                  : "First-time users get one free analysis. Upload your report to begin."}
              </p>
              {!user && (
                <Link to="/login" className="mt-6 flex items-center gap-2 text-sm font-semibold text-emerald-500 hover:text-emerald-600 transition-colors">
                  <LogIn className="h-4 w-4" /> Sign in for more features
                </Link>
              )}
            </div>
          )}

          {loading && (
            <Card className="h-full">
              <CardContent className="p-8 space-y-6 pt-8">
                <div className="flex items-center gap-4">
                  <Skeleton className="h-12 w-12 rounded-full" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-1/4" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                </div>
                <div className="space-y-3">
                  <Skeleton className="h-20 w-full rounded-xl" />
                  <Skeleton className="h-40 w-full rounded-xl" />
                  <Skeleton className="h-32 w-full rounded-xl" />
                </div>
              </CardContent>
            </Card>
          )}

          {result && (
            <div className="space-y-6 animate-in fade-in duration-700">
              <ClinicalInsights result={result} />
              <BiomarkerChart result={result} resolvedTheme={resolvedTheme} />
              <ResultList result={result} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
