import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: '/voice-chat/',
  build: {
    outDir: '../plugin-static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "http://localhost:8321",
      "/ws": {
        target: "ws://localhost:8321",
        ws: true,
      },
    },
  },
});
