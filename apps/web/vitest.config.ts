import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
      "@intelligent-customer/ui": path.resolve(__dirname, "../../packages/ui/src"),
      "@intelligent-customer/fetch-client": path.resolve(
        __dirname,
        "../../packages/fetch-client/src"
      ),
    },
  },
});
