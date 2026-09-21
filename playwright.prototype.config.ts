import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/prototype",
  workers: 1,
  timeout: 120_000,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:13000",
    trace: "off",
    screenshot: "off",
    ...(process.platform === "win32" ? { channel: "chrome" } : {}),
  },
  projects: [
    { name: "video-desktop", use: { ...devices["Desktop Chrome"] } },
    {
      name: "video-mobile",
      use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" },
    },
  ],
});
