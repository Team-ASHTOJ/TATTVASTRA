import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const env = Object.fromEntries(
  readFileSync(".env", "utf8")
    .split(/\r?\n/)
    .filter((line) => line.includes("=") && !line.startsWith("#"))
    .map((line) => [
      line.slice(0, line.indexOf("=")),
      line.slice(line.indexOf("=") + 1),
    ]),
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

test("one-click local Rust endpoint connects, survives refresh, reuses identity and restarts", async ({
  page,
}) => {
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  await page.goto("/login");
  await page.getByLabel("Organization UUID").fill(organization);
  await page.getByLabel("Username", { exact: true }).fill("admin");
  await page
    .getByLabel("Password", { exact: true })
    .fill(env.JOCKY_BOOTSTRAP_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  const post = (path: string) =>
    page.request.post(`/api/control/domain/${path}`, {
      headers: { Origin: "http://127.0.0.1:13000" },
    });
  const status = async () =>
    (await page.request.get("/api/control/domain/local-agent/status")).json();
  const before = await status();
  if (["ONLINE", "STALE", "WAITING_FOR_HEARTBEAT"].includes(before.state))
    expect((await post("local-agent/stop")).ok()).toBe(true);
  const artifacts = await (
    await page.request.get("/api/control/domain/artifacts")
  ).json();
  await page.goto("/endpoints");
  await page
    .getByRole("button", { name: "Connect Endpoint", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Endpoint Enrollment" });
  await expect(
    dialog.getByRole("button", { name: "Generate Enrollment", exact: true }),
  ).toBeVisible();
  await dialog
    .getByRole("button", { name: "Start Local Endpoint", exact: true })
    .click();
  await expect(
    dialog.getByText("Endpoint connected", { exact: true }),
  ).toBeVisible({ timeout: 45000 });
  const online = await status();
  expect(online.state).toBe("ONLINE");
  expect(online.endpoint.simulation).toBe(false);
  expect(online.endpoint.hostname).toBe("LOCAL-LINUX-01");
  expect(Date.parse(online.endpoint.last_seen)).toBeGreaterThanOrEqual(
    Date.parse(online.connected_at),
  );
  expect(online.endpoint.agent_version).toBeTruthy();
  await dialog.getByRole("button", { name: "Open Endpoint" }).click();
  await expect(
    page.getByRole("dialog", { name: "LOCAL-LINUX-01" }),
  ).toBeVisible();
  await page.reload();
  const row = page.getByRole("row").filter({
    has: page.getByRole("button", { name: "LOCAL-LINUX-01", exact: true }),
  });
  await expect(row).toContainText("ONLINE");
  await expect(row).toContainText("LOCAL");
  const endpoints = await (
    await page.request.get("/api/control/domain/endpoints")
  ).json();
  await page
    .getByRole("button", { name: "Connect Endpoint", exact: true })
    .click();
  await dialog
    .getByRole("button", { name: "Start Local Endpoint", exact: true })
    .click();
  await expect(
    dialog.getByText("Endpoint connected", { exact: true }),
  ).toBeVisible();
  const repeated = await status();
  expect(repeated.endpoint_id).toBe(online.endpoint_id);
  expect(repeated.enrollment_id).toBe(online.enrollment_id);
  expect(
    (await (await page.request.get("/api/control/domain/endpoints")).json())
      .length,
  ).toBe(endpoints.length);
  await dialog.getByRole("button", { name: "Stop Local Endpoint" }).click();
  await expect.poll(async () => (await status()).state).toBe("STOPPED");
  await dialog.getByRole("button", { name: "Close", exact: true }).click();
  await expect(row).toContainText(/STALE|OFFLINE/);
  if (test.info().project.name === "video-desktop") {
    await expect
      .poll(
        async () => {
          const rows = await (
            await page.request.get("/api/control/domain/endpoints")
          ).json();
          return rows.find(
            (endpoint: { id: string }) => endpoint.id === online.endpoint_id,
          ).status;
        },
        { timeout: 105000, intervals: [3000] },
      )
      .toBe("OFFLINE");
  }
  await page
    .getByRole("button", { name: "Connect Endpoint", exact: true })
    .click();
  await dialog
    .getByRole("button", { name: "Start Local Endpoint", exact: true })
    .click();
  await expect(
    dialog.getByText("Endpoint connected", { exact: true }),
  ).toBeVisible({ timeout: 45000 });
  const restarted = await status();
  expect(restarted.endpoint_id).toBe(online.endpoint_id);
  expect(restarted.enrollment_id).toBe(online.enrollment_id);
  const retained = await (
    await page.request.get("/api/control/domain/artifacts")
  ).json();
  for (const artifact of artifacts)
    expect(retained.some((a: { id: string }) => a.id === artifact.id)).toBe(
      true,
    );
  expect(errors).toEqual([]);
});
