import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
const env = Object.fromEntries(
  readFileSync(".env", "utf8")
    .split(/\r?\n/)
    .filter((l) => l.includes("=") && !l.startsWith("#"))
    .map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1)]),
);
const organization =
  /Organization: ([0-9a-f-]+)/.exec(
    execFileSync(
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
    ),
  )?.[1] ?? "";
test("Build Forge delivers three real structurally distinct fixture-verified objects", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  const post = (path: string, data?: unknown) =>
    page.request.post(`/api/control/domain/${path}`, {
      headers: { Origin: "http://127.0.0.1:13000" },
      ...(data ? { data } : {}),
    });
  const get = async (path: string) =>
    (await page.request.get(`/api/control/domain/${path}`)).json();
  await page.goto("/login");
  await page.getByLabel("Organization UUID").fill(organization);
  await page.getByLabel("Username", { exact: true }).fill("admin");
  await page
    .getByLabel("Password", { exact: true })
    .fill(env.JOCKY_BOOTSTRAP_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/workbench");
  await page.getByText("Load Example", { exact: true }).click();
  await page
    .getByRole("button", { name: "Combined Investigation", exact: true })
    .click();
  await page.getByRole("button", { name: "CHECK", exact: true }).click();
  await expect(page.getByLabel("Compiler output")).toContainText("source_hash");
  await page.getByRole("button", { name: "COMPILE", exact: true }).click();
  await expect(
    page.getByText("Compilation complete", { exact: false }),
  ).toBeVisible({ timeout: 30000 });
  const compilation = await page.evaluate(() =>
    sessionStorage.getItem("jocky-compilation"),
  );
  await page.goto(`/forge?compilation=${compilation}`);
  await expect(
    page.getByRole("heading", { name: "Build Forge", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Build compilation").selectOption(compilation!);
  await page.getByLabel("Build seed").fill("fedcba9876543210");
  await page
    .getByRole("button", { name: "BUILD 3 VARIANTS", exact: true })
    .click();
  await expect(
    page.getByText("3 real objects published", { exact: false }),
  ).toBeVisible({ timeout: 45000 });
  const runs = await get("build-runs");
  const run = runs
    .filter((r: { compilation_id: string }) => r.compilation_id === compilation)
    .at(-1);
  expect(run.status).toBe("READY");
  expect(
    run.stages.every((s: { status: string }) => s.status === "SUCCESS"),
  ).toBe(true);
  expect(run.results.equivalence_status).toBe("VERIFIED");
  expect(run.results.simulation).toBe(true);
  for (const field of [
    "artifact_hash",
    "llvm_ir_hash",
    "structural_fingerprint",
  ])
    expect(
      new Set(
        run.manifest.variants.map((v: Record<string, unknown>) => v[field]),
      ).size,
    ).toBe(3);
  expect(
    new Set(
      run.manifest.variants.map((v: Record<string, unknown>) => v.jir_hash),
    ).size,
  ).toBe(1);
  await page
    .getByRole("button", { name: "Verify build manifest & bytes" })
    .click();
  await expect(page.locator(".property-grid")).toContainText(
    "artifact integrity valid",
  );
  expect((await post(`build-runs/${run.id}/verify`)).ok()).toBe(true);
  expect((await (await post(`build-runs/${run.id}/verify`)).json()).valid).toBe(
    true,
  );
  await page.reload();
  await expect(
    page.getByText("3 real objects published", { exact: false }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Variant A", exact: true }).click();
  await page.getByRole("button", { name: "Compare variants" }).click();
  const comparison = page.getByRole("dialog", { name: "Variant comparison" });
  await expect(comparison).toContainText("VERIFIED");
  await expect(comparison).toContainText("DIFFERENT");
  await expect(comparison).toContainText("deterministic compiler fixture");
  await comparison.getByRole("button", { name: "Close", exact: true }).click();
  expect(
    await page
      .locator("main")
      .evaluate((e) => e.scrollWidth <= e.clientWidth + 1),
  ).toBe(true);
  await page.getByRole("button", { name: "Build 3 Verified Variants" }).click();
  await expect(page).toHaveURL(/\/forge\?compilation=/);
  await expect(
    page.getByText("3 real objects published", { exact: false }),
  ).toBeVisible({ timeout: 45000 });
  expect(errors).toEqual([]);
});
