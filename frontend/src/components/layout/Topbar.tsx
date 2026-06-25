import { Activity, Coins, Menu } from "lucide-react";
import { useAuth } from "../../lib/AuthContext";
import { Avatar } from "../ui/Avatar";

interface TopbarProps {
  onMenuToggle: () => void;
}

export function Topbar({ onMenuToggle }: TopbarProps) {
  const { user } = useAuth();

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur-md dark:border-[#1e293b] dark:bg-[#020617]/80">
      <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between gap-4 px-4 lg:px-8">
        <div className="flex items-center gap-3">
          <button
            onClick={onMenuToggle}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-[#94a3b8] dark:hover:bg-[#1e293b] dark:hover:text-white lg:hidden"
            aria-label="Open navigation menu"
          >
            <Menu className="h-5 w-5" />
          </button>
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
              <Avatar src={user.picture} email={user.email} size="sm" alt={user.email} />
              <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-amber-50 border border-amber-100 dark:bg-amber-900/10 dark:border-amber-900/20">
                <Coins className="h-3.5 w-3.5 text-amber-500" />
                <span className="text-xs font-bold text-amber-600 dark:text-amber-500">{user.credits}</span>
                <button className="ml-1 text-[10px] font-extrabold text-amber-700 hover:underline dark:text-amber-400" aria-label="Buy more credits">BUY</button>
              </div>
            </div>
          )}

        </div>
      </div>
    </header>
  );
}
