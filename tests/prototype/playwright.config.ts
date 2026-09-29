import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "hypothesis-analysis.spec.ts",
  reporter: "list",
  use: {
    ...devices["Desktop Chrome"],
    ...(process.platform === "win32" ? {} : { channel: "chrome" }),
    baseURL: "http://127.0.0.1:13000",
  },
});
