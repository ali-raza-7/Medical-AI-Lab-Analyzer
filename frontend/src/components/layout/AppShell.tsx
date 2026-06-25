import { useState, useCallback } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { cn } from "../../lib/utils";
import { ErrorBoundary } from "../ui/ErrorBoundary";

export function AppShell() {
  const [sidebarExpanded, setSidebarExpanded] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const closeMobileMenu = useCallback(() => setMobileMenuOpen(false), []);

  return (
    <div className="min-h-dvh bg-slate-50 transition-colors duration-300 dark:bg-[#020617]">
      <Sidebar
        expanded={sidebarExpanded}
        setExpanded={setSidebarExpanded}
        mobileOpen={mobileMenuOpen}
        onMobileClose={closeMobileMenu}
      />

      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={closeMobileMenu}
          aria-hidden="true"
        />
      )}

      <div
        className={cn(
          "transition-all duration-300 ease-in-out",
          sidebarExpanded ? "lg:pl-64" : "lg:pl-20",
        )}
      >
        <Topbar onMenuToggle={() => setMobileMenuOpen((v) => !v)} />
        <main className="mx-auto max-w-[1400px] px-4 py-8 lg:px-8">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
