import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { documentationExamples } from "../../apps/dashboard/src/lib/documentation";
import {
  aggregateConnections,
  sortedEndpoints,
} from "../../apps/dashboard/src/lib/product-data";
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
test("sorting and visual connection aggregation preserve identity and raw evidence", () => {
  expect(
    sortedEndpoints([
      { id: "fixture", status: "ONLINE", simulation: true },
      { id: "offline", status: "OFFLINE" },
      { id: "online", status: "ONLINE", simulation: false },
    ]).map((e) => e.id),
  ).toEqual(["online", "offline", "fixture"]);
  const observations = [1, 2, 3].map((i) => ({
    id: `o${i}`,
    endpoint_id: "endpoint",
    job_id: i === 3 ? "other-job" : "job",
    document: {
      data: {
        pid: 5,
        remote_address: "203.0.113.10",
        remote_port: 443,
        protocol: "tcp",
      },
    },
  }));
  const nodes = observations.map((o) => ({
    id: `connection:${o.id}`,
    type: "Connection",
    observation_id: o.id,
  }));
  const graph = aggregateConnections(nodes, [], observations);
  expect(graph.nodes.length).toBe(2);
  expect(graph.nodes[0]?.count).toBe(2);
  expect(observations.length).toBe(3);
});
test("coherent product connects three real agents and runs one investigation", async ({
  page,
}) => {
  test.setTimeout(180000);
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
  await expect(page.locator("header")).toContainText("admin · Administrator");
  await expect(page.locator("header")).not.toContainText("Operator sign in");
  await expect(
    page.getByRole("heading", { name: "Operation flow" }),
  ).toBeVisible();
  for (const state of await get("local-agents"))
    if (["ONLINE", "STALE", "WAITING_FOR_HEARTBEAT"].includes(state.state))
      expect((await post(`local-agent/stop?slot=${state.slot}`)).ok()).toBe(
        true,
      );
  await page.goto("/endpoints");
  await page
    .getByRole("button", { name: "Connect Endpoint", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Endpoint Enrollment" });
  await dialog
    .getByRole("button", { name: "Start Local Endpoint", exact: true })
    .click();
  await expect(
    dialog.getByText("Endpoint connected", { exact: true }),
  ).toBeVisible({ timeout: 45000 });
  for (let slot = 2; slot <= 3; slot++) {
    await dialog
      .getByRole("button", {
        name: "Start Another Local Endpoint",
        exact: true,
      })
      .click();
    await expect
      .poll(
        async () => {
          const states = await get("local-agents");
          return states.find((s: { slot: number }) => s.slot === slot).state;
        },
        { timeout: 45000 },
      )
      .toBe("ONLINE");
    await expect(dialog).toContainText(`LOCAL-LINUX-0${slot}`);
  }
  const states = await get("local-agents");
  expect(
    new Set(states.map((s: { endpoint_id: string }) => s.endpoint_id)).size,
  ).toBe(3);
  expect(
    states.every(
      (s: { endpoint: { simulation: boolean } }) =>
        s.endpoint.simulation === false,
    ),
  ).toBe(true);
  for (let slot = 1; slot <= 3; slot++) {
    const response = await post(`local-agent/start?slot=${slot}`);
    expect((await response.json()).endpoint_id).toBe(
      states[slot - 1].endpoint_id,
    );
  }
  await dialog.getByRole("button", { name: "Close", exact: true }).click();
  await page.reload();
  await expect(page.locator("tbody tr").first()).toContainText("LOCAL-LINUX-");
  await page.goto("/workbench");
  await page.getByText("Load Example", { exact: true }).click();
  await page
    .getByRole("button", { name: "Comprehensive Endpoint Sweep", exact: true })
    .click();
  await page.getByRole("button", { name: "CHECK", exact: true }).click();
  await expect(page.getByLabel("Compiler output")).toContainText("source_hash");
  await page.getByRole("button", { name: "COMPILE", exact: true }).click();
  await expect(
    page.getByText("Compilation complete", { exact: false }),
  ).toBeVisible({ timeout: 30000 });
  for (const tab of ["Tokens", "AST", "Typed JIR", "LLVM IR", "Execution Plan"])
    await page.getByRole("button", { name: tab, exact: true }).click();
  const comp = await page.evaluate(() =>
    sessionStorage.getItem("jocky-compilation"),
  );
  await page.goto("/compiler");
  await expect(page.locator("main")).not.toBeEmpty();
  await expect(page.locator(".compilation-list button.active")).toContainText(
    comp!,
  );
  await page.goto("/variants");
  await page.getByLabel("Variant compilation").selectOption(comp!);
  await page.getByRole("button", { name: "Build 3 Verified Variants" }).click();
  await expect(
    page.getByText("3 real objects published", { exact: false }),
  ).toBeVisible({
    timeout: 30000,
  });
  const generated = (await get("variants")).filter(
    (v: { compilation_id: string }) => v.compilation_id === comp,
  );
  expect(generated).toHaveLength(3);
  for (const variant of generated) {
    expect(variant.manifest.artifact_size_bytes).toBeGreaterThan(0);
    expect(typeof variant.manifest.profile.variant_ms).toBe("number");
    expect(typeof variant.manifest.profile.aot_ms).toBe("number");
  }
  await page.getByRole("link", { name: "Variant A", exact: true }).click();
  await page.getByRole("button", { name: "Compare variants" }).click();
  await expect(
    page.getByRole("dialog", { name: "Variant comparison" }),
  ).toContainText("VERIFIED");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Close", exact: true })
    .click();
  await page.getByRole("link", { name: "Compilation →", exact: true }).click();
  await expect(page.locator(".compilation-list button.active")).toContainText(
    comp!,
  );
  await page.goto("/investigations?new=1");
  const wizard = page.getByRole("dialog", { name: "New Investigation" });
  await wizard.getByLabel("Investigation compilation").selectOption(comp!);
  await wizard.getByRole("button", { name: "Next", exact: true }).click();
  for (let slot = 1; slot <= 3; slot++)
    await wizard
      .getByRole("checkbox", { name: new RegExp(`LOCAL-LINUX-0${slot}`) })
      .check();
  await wizard.getByRole("button", { name: "Next", exact: true }).click();
  await wizard.getByRole("button", { name: "Next", exact: true }).click();
  expect(
    await wizard.evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
  ).toBe(true);
  await wizard
    .getByRole("button", { name: "Start Investigation", exact: true })
    .click();
  const detail = page.getByRole("dialog", { name: "Investigation Detail" });
  await expect(detail).toContainText("SUCCESS", { timeout: 60000 });
  const hunts = await get("hunts"),
    hunt = hunts.find(
      (h: { compilation_id: string }) => h.compilation_id === comp,
    );
  await expect
    .poll(
      async () => {
        const jobs = await get(`hunts/${hunt.id}/jobs`);
        return jobs.filter((j: { status: string }) => j.status === "SUCCESS")
          .length;
      },
      { timeout: 60000 },
    )
    .toBe(3);
  const jobs = await get(`hunts/${hunt.id}/jobs`),
    artifacts = await get("artifacts");
  const artifact = artifacts.find((a: { job_id: string }) =>
    jobs.some((j: { id: string }) => j.id === a.job_id),
  );
  expect(artifact).toBeTruthy();
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
  await page.goto("/graph");
  await page
    .getByRole("button", { name: "Inspect Process", exact: true })
    .first()
    .click();
  await expect(page.getByRole("dialog", { name: "Node Detail" })).toBeVisible();
  await page.goto("/timeline");
  await expect(page.locator("main")).not.toBeEmpty();
  await page.goto("/evidence");
  const artifactRow = page.getByRole("row").filter({
    has: page.getByRole("link", {
      name: new RegExp(artifact.id.slice(0, 8)),
    }),
  });
  await artifactRow.getByRole("button", { name: "VERIFY INTEGRITY" }).click();
  const integrity = page.getByRole("dialog", { name: "Integrity result" });
  await expect(integrity.getByText("VALID", { exact: true })).toBeVisible();
  await integrity
    .getByRole("button", { name: "Verify related manifest" })
    .click();
  const manifest = page.getByRole("dialog", { name: "Manifest verification" });
  await expect(manifest).toContainText("VALID");
  await expect(manifest).toContainText("Manifest ID");
  await expect(manifest).not.toContainText("Recomputed SHA-256");
  await expect(manifest).not.toContainText("Artifact ID");
  await page.goto("/drivers");
  await expect(
    page.getByRole("heading", { name: "Linux module inventory" }),
  ).toBeVisible();
  await page.goto("/performance");
  await page.getByLabel("Benchmark compilation").selectOption(comp!);
  await page.getByRole("button", { name: "Measure Compiler" }).click();
  await expect(page.getByText("Benchmark complete ✓")).toBeVisible({
    timeout: 30000,
  });
  await expect(page.getByText("✓ New measurement")).toBeVisible();
  await page.goto("/language");
  await expect(
    page.getByRole("navigation", { name: "Documentation sections" }),
  ).toBeVisible();
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
    expect(response.ok(), example.name).toBe(true);
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
  ]) {
    const response = await page.goto(route);
    expect(response?.status(), route).toBeLessThan(400);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
      route,
    ).toBe(true);
  }
  expect(errors).toEqual([]);
});
