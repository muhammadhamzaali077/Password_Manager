import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config — Constitution V requires the chat flow to work at the
 * 375 × 812 mobile viewport. The default `mobile` project below pins that
 * size; CI invokes it with `pnpm exec playwright test --project=mobile`.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "mobile",
      use: {
        ...devices["iPhone 13 mini"],
        viewport: { width: 375, height: 812 },
      },
    },
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
      },
    },
  ],
  webServer: {
    command: "pnpm dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
