import React, { useState, useCallback } from 'react';
import { api } from '../api';
import { Card, CardContent } from '../components/ui/card';
import { ArrowLeftRight, CheckCircle, XCircle, MinusCircle, AlertTriangle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { useAuth } from '../lib/AuthContext';
import { useHistory } from '../lib/useHistory';
import { Link } from 'react-router-dom';

interface ComparisonTestItem {
  test_name: string;
  prev_value: number;
  curr_value: number;
  unit: string;
  change_pct: number;
}

interface ComparisonResult {
  improved: ComparisonTestItem[];
  worsened: ComparisonTestItem[];
  stable: ComparisonTestItem[];
  summary: string;
}

function formatChange(pct: number): string {
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(1)}%`;
}

const ComparePage: React.FC = () => {
  const { user } = useAuth();
  const { history, loading, error: historyError } = useHistory();
  const [selected, setSelected] = useState<string[]>([]);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState('');

  const handleSelect = useCallback((id: string) => {
    setSelected((prev) => {
      if (prev.includes(id)) {
        return prev.filter((i) => i !== id);
      }
      if (prev.length < 2) {
        return [...prev, id];
      }
      return prev;
    });
  }, []);

  const handleCompare = useCallback(async () => {
    if (selected.length !== 2) return;
    setComparing(true);
    setComparison(null);
    setError('');

    try {
      const s1 = history.find((h) => h.id === selected[0]);
      const s2 = history.find((h) => h.id === selected[1]);

      if (!s1 || !s2) {
        setError('Could not find selected analyses.');
        setComparing(false);
        return;
      }

      let id1 = selected[0];
      let id2 = selected[1];

      if (new Date(s1.created_at) > new Date(s2.created_at)) {
        id1 = selected[1];
        id2 = selected[0];
      }

      const res = await api.post('/compare', { id1, id2 });
      setComparison(res.data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } } };
      const msg = axiosErr.response?.data?.detail;
      setError(typeof msg === 'string' ? msg : 'Comparison failed. Please try again.');
    } finally {
      setComparing(false);
    }
  }, [selected, history]);

  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="p-4 bg-amber-100 dark:bg-amber-900/30 rounded-full">
          <AlertTriangle className="h-8 w-8 text-amber-500" />
        </div>
        <h2 className="text-xl font-bold dark:text-white">Sign In Required</h2>
        <p className="text-sm text-slate-500 text-center max-w-sm">You need to sign in to compare analyses.</p>
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
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Compare Analyses</h2>
        <p className="text-sm text-slate-500 dark:text-[#94a3b8]">Select two reports to track progress over time.</p>
      </div>

      {(error || historyError) && (
        <div className="p-4 text-sm text-red-500 bg-red-100 dark:bg-red-900/30 rounded-lg" role="alert">
          {error || historyError}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[350px,1fr]">
        <div className="space-y-4">
          <div className="p-4 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400" id="compare-select-label">
              Select Reports ({selected.length}/2)
            </h3>
            <div className="space-y-2" role="group" aria-labelledby="compare-select-label">
              {history.length === 0 ? (
                <div className="p-4 text-center text-sm text-slate-400 italic">
                  No analyses available. Analyze a report first!
                </div>
              ) : (
                history.map((item) => (
                  <div 
                    key={item.id}
                    onClick={() => handleSelect(item.id)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleSelect(item.id); }}
                    role="radio"
                    tabIndex={0}
                    aria-checked={selected.includes(item.id)}
                    aria-label={`Select analysis from ${item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Unknown date'}`}
                    className={`p-3 rounded-xl border-2 cursor-pointer transition-all flex items-center gap-3 ${selected.includes(item.id) ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20' : 'border-transparent bg-slate-50 dark:bg-slate-800/50'}`}
                  >
                    <div className={`h-4 w-4 rounded-full border-2 flex items-center justify-center ${selected.includes(item.id) ? 'bg-emerald-500 border-emerald-500' : 'border-slate-300'}`}>
                      {selected.includes(item.id) && (
                        <div className="h-1.5 w-1.5 rounded-full bg-white" />
                      )}
                    </div>
                    <div className="flex flex-col overflow-hidden">
                      <span className="text-xs font-semibold truncate dark:text-white">{item.file_name || 'Unnamed Report'}</span>
                      <span className="text-[10px] text-slate-500">{item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Unknown date'}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
            <Button 
              className="w-full" 
              variant="clinical"
              disabled={selected.length !== 2 || comparing}
              onClick={handleCompare}
              aria-label="Generate comparison of selected reports"
            >
              {comparing ? (
                <div className="flex items-center gap-2">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                  Comparing...
                </div>
              ) : (
                "Generate Comparison"
              )}
            </Button>
          </div>
        </div>

        <div className="space-y-6" aria-live="polite" aria-label="Comparison result">
          {comparison ? (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <Card className="border-l-4 border-l-teal-500">
                <CardContent className="p-6">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-teal-500 mb-2">
                    PERSONALIZED ANALYSIS
                  </p>
                  <h3 className="text-lg font-bold mb-4 flex items-center gap-2 dark:text-white">
                    <ArrowLeftRight className="h-5 w-5 text-teal-500" />
                    AI Comparison Summary
                  </h3>
                  <div className="text-slate-600 dark:text-slate-300 leading-relaxed space-y-2">
                    {comparison.summary.split('\n').filter(Boolean).map((para, i) => (
                      <p key={i} className="leading-relaxed">{para}</p>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <div className="grid gap-6 md:grid-cols-3">
                <Card className="bg-emerald-50/50 dark:bg-emerald-900/10 border-emerald-100 dark:border-emerald-900/20">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-2 mb-4 text-emerald-600 dark:text-emerald-400 font-bold uppercase tracking-wider text-xs">
                      <CheckCircle className="h-4 w-4" /> Improved
                    </div>
                    <div className="space-y-2">
                      {Array.isArray(comparison.improved) && comparison.improved.length > 0 ? comparison.improved.map((t: ComparisonTestItem) => (
                        <div key={t.test_name} className="text-sm bg-white dark:bg-slate-800 rounded-lg shadow-sm p-3 space-y-1">
                          <div className="font-semibold dark:text-white text-emerald-700 dark:text-emerald-300">&#10003; {t.test_name}</div>
                          <div className="text-xs text-slate-500">
                            {t.prev_value} → {t.curr_value} {t.unit}
                          </div>
                          <div className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                            {formatChange(t.change_pct)}
                          </div>
                        </div>
                      )) : <div className="text-xs text-slate-400 italic">No significant improvements</div>}
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-red-50/50 dark:bg-red-900/10 border-red-100 dark:border-red-900/20">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-2 mb-4 text-red-600 dark:text-red-400 font-bold uppercase tracking-wider text-xs">
                      <XCircle className="h-4 w-4" /> Worsened
                    </div>
                    <div className="space-y-2">
                      {Array.isArray(comparison.worsened) && comparison.worsened.length > 0 ? comparison.worsened.map((t: ComparisonTestItem) => (
                        <div key={t.test_name} className="text-sm bg-white dark:bg-slate-800 rounded-lg shadow-sm p-3 space-y-1">
                          <div className="font-semibold dark:text-white text-red-700 dark:text-red-300">&#10007; {t.test_name}</div>
                          <div className="text-xs text-slate-500">
                            {t.prev_value} → {t.curr_value} {t.unit}
                          </div>
                          <div className="text-xs font-medium text-red-600 dark:text-red-400">
                            {formatChange(t.change_pct)}
                          </div>
                        </div>
                      )) : <div className="text-xs text-slate-400 italic">No significant worsening</div>}
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-slate-50/50 dark:bg-slate-800/50 border-slate-100 dark:border-slate-800">
                  <CardContent className="p-6">
                    <div className="flex items-center gap-2 mb-4 text-slate-600 dark:text-slate-400 font-bold uppercase tracking-wider text-xs">
                      <MinusCircle className="h-4 w-4" /> Stable
                    </div>
                    <div className="space-y-2">
                      {Array.isArray(comparison.stable) && comparison.stable.length > 0 ? comparison.stable.map((t: ComparisonTestItem) => (
                        <div key={t.test_name} className="text-sm bg-white dark:bg-slate-800 rounded-lg shadow-sm p-3 space-y-1">
                          <div className="font-semibold dark:text-white">{t.test_name}</div>
                          <div className="text-xs text-slate-500">
                            {t.prev_value} → {t.curr_value} {t.unit}
                          </div>
                          <div className="text-xs font-medium text-slate-500">
                            {formatChange(t.change_pct)}
                          </div>
                        </div>
                      )) : <div className="text-xs text-slate-400 italic">No stable biomarkers</div>}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
            <div className="flex h-[400px] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/50 text-center p-12">
               <ArrowLeftRight className="h-12 w-12 text-slate-200 dark:text-slate-800 mb-4" />
               <h3 className="text-lg font-medium text-slate-900 dark:text-white">Ready to Compare</h3>
               <p className="text-sm text-slate-500 max-w-sm">Select exactly two laboratory reports from your history to generate a longitudinal progress comparison.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ComparePage;
