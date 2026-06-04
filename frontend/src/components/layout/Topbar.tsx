import { Activity, Coins } from "lucide-react";
import { useAuth } from "../../lib/AuthContext";

export function Topbar() {
  const { user } = useAuth();

  return (
    <div className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur-md dark:border-[#1e293b] dark:bg-[#020617]/80">
      <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between gap-4 px-4 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-[#14b8a6] text-white">
            <Activity className="h-4 w-4" />
          </div>
          <h1 className="text-sm font-semibold tracking-wide text-slate-900 uppercase dark:text-white">
            Medical AI Lab Analyzer
          </h1>
        </div>

        <div className="flex items-center gap-4">
          {user && (
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                <span className="font-medium">{user.email}</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-amber-50 border border-amber-100 dark:bg-amber-900/10 dark:border-amber-900/20">
                <Coins className="h-3.5 w-3.5 text-amber-500" />
                <span className="text-xs font-bold text-amber-600 dark:text-amber-500">{user.credits}</span>
                <button className="ml-1 text-[10px] font-extrabold text-amber-700 hover:underline dark:text-amber-400">BUY</button>
              </div>
            </div>
          )}
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-100 dark:bg-[#14b8a6]/10 dark:border-[#14b8a6]/20">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider dark:text-[#14b8a6]">System Active</span>
          </div>
        </div>
      </div>
    </div>
  );
}


