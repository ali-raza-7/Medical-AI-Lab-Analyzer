import { NavLink, useNavigate } from "react-router-dom";
import { 
  LayoutDashboard, 
  ChevronLeft,
  ChevronRight,
  Database,
  Sun,
  Moon,
  History,
  ArrowLeftRight,
  LogOut,
  LogIn,
  X,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { useTheme } from "../../lib/theme";
import { useAuth } from "../../lib/AuthContext";
import { Avatar } from "../ui/Avatar";

const items = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/history", icon: History, label: "History" },
  { to: "/compare", icon: ArrowLeftRight, label: "Compare" },
];

export function Sidebar({ 
  expanded, 
  setExpanded,
  mobileOpen,
  onMobileClose,
}: { 
  expanded: boolean; 
  setExpanded: (v: boolean) => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}) {
  const { theme, toggle } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <>
      <aside 
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex-col border-r border-slate-200 bg-white transition-all duration-300 ease-in-out dark:border-[#1e293b] dark:bg-[#0f172a]",
          "lg:flex",
          mobileOpen
            ? "flex w-64 shadow-2xl"
            : "hidden w-64",
          !mobileOpen && "lg:flex",
          expanded ? "lg:w-64" : "lg:w-20",
        )}
        role="navigation"
        aria-label="Main navigation"
      >
        <div className="flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#14b8a6] text-white shadow-lg shadow-[#14b8a6]/20">
              <Database className="h-5 w-5" />
            </div>
            {(expanded || mobileOpen) && (
              <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
                LAB<span className="text-[#14b8a6]">SYSTEM</span>
              </span>
            )}
          </div>
          <button
            onClick={onMobileClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-[#1e293b] dark:hover:text-white lg:hidden"
            aria-label="Close navigation menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="absolute -right-3 top-20 hidden lg:flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-400 shadow-sm transition-colors hover:text-[#14b8a6] dark:border-[#1e293b] dark:bg-[#0f172a] dark:text-[#94a3b8]"
          aria-label={expanded ? "Collapse sidebar" : "Expand sidebar"}
        >
          {expanded ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>

        <nav className="mt-8 flex flex-col gap-2 px-3" aria-label="Navigation links">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={() => onMobileClose()}
              className={({ isActive }) =>
                cn(
                  "group flex h-11 items-center gap-4 rounded-lg px-3 transition-all duration-200",
                  isActive 
                    ? "bg-[#14b8a6]/10 text-[#14b8a6]" 
                    : "text-slate-500 hover:bg-slate-50 hover:text-slate-900 dark:text-[#94a3b8] dark:hover:bg-[#1e293b] dark:hover:text-white",
                )
              }
              aria-label={`Navigate to ${item.label}`}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {(expanded || mobileOpen) && (
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
              !expanded && !mobileOpen && "lg:justify-center lg:px-0"
            )}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? <Sun className="h-5 w-5 shrink-0" /> : <Moon className="h-5 w-5 shrink-0" />}
            {(expanded || mobileOpen) && <span className="text-sm font-medium">{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>}
          </button>

          {user ? (
            <div className="flex flex-col gap-2">
              <div className={cn(
                "flex items-center gap-3 rounded-xl p-2 transition-all bg-slate-50 dark:bg-[#1e293b]/50",
                !expanded && !mobileOpen && "lg:justify-center lg:p-0"
              )}>
                <Avatar
                  src={user.picture}
                  email={user.email}
                  size="md"
                  alt={user.email}
                />
                {(expanded || mobileOpen) && (
                  <div className="flex flex-col overflow-hidden">
                    <span className="truncate text-sm font-semibold text-slate-900 dark:text-white">{user.email.split('@')[0]}</span>
                    <span className="truncate text-[11px] text-slate-500 dark:text-[#64748b]">{user.credits} Credits</span>
                  </div>
                )}
              </div>
              <button
                onClick={() => { logout(); navigate('/login'); onMobileClose(); }}
                className={cn(
                  "flex h-10 items-center gap-4 rounded-lg px-3 text-red-500 transition-all hover:bg-red-50 dark:hover:bg-red-900/10",
                  !expanded && !mobileOpen && "lg:justify-center lg:px-0"
                )}
                aria-label="Log out of your account"
              >
                <LogOut className="h-5 w-5 shrink-0" />
                {(expanded || mobileOpen) && <span className="text-sm font-medium">Log Out</span>}
              </button>
            </div>
          ) : (
            <NavLink
              to="/login"
              onClick={() => onMobileClose()}
              className={cn(
                "flex h-10 items-center gap-4 rounded-lg px-3 text-emerald-500 transition-all hover:bg-emerald-50 dark:hover:bg-emerald-900/10",
                !expanded && !mobileOpen && "lg:justify-center lg:px-0"
              )}
              aria-label="Sign in to your account"
            >
              <LogIn className="h-5 w-5 shrink-0" />
              {(expanded || mobileOpen) && <span className="text-sm font-medium">Sign In</span>}
            </NavLink>
          )}
        </div>
      </aside>
    </>
  );
}


