import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        clinical: {
          bg: {
            DEFAULT: "#f8fafc",
            dark: "#020617",
          },
          panel: {
            DEFAULT: "#ffffff",
            dark: "#0f172a",
          },
          card: {
            DEFAULT: "#ffffff",
            dark: "#111827",
          },
          accent: "#14b8a6",
          emerald: "#10b981",
          border: {
            DEFAULT: "#e2e8f0",
            dark: "#1e293b",
          },
          text: {
            primary: {
              DEFAULT: "#0f172a",
              dark: "#f1f5f9",
            },
            secondary: {
              DEFAULT: "#475569",
              dark: "#94a3b8",
            },
            muted: {
              DEFAULT: "#94a3b8",
              dark: "#64748b",
            },
          }
        }
      },
      borderRadius: {
        "xl": "12px",
        "2xl": "16px",
        "3xl": "24px",
      },
      boxShadow: {
        "clinical": "0 4px 20px -2px rgba(0, 0, 0, 0.05)",
        "clinical-dark": "0 4px 20px -2px rgba(0, 0, 0, 0.5)",
      }
    },
  },
  plugins: [],
} satisfies Config;

