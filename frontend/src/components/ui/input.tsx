import * as React from "react";
import { cn } from "../../lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return (
      <input
        ref={ref}
        className={cn(
          "h-10 w-full rounded-2xl border border-slate-200/80 bg-white/70 px-3 text-sm shadow-sm outline-none transition-all placeholder:text-slate-400 focus:border-emerald-500/60 focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-800/70 dark:bg-slate-950/40 dark:placeholder:text-slate-500",
          className,
        )}
        {...props}
      />
    );
  },
);

