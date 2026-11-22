import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const BACKEND = "http://127.0.0.1:8765";

// `npm run build` writes into ../dashboard/static, which the Python server serves.
// `npm run dev` proxies API and evidence requests to the running Python server.
export default defineConfig({
  plugins: [react()],
  build: { outDir: "../dashboard/static", emptyOutDir: true },
  server: { proxy: { "/api": BACKEND, "/evidence": BACKEND } },
});
