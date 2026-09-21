import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const entries = Object.fromEntries(
  readFileSync(".env", "utf8")
    .split("\n")
    .filter((line) => line.includes("=") && !line.startsWith("#"))
    .map((line) => {
      const split = line.indexOf("=");
      return [line.slice(0, split), line.slice(split + 1)];
    }),
);
const init = execFileSync(
  "docker",
  [
    "compose",
    "--env-file",
    ".env",
    "-f",
    "infra/docker/prototype.compose.yaml",
    "exec",
    "-T",
    "control-plane",
    "/app/.venv/bin/python",
    "-m",
    "jocky_control_plane.cli",
    "init",
  ],
  { encoding: "utf8" },
);
const organization = /Organization: ([0-9a-f-]+)/.exec(init)?.[1] ?? "";

test("recording walkthrough uses actual compiler and persisted simulated evidence", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByLabel("Organization UUID").fill(organization);
  await page.getByLabel("Username", { exact: true }).fill("admin");
  await page
    .getByLabel("Password", { exact: true })
    .fill(entries.JOCKY_BOOTSTRAP_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/cases$/);
  await page.goto("/judge");
  await expect(page.getByText("3", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Restore prepared scenario" }).click();
  await expect(
    page.getByText("Scenario ready.", { exact: false }),
  ).toBeVisible();
  await page.goto("/workbench");
  await page.getByRole("button", { name: "Load prepared demo source" }).click();
  await expect(page.getByLabel("JOCKY source", { exact: true })).toHaveValue(
    /sih-triage/,
  );
  await page.getByRole("button", { name: /Check/ }).click();
  await expect(page.locator(".compiler-output")).toContainText("source_hash");
  await page.goto("/compiler");
  await page.getByRole("button", { name: /LLVM IR/ }).click();
  await expect(page.locator(".compiler-output")).toContainText("jocky_rt_");
  await page.goto("/variants");
  await expect(page.getByText("VARIANT 1 / REAL BUILD")).toBeVisible();
  await expect(page.locator(".hash")).toHaveCount(3);
  await page.goto("/endpoints");
  await expect(page.getByRole("heading", { name: "WIN-01" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "WIN-02" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "UBUNTU-01" })).toBeVisible();
  await page.goto("/live");
  await expect(page.getByText("PARTIAL", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Connected — committed events only", { exact: false }),
  ).toBeVisible();
  await page.goto("/findings");
  await expect(
    page.getByRole("button", { name: /SIMULATED INPUT/ }),
  ).toHaveCount(1);
  await page.goto("/graph");
  await page
    .getByRole("button", { name: "Inspect Process", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Evidence & provenance" }),
  ).toBeVisible();
  await page.goto("/timeline");
  await page.getByLabel("Filter collector").fill("drivers");
  await expect(page.locator(".video-timeline li")).toHaveCount(2);
  await page.goto("/drivers");
  await expect(
    page.getByRole("heading", { name: "demo-legacy-driver.sys" }),
  ).toBeVisible();
  await page.goto("/evidence");
  await page
    .getByRole("button", { name: "Verify stored bytes" })
    .first()
    .click();
  await expect(page.getByLabel("Selected evidence")).toContainText(
    '"integrity_valid": true',
  );
  await page
    .getByRole("button", { name: "Verify manifest", exact: true })
    .first()
    .click();
  await expect(page.getByLabel("Selected evidence")).toContainText(
    '"signature_valid": true',
  );
  await page.goto("/performance");
  await page.getByRole("button", { name: "Run 3 measured samples" }).click();
  await expect(page.getByLabel("Selected evidence")).toContainText(
    '"status": "SUCCESS"',
  );
  await page.goto("/architecture");
  await page.getByLabel("Filter requirements").fill("SAFE-01");
  await expect(
    page.getByText("Controlled visibility-loss fixture simulator", {
      exact: true,
    }),
  ).toBeVisible();
  await page.goto("/");
  await page.reload();
  await expect(page.getByRole("heading", { name: "WIN-01" })).toBeVisible();
  await expect(
    page.getByText("DEMO / SIMULATED", { exact: true }).first(),
  ).toBeVisible();
});
