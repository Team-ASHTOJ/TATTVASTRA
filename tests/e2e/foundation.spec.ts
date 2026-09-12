import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";

test("overview shows real availability without invented fleet metrics", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Command Center", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("API CONNECTED")).toBeVisible();
  await expect(
    page.getByText("REAL mode — endpoint execution is not available yet"),
  ).toBeVisible();
  await expect(page.getByLabel("Not available", { exact: true })).toHaveCount(
    4,
  );
});

test("coverage comes from API and preserves safe technique mappings", async ({
  page,
}) => {
  await page.goto("/architecture");
  await page.getByLabel("Filter requirements").fill("SAFE-01");
  await expect(
    page.getByText("EDR callback disabling requirement", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Controlled visibility-loss fixture simulator", {
      exact: true,
    }),
  ).toBeVisible();
});

test("verifier calls backend and detects changed evidence", async ({
  page,
}) => {
  const fixture = JSON.parse(
    await readFile("fixtures/evidence/simulated-observation.json", "utf8"),
  );
  await page.goto("/evidence");
  await page
    .getByLabel("Observation JSON (contract v1.0.0)")
    .fill(JSON.stringify(fixture));
  await page.getByRole("button", { name: "VERIFY INTEGRITY" }).click();
  await expect(
    page.getByRole("heading", { name: "Hash matches submitted observation" }),
  ).toBeVisible();
  await expect(
    page.getByText("SIMULATED / DEMO", { exact: true }),
  ).toBeVisible();
  fixture.data.hostname = "tampered-host";
  await page
    .getByLabel("Observation JSON (contract v1.0.0)")
    .fill(JSON.stringify(fixture));
  await page.getByRole("button", { name: "VERIFY INTEGRITY" }).click();
  await expect(
    page.getByRole("heading", { name: "Integrity mismatch" }),
  ).toBeVisible();
});

test("judge mode identifies incomplete execution and narrow screens do not overflow", async ({
  page,
}) => {
  await page.goto("/judge");
  await expect(page.getByText("NOT READY", { exact: true })).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflow).toBe(false);
});

test("unavailable API is an error with retry", async ({ page }) => {
  // Explicit transport-failure injection, not synthetic operational telemetry.
  await page.route("**/api/control/status", (route) => route.abort("failed"));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Control plane unavailable" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Retry connection" }),
  ).toBeVisible();
});
