import { defineConfig, devices } from "@playwright/test";

const apiCommand =
  process.platform === "win32"
    ? ".venv\\Scripts\\uvicorn.exe jocky_control_plane.app:app --host 127.0.0.1 --port 8100 --no-access-log"
    : ".venv/bin/uvicorn jocky_control_plane.app:app --host 127.0.0.1 --port 8100 --no-access-log";
const localBrowser = process.platform === "win32" ? { channel: "chrome" } : {};

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  retries: 0,
  reporter: "list",
  use: { baseURL: "http://127.0.0.1:3100", trace: "retain-on-failure" },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], ...localBrowser },
    },
    {
      name: "mobile",
      use: {
        ...devices["iPhone 13"],
        defaultBrowserType: "chromium",
        ...localBrowser,
      },
    },
  ],
  webServer: [
    {
      command: apiCommand,
      url: "http://127.0.0.1:8100/health/live",
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: "npm run start --workspace @jocky/dashboard -- --port 3100",
      env: { JOCKY_API_URL: "http://127.0.0.1:8100" },
      url: "http://127.0.0.1:3100",
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
