import { test, expect } from "@playwright/test";
import {
  readFileSync,
  writeFileSync,
  mkdtempSync,
  chmodSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execFileSync } from "node:child_process";
import { languageExamples } from "../../apps/dashboard/src/lib/language-examples";

const compose = [
  "compose",
  "--env-file",
  ".env",
  "-f",
  "infra/docker/prototype.compose.yaml",
];
const entries = Object.fromEntries(
  readFileSync(".env", "utf8")
    .split(/\r?\n/)
    .filter((l) => l.includes("=") && !l.startsWith("#"))
    .map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1)]),
);
const init = execFileSync(
  "docker",
  [
    ...compose,
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

test("complete operator journey uses real enrollment, compiler, hunt and evidence", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  await page.goto("/login");
  await page.getByLabel("Organization UUID").fill(organization);
  await page.getByLabel("Username", { exact: true }).fill("admin");
  await page
    .getByLabel("Password", { exact: true })
    .fill(entries.JOCKY_BOOTSTRAP_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/endpoints");
  await page
    .getByRole("button", { name: "Connect Endpoint", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Endpoint Enrollment" });
  await dialog.getByRole("button", { name: "Create enrollment" }).click();
  await expect(
    dialog.getByText("WAITING FOR AGENT", { exact: true }),
  ).toBeVisible();
  const token = await dialog
    .getByLabel("One-time enrollment token")
    .inputValue();
  const directory = mkdtempSync(join(tmpdir(), "jocky-operator-"));
  chmodSync(directory, 0o777);
  writeFileSync(join(directory, "enrollment.token"), token, { mode: 0o600 });
  execFileSync(
    "docker",
    [
      ...compose,
      "cp",
      "control-plane:/app/.local/tls/ca.pem",
      join(directory, "ca.pem"),
    ],
    { stdio: "pipe" },
  );
  const name = `jocky-operator-${test.info().project.name}-${Date.now()}`;
  const base = [
    "run",
    "--rm",
    "--user",
    "0",
    "--network",
    "jocky-video_default",
    "--hostname",
    name,
    "-v",
    `${directory}:/endpoint`,
    "jocky-agent-runtime:phase4-current",
    "--state-dir",
    "/endpoint/state",
  ];
  execFileSync("docker", [...base, "init"], { stdio: "pipe" });
  execFileSync(
    "docker",
    [
      ...base,
      "enroll",
      "--enrollment-server",
      "https://agent-control:50052",
      "--server",
      "https://agent-control:50051",
      "--ca",
      "/endpoint/ca.pem",
      "--token-file",
      "/endpoint/enrollment.token",
      "--worker",
      "/usr/local/bin/jocky-worker",
    ],
    { stdio: "pipe" },
  );
  const container = execFileSync(
    "docker",
    [
      "run",
      "-d",
      "--rm",
      "--name",
      name,
      "--user",
      "0",
      "--network",
      "jocky-video_default",
      "--hostname",
      name,
      "-v",
      `${directory}:/endpoint`,
      "jocky-agent-runtime:phase4-current",
      "--state-dir",
      "/endpoint/state",
      "connect",
    ],
    { encoding: "utf8" },
  ).trim();
  try {
    await expect(
      dialog.getByText("ONLINE · Agent connected", { exact: true }),
    ).toBeVisible({ timeout: 30000 });
    await dialog.getByRole("button", { name: "Close", exact: true }).click();
    await page.getByRole("button", { name, exact: true }).click();
    await expect(page.getByRole("dialog", { name })).toBeVisible();
    await page.getByRole("button", { name: "Processes", exact: true }).click();
    await expect(
      page.getByText("No processes data has been collected", { exact: false }),
    ).toBeVisible();
    await page
      .getByRole("dialog", { name })
      .getByRole("button", { name: "Close", exact: true })
      .click();
    await page.goto("/workbench");
    await expect(page.getByLabel("JOCKY source")).toHaveValue("");
    await page.getByText("Load Example", { exact: true }).click();
    await page
      .getByRole("button", { name: "System Baseline", exact: true })
      .click();
    await page.getByRole("button", { name: "CHECK", exact: true }).click();
    await expect(page.getByLabel("Compiler output")).toContainText(
      "source_hash",
    );
    await page.getByRole("button", { name: "COMPILE", exact: true }).click();
    await expect(
      page.getByText("Compilation complete", { exact: false }),
    ).toBeVisible({ timeout: 30000 });
    for (const stage of [
      "Tokens",
      "AST",
      "Typed JIR",
      "LLVM IR",
      "Execution Plan",
    ]) {
      await page.getByRole("button", { name: stage, exact: true }).click();
      await expect(page.getByLabel("Compiler output")).not.toBeEmpty();
    }
    await page
      .getByRole("button", { name: "BUILD VARIANTS", exact: true })
      .click();
    await expect(page).toHaveURL(/\/variants$/);
    await expect(page.getByText("Variant A", { exact: true })).toBeVisible({
      timeout: 30000,
    });
    await page.getByRole("button", { name: "Compare variants" }).click();
    await expect(
      page.getByText("semantic equivalence", { exact: true }),
    ).toBeVisible();
    await page.goto("/investigations");
    await page
      .getByRole("button", { name: "New Investigation", exact: true })
      .click();
    const wizard = page.getByRole("dialog", { name: "New Investigation" });
    await wizard.getByRole("button", { name: "Next", exact: true }).click();
    await wizard.getByLabel(new RegExp(name)).check();
    await wizard.getByRole("button", { name: "Next", exact: true }).click();
    await wizard.getByRole("button", { name: "Next", exact: true }).click();
    await wizard
      .getByRole("button", { name: "Start Investigation", exact: true })
      .click();
    const detail = page.getByRole("dialog", { name: "Investigation Detail" });
    await expect(detail).toBeVisible({ timeout: 30000 });
    await expect(
      detail.getByText("SUCCESS", { exact: true }).first(),
    ).toBeVisible({ timeout: 60000 });
    await detail.getByRole("button", { name: "Close", exact: true }).click();
    await page.goto("/findings");
    await page
      .getByRole("button", {
        name: "Unsigned process with external connection",
        exact: true,
      })
      .first()
      .click();
    await expect(
      page.getByRole("dialog", { name: "Finding Detail" }),
    ).toContainText("Supporting observations");
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Close", exact: true })
      .click();
    await page.goto("/graph");
    await page
      .getByRole("button", { name: "Inspect Process", exact: true })
      .first()
      .click();
    await expect(
      page.getByRole("dialog", { name: "Node Detail" }),
    ).toBeVisible();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Close", exact: true })
      .click();
    await page.goto("/timeline");
    await page.getByLabel("Filter type").selectOption("drivers");
    const cases = (await (
      await page.request.get("/api/control/domain/cases")
    ).json()) as { id: string }[];
    const timelines = await Promise.all(
      cases.map(
        async (c) =>
          (
            await page.request.get(
              `/api/control/domain/timeline?case_id=${c.id}`,
            )
          ).json() as Promise<{ type: string }[]>,
      ),
    );
    await expect(page.locator(".forensic-timeline li")).toHaveCount(
      timelines.flat().filter((t) => t.type === "drivers").length,
    );
    await page.locator(".timeline-event").first().click();
    await expect(
      page.getByRole("dialog", { name: "Timeline Event" }),
    ).toBeVisible();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Close", exact: true })
      .click();
    await page.goto("/evidence");
    await page
      .getByRole("button", { name: "VERIFY INTEGRITY", exact: true })
      .first()
      .click();
    await expect(
      page.getByRole("heading", { name: "Integrity result" }),
    ).toBeVisible();
    await expect(page.getByText("VALID", { exact: true })).toBeVisible();
    await page.goto("/drivers");
    await expect(
      page
        .getByRole("button", { name: "demo-legacy-driver.sys", exact: true })
        .first(),
    ).toBeVisible();
    await page.goto("/performance");
    await page
      .getByRole("button", { name: "Measure Compiler", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Measure Compiler", exact: true }),
    ).toBeEnabled({ timeout: 30000 });
    await page.goto("/language");
    await page
      .getByRole("link", { name: "Open in Workbench", exact: true })
      .last()
      .click();
    await expect(page.getByLabel("JOCKY source")).toHaveValue(
      /combined-investigation/,
    );
    for (const example of languageExamples) {
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
      expect(response.ok(), example.name).toBe(true);
      expect((await response.json()).ir, example.name).toContain(
        "target triple",
      );
    }
    for (const route of [
      "/",
      "/endpoints",
      "/workbench",
      "/compiler",
      "/variants",
      "/investigations",
      "/findings",
      "/graph",
      "/timeline",
      "/evidence",
      "/drivers",
      "/performance",
      "/language",
      "/architecture",
    ]) {
      const response = await page.goto(route);
      expect(response?.status(), route).toBeLessThan(400);
      await expect(page.locator("main")).not.toBeEmpty();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
        route,
      ).toBe(true);
    }
    expect(errors).toEqual([]);
  } finally {
    execFileSync("docker", ["stop", container], { stdio: "pipe" });
    rmSync(directory, { recursive: true, force: true });
  }
});
