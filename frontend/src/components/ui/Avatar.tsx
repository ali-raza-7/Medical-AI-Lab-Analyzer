import { useState, type ImgHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

const AVATAR_COLORS = [
  "#14b8a6", "#f59e0b", "#ef4444", "#8b5cf6",
  "#06b6d4", "#f97316", "#84cc16", "#ec4899",
  "#6366f1", "#22c55e",
];

function hashColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return (name[0] || "?").toUpperCase();
}

const sizeClasses = {
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-12 w-12 text-base",
  xl: "h-16 w-16 text-lg",
};

interface AvatarProps extends Omit<ImgHTMLAttributes<HTMLImageElement>, "src" | "alt" | "onLoad" | "onError"> {
  src?: string;
  alt?: string;
  email?: string;
  name?: string;
  size?: keyof typeof sizeClasses;
}

export function Avatar({
  src,
  alt = "",
  email,
  name,
  size = "md",
  className,
  ...imgProps
}: AvatarProps) {
  const [status, setStatus] = useState<"loading" | "loaded" | "error">(
    src ? "loading" : "error",
  );

  const identifier = name || email || alt || "?";
  const bgColor = email ? hashColor(email) : "#14b8a6";
  const initials = name ? getInitials(name) : email ? getInitials(email) : "?";

  return (
    <div
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full",
        sizeClasses[size],
        className,
      )}
      aria-label={alt || name || email || "User avatar"}
      role="img"
    >
      {src && status !== "error" && (
        <img
          src={src}
          alt={alt || name || "Avatar"}
          onLoad={() => setStatus("loaded")}
          onError={() => setStatus("error")}
          className={cn(
            "h-full w-full rounded-full object-cover",
            status === "loading" && "opacity-0",
          )}
          {...imgProps}
        />
      )}

      <div
        className={cn(
          "absolute inset-0 flex items-center justify-center rounded-full font-bold text-white",
          status === "loaded" && "opacity-0 pointer-events-none",
        )}
        style={{ backgroundColor: bgColor }}
        aria-hidden
      >
        {initials}
      </div>
    </div>
  );
}
