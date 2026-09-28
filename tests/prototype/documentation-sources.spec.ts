import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { documentationExamples } from "../../apps/dashboard/src/lib/documentation";

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

test("documentation and Workbench sources pass the authoritative compiler", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByLabel("Organization UUID").fill(organization);
  await page.getByLabel("Username", { exact: true }).fill("admin");
  await page
    .getByLabel("Password", { exact: true })
    .fill(env.JOCKY_BOOTSTRAP_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);

  for (const example of documentationExamples) {
    const response = await page.request.post("/api/control/compilations", {
      headers: { Origin: "http://127.0.0.1:13000" },
      data: {
        simulation: false,
        source: example.source,
        command: "llvm",
        target: { os: "linux", arch: "aarch64" },
        execution_mode: "memory",
      },
    });
    expect(response.ok(), `${example.name}: ${await response.text()}`).toBe(
      true,
    );
  }
});
