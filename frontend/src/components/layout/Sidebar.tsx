import { NavLink, useNavigate } from "react-router-dom";
import { 
  LayoutDashboard, 
  User as UserIcon,
  ChevronLeft,
  ChevronRight,
  Database,
  Sun,
  Moon,
  History,
  ArrowLeftRight,
  LogOut,
  LogIn
} from "lucide-react";
import { cn } from "../../lib/utils";
import { useTheme } from "../../lib/theme";
import { useAuth } from "../../lib/AuthContext";

const items = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/history", icon: History, label: "History" },
  { to: "/compare", icon: ArrowLeftRight, label: "Compare" },
];

export function Sidebar({ 
  expanded, 
  setExpanded 
}: { 
  expanded: boolean; 
  setExpanded: (v: boolean) => void 
}) {
  const { theme, toggle } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <aside 
      className={cn(
        "fixed inset-y-0 left-0 z-40 hidden border-r border-slate-200 bg-white transition-all duration-300 ease-in-out dark:border-[#1e293b] dark:bg-[#0f172a] lg:flex lg:flex-col",
        expanded ? "w-64" : "w-20"
      )}
    >
      <div className="flex h-16 items-center px-4">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#14b8a6] text-white shadow-lg shadow-[#14b8a6]/20">
            <Database className="h-5 w-5" />
          </div>
          {expanded && (
            <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
              LAB<span className="text-[#14b8a6]">SYSTEM</span>
            </span>
          )}
        </div>
      </div>

      <div className="absolute -right-3 top-20">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-400 hover:text-[#14b8a6] shadow-sm transition-colors dark:border-[#1e293b] dark:bg-[#0f172a] dark:text-[#94a3b8]"
        >
          {expanded ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>
      </div>

      <nav className="mt-8 flex flex-col gap-2 px-3">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "group flex h-11 items-center gap-4 rounded-lg px-3 transition-all duration-200",
                isActive 
                  ? "bg-[#14b8a6]/10 text-[#14b8a6]" 
                  : "text-slate-500 hover:bg-slate-50 hover:text-slate-900 dark:text-[#94a3b8] dark:hover:bg-[#1e293b] dark:hover:text-white"
              )
            }
          >
            <item.icon className="h-5 w-5 shrink-0" />
            {expanded && (
              <span className="text-sm font-medium transition-opacity duration-300">
                {item.label}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto flex flex-col gap-4 border-t border-slate-200 p-4 dark:border-[#1e293b]">
        <button
          onClick={toggle}
          className={cn(
            "flex h-10 items-center gap-4 rounded-lg px-3 text-slate-500 transition-all hover:bg-slate-50 hover:text-slate-900 dark:text-[#94a3b8] dark:hover:bg-[#1e293b] dark:hover:text-white",
            !expanded && "justify-center px-0"
          )}
          title="Toggle Theme"
        >
          {theme === "dark" ? <Sun className="h-5 w-5 shrink-0" /> : <Moon className="h-5 w-5 shrink-0" />}
          {expanded && <span className="text-sm font-medium">{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>}
        </button>

        {user ? (
          <div className="flex flex-col gap-2">
            <div className={cn(
              "flex items-center gap-3 rounded-xl p-2 transition-all bg-slate-50 dark:bg-[#1e293b]/50",
              !expanded && "justify-center p-0"
            )}>
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-emerald-500 text-white shadow-lg shadow-emerald-500/20">
                <UserIcon className="h-5 w-5" />
              </div>
              {expanded && (
                <div className="flex flex-col overflow-hidden">
                  <span className="truncate text-sm font-semibold text-slate-900 dark:text-white">{user.email.split('@')[0]}</span>
                  <span className="truncate text-[11px] text-slate-500 dark:text-[#64748b]">{user.credits} Credits</span>
                </div>
              )}
            </div>
            <button
              onClick={() => { logout(); navigate('/login'); }}
              className={cn(
                "flex h-10 items-center gap-4 rounded-lg px-3 text-red-500 transition-all hover:bg-red-50 dark:hover:bg-red-900/10",
                !expanded && "justify-center px-0"
              )}
            >
              <LogOut className="h-5 w-5 shrink-0" />
              {expanded && <span className="text-sm font-medium">Log Out</span>}
            </button>
          </div>
        ) : (
          <NavLink
            to="/login"
            className={cn(
              "flex h-10 items-center gap-4 rounded-lg px-3 text-emerald-500 transition-all hover:bg-emerald-50 dark:hover:bg-emerald-900/10",
              !expanded && "justify-center px-0"
            )}
          >
            <LogIn className="h-5 w-5 shrink-0" />
            {expanded && <span className="text-sm font-medium">Sign In</span>}
          </NavLink>
        )}
      </div>
    </aside>
  );
}


