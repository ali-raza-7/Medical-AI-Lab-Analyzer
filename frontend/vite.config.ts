import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/analyze": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/history": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        bypass: (req) => {
          if (req.method === "GET" && req.headers?.["x-requested-with"] !== "XMLHttpRequest") {
            return "/index.html";
          }
        },
      },
      "/compare": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        bypass: (req) => { if (req.method === "GET") return "/index.html"; },
      },
      "/login": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        bypass: (req) => { if (req.method === "GET") return "/index.html"; },
      },
      "/signup": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        bypass: (req) => { if (req.method === "GET") return "/index.html"; },
      },
      "/me": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/refresh": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/logout": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/auth": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/forgot-password": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/reset-password": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        bypass: (req) => { if (req.method === "GET") return "/index.html"; },
      },
      "/verify-email": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/status": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/worker/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
