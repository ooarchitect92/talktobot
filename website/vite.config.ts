import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  ssr: { noExternal: true },
  build: { rollupOptions: { output: { entryFileNames: chunk => chunk.name === "entry-server" ? "entry-server.mjs" : "assets/[name]-[hash].js" } } },
  server: {
    port: 3300,
    strictPort: true,
    proxy: {
      "/api": {
        target: process.env.WEBSITE_API_TARGET || "http://127.0.0.1:8200",
        changeOrigin: true,
      },
    },
  },
});
