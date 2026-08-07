
import { defineConfig, configDefaults } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";
import tailwindcss from '@tailwindcss/vite'

// use process.cwd() to avoid import.meta.url complexity
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(process.cwd(), "src"),
    },
  },
  server: {
    port: 3000,
    host: true, // needed for Docker
  },
  test: {
    globals: true, // so you can use describe/it/expect without imports
    environment: "jsdom", // so React can render
    setupFiles: ["./src/setupTests.ts"], // optional, for global setup
    exclude: [...configDefaults.exclude, "e2e/**"],
  },

})
