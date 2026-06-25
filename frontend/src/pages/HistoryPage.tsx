import React from 'react';
import { Card, CardContent } from '../components/ui/card';
import { FileText, Calendar, ArrowRight, AlertTriangle } from 'lucide-react';
import { AnalysisSummary } from '../components/dashboard/AnalysisSummary';
import { ClinicalInsights } from '../components/dashboard/ClinicalInsights';
import { BiomarkerChart } from '../components/dashboard/BiomarkerChart';
import { ResultList } from '../components/dashboard/ResultList';
import { useTheme } from '../lib/theme';
import { useAuth } from '../lib/AuthContext';
import { useHistory } from '../lib/useHistory';
import { Link } from 'react-router-dom';
import type { AnalyzeResponse } from '../types';

const HistoryPage: React.FC = () => {
  const { resolvedTheme } = useTheme();
  const { user } = useAuth();
  const { history, loading, error } = useHistory();
  const [selectedId, setSelectedId] = React.useState<string | null>(null);

  const selectedAnalysis = history.find((h) => h.id === selectedId) || null;

  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4" role="region" aria-label="Sign in required">
        <div className="p-4 bg-amber-100 dark:bg-amber-900/30 rounded-full">
          <AlertTriangle className="h-8 w-8 text-amber-500" />
        </div>
        <h2 className="text-xl font-bold dark:text-white">Sign In Required</h2>
        <p className="text-sm text-slate-500 text-center max-w-sm">You need to sign in to view your analysis history.</p>
        <Link to="/login" className="px-6 py-2 bg-emerald-500 text-white rounded-xl font-bold hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-500/20">
          Sign In
        </Link>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-6" role="status" aria-label="Loading history">
        <div className="flex flex-col gap-1">
          <div className="h-8 w-48 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
          <div className="h-4 w-64 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800/50" />
        </div>
        <div className="grid gap-6 lg:grid-cols-[350px,1fr]">
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Analysis History</h2>
        <p className="text-sm text-slate-500 dark:text-[#94a3b8]">View and manage your past laboratory reports.</p>
      </div>

      {error && (
        <div className="p-4 text-sm text-red-500 bg-red-100 dark:bg-red-900/30 rounded-lg" role="alert">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[350px,1fr]">
        <div className="space-y-4" role="list" aria-label="Analysis history list">
          {history.length === 0 ? (
            <div className="p-8 text-center bg-white dark:bg-slate-900 rounded-2xl border-2 border-dashed border-slate-200 dark:border-slate-800 text-slate-400">
              No past analyses found. Analyze a report first!
            </div>
          ) : (
            history.map((item) => (
              <Card 
                key={item.id}
                className={`cursor-pointer transition-all hover:ring-2 hover:ring-emerald-500/50 ${selectedId === item.id ? 'ring-2 ring-emerald-500' : ''}`}
                onClick={() => setSelectedId(item.id)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setSelectedId(item.id); }}
                role="listitem"
                tabIndex={0}
                aria-label={`Analysis from ${item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Unknown date'}`}
                aria-current={selectedId === item.id ? 'true' : undefined}
              >
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg text-emerald-600 dark:text-emerald-400">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="flex flex-col overflow-hidden">
                      <span className="text-sm font-semibold truncate dark:text-white">{item.file_name || 'Unnamed Report'}</span>
                      <div className="flex items-center gap-1 text-[10px] text-slate-500">
                        <Calendar className="h-3 w-3" />
                        {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Unknown date'}
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-slate-300" />
                </CardContent>
              </Card>
            ))
          )}
        </div>

        <div className="space-y-6" aria-live="polite" aria-label="Analysis detail">
          {selectedAnalysis ? (
            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
              <AnalysisSummary result={selectedAnalysis.results_json} />
              <ClinicalInsights result={selectedAnalysis.results_json} />
              <BiomarkerChart result={selectedAnalysis.results_json} resolvedTheme={resolvedTheme} />
              <ResultList result={selectedAnalysis.results_json} />
            </div>
          ) : (
            <div className="flex h-[400px] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/50 text-center p-12">
               <FileText className="h-12 w-12 text-slate-200 dark:text-slate-800 mb-4" />
               <h3 className="text-lg font-medium text-slate-900 dark:text-white">No Analysis Selected</h3>
               <p className="text-sm text-slate-500">Select an analysis from the list to view detailed results.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;
