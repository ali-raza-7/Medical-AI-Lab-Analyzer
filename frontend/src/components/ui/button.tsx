import * as React from "react";
import { cn } from "../../lib/utils";

type Variant = "default" | "secondary" | "ghost" | "outline" | "clinical";
type Size = "sm" | "md" | "lg" | "icon";

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
};

const variants: Record<Variant, string> = {
  default:
    "bg-slate-900 text-white hover:bg-slate-800 dark:bg-[#14b8a6] dark:text-white dark:hover:bg-[#0d9488]",
  secondary:
    "bg-slate-100 text-slate-900 hover:bg-slate-200 dark:bg-[#1e293b] dark:text-white dark:hover:bg-[#334155]",
  ghost:
    "bg-transparent hover:bg-slate-100 text-slate-900 dark:text-[#94a3b8] dark:hover:text-white dark:hover:bg-[#1e293b]",
  outline:
    "bg-transparent ring-1 ring-slate-200 hover:bg-slate-50 text-slate-900 dark:text-white dark:ring-[#1e293b] dark:hover:bg-[#1e293b]",
  clinical:
    "bg-[#14b8a6] text-white shadow-lg shadow-[#14b8a6]/20 hover:bg-[#0d9488] hover:-translate-y-0.5 transition-all",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-3 text-[11px] font-bold uppercase tracking-wider rounded-md",
  md: "h-10 px-4 text-xs font-bold uppercase tracking-wider rounded-lg",
  lg: "h-12 px-6 text-sm font-bold uppercase tracking-wider rounded-xl",
  icon: "h-9 w-9 rounded-lg",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "default", size = "md", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950 disabled:pointer-events-none disabled:opacity-50 dark:focus-visible:ring-slate-300",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  );
});
