/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// base = nome do repositório: a demo publicada no GitHub Pages vive em /TradingBot/
export default defineConfig({
  base: "/TradingBot/",
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
