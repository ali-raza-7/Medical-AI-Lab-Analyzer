import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { cn } from "../../lib/utils";

export function AppShell() {
  const [sidebarExpanded, setSidebarExpanded] = useState(true);

  return (
    <div className="min-h-dvh bg-slate-50 transition-colors duration-300 dark:bg-[#020617]">
      <Sidebar expanded={sidebarExpanded} setExpanded={setSidebarExpanded} />
      <div 
        className={cn(
          "transition-all duration-300 ease-in-out",
          sidebarExpanded ? "lg:pl-64" : "lg:pl-20"
        )}
      >
        <Topbar />
        <main className="mx-auto max-w-[1400px] px-4 py-8 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

