import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy ALL API routes to the FastAPI backend
    proxy: {
      "/analyze": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/history": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/compare": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/login": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/signup": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/me": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/auth": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
