/**
 * Sprint 2 acceptance: one program, genuine Linux and Windows target output,
 * three real Rust endpoints, in-JOCKY-worker MEMORY/JIT and NATIVE/AOT
 * execution, truthful provenance, and a real job carried over TRUSTED_RELAY.
 *
 * Every fact asserted here comes from backend state or real artifact bytes.
 * Nothing is inferred from a hostname or a UI label, and no Windows runtime
 * success is claimed: this host cannot link or run a Windows binary.
 */
import { test, expect, type Page } from "@playwright/test";
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

const ORIGIN = "http://127.0.0.1:13000";
const SLOTS = [1, 2, 3] as const;
const HOSTNAMES = ["LOCAL-LINUX-01", "LOCAL-LINUX-02", "LOCAL-LINUX-03"];

type Row = Record<string, unknown>;
const obj = (value: unknown): Row =>
  value && typeof value === "object" ? (value as Row) : {};

/** One deterministic benign program, used for both target builds and hunts. */
const SOURCE = `// Sprint 2 acceptance program: bounded, benign system inventory.
hunt "sprint-2-execution" {
    targets { os windows | linux }
    capabilities { system.read }
    budget { cpu <= 10% memory <= 64MiB io <= 0B duration <= 15s }
    collect system as sys
}
`;

function api(page: Page) {
  const headers = { Origin: ORIGIN };
  const get = (path: string): Promise<unknown> =>
    page.request.get(`/api/control/domain/${path}`).then((r) => r.json());
  const list = async (path: string): Promise<Row[]> =>
    (await get(path)) as Row[];
  const post = async (path: string, data?: unknown): Promise<Row> => {
    const response = await page.request.post(`/api/control/domain/${path}`, {
      headers,
      data,
    });
    expect(response.ok(), `${path}: ${await response.text()}`).toBe(true);
    return obj(await response.json());
  };
  return { get, list, post };
}

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Organization UUID").fill(organization);
  await page.getByLabel("Username", { exact: true }).fill("admin");
  await page
    .getByLabel("Password", { exact: true })
    .fill(env.JOCKY_BOOTSTRAP_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
}

/** Reuse the enrolled identity of each slot; start only what is not running. */
async function ensureAgentsOnline(page: Page) {
  const { get, list, post } = api(page);
  for (const slot of SLOTS) {
    const status = obj(await get(`local-agent/status?slot=${slot}`));
    if (
      !["ONLINE", "STALE", "WAITING_FOR_HEARTBEAT"].includes(
        String(status.state),
      )
    ) {
      await post(`local-agent/start?slot=${slot}`);
    }
  }
  await expect
    .poll(
      async () => {
        const endpoints = await list("endpoints");
        return HOSTNAMES.filter((hostname) =>
          endpoints.some(
            (endpoint) =>
              endpoint.hostname === hostname && endpoint.status === "ONLINE",
          ),
        ).length;
      },
      { timeout: 120000, intervals: [2000] },
    )
    .toBe(3);
}

/** Drive the real wizard, then wait for every child job to reach a terminal state. */
async function startInvestigation(
  page: Page,
  compilation: string,
  mode: "memory" | "native",
  hostnames: string[],
) {
  const { list } = api(page);
  const before = (await list("hunts")).map((hunt) => String(hunt.id));
  await page.goto("/investigations?new=1");
  const wizard = page.getByRole("dialog", { name: "New Investigation" });
  await wizard
    .getByLabel("Investigation compilation")
    .selectOption(compilation);
  await wizard.getByRole("button", { name: "Next", exact: true }).click();
  for (const hostname of hostnames) {
    await wizard.getByRole("checkbox", { name: new RegExp(hostname) }).check();
  }
  await wizard.getByRole("button", { name: "Next", exact: true }).click();
  await wizard.getByLabel("Execution mode").selectOption(mode);
  await wizard.getByRole("button", { name: "Next", exact: true }).click();
  await wizard
    .getByRole("button", { name: "Start Investigation", exact: true })
    .click();
  // The wizard only hands over once `hunts/{id}/start` returns, and that call
  // dispatches and settles every job, so it is legitimately slow.
  await expect(
    page.getByRole("dialog", { name: "Investigation Detail" }),
  ).toBeVisible({ timeout: 180000 });

  let huntId = "";
  await expect
    .poll(
      async () => {
        const hunts = await list("hunts");
        const created = hunts.find((hunt) => !before.includes(String(hunt.id)));
        huntId = created ? String(created.id) : "";
        if (!huntId) return -1;
        const jobs = await list(`hunts/${huntId}/jobs`);
        if (!jobs.length) return -1;
        const settled = jobs.filter((job) =>
          ["SUCCESS", "FAILED", "INCOMPATIBLE"].includes(String(job.status)),
        );
        return settled.length === jobs.length ? settled.length : -1;
      },
      { timeout: 180000, intervals: [2000] },
    )
    .toBe(hostnames.length);
  return huntId;
}

test("sprint 2 execution acceptance across three endpoints, two targets and both transports", async ({
  page,
}) => {
  test.setTimeout(600000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });

  await signIn(page);
  const { list, post } = api(page);

  // ---- three distinct, real endpoints, each with an authoritative transport ----
  await ensureAgentsOnline(page);
  const endpoints = await list("endpoints");
  const agents = HOSTNAMES.map((hostname) => {
    const endpoint = endpoints.find((row) => row.hostname === hostname);
    expect(endpoint, `${hostname} missing`).toBeTruthy();
    return endpoint!;
  });
  expect(new Set(agents.map((endpoint) => endpoint.id)).size).toBe(3);
  for (const [index, endpoint] of agents.entries()) {
    expect(endpoint.simulation, HOSTNAMES[index]).toBe(false);
    expect(endpoint.status, HOSTNAMES[index]).toBe("ONLINE");
    expect(endpoint.target_os, HOSTNAMES[index]).toBe("linux");
    expect(endpoint.execution_modes, HOSTNAMES[index]).toEqual(
      expect.arrayContaining(["memory", "native"]),
    );
    expect(Date.parse(String(endpoint.last_seen))).toBeGreaterThan(0);
    expect(["DIRECT", "TRUSTED_RELAY"]).toContain(endpoint.transport_mode);
  }
  // Slot 2 is routed through the trusted relay by Compose; slots 1 and 3 are direct.
  expect(agents[1].transport_mode).toBe("TRUSTED_RELAY");
  expect(agents[0].transport_mode).toBe("DIRECT");
  expect(agents[2].transport_mode).toBe("DIRECT");
  // No Windows endpoint is claimed to be running: this fleet is Linux only.
  expect(
    endpoints.filter(
      (endpoint) =>
        endpoint.target_os === "windows" && endpoint.status === "ONLINE",
    ),
    "no Windows endpoint may report ONLINE without a real Windows host",
  ).toEqual([]);

  // ---- one program compiled for real Linux and Windows targets ----
  const run = Date.now().toString(36);
  const testCase = await post("cases", {
    simulation: false,
    title: `sprint-2 execution ${run}`,
    description: "Sprint 2 target and execution acceptance",
  });
  const script = await post("scripts", {
    case_id: testCase.id,
    name: `sprint-2-execution-${run}`,
    source: SOURCE,
  });
  await post(`scripts/${script.id}/versions`, { source: SOURCE });
  const compilation = await post(`scripts/${script.id}/compile`);
  expect(compilation.status).toBe("SUCCESS");

  const built = (await post(`compilations/${compilation.id}/target-builds`, {
    targets: ["linux-x86_64", "windows-x86_64"],
  })) as unknown as Row[];
  const byTarget = new Map(
    built.map((variant) => [
      String(obj(variant.manifest).target_triple),
      obj(variant.manifest),
    ]),
  );
  const contentHash = new Map(
    built.map((variant) => [
      String(obj(variant.manifest).target_triple),
      String(variant.content_hash),
    ]),
  );
  const linux = byTarget.get("x86_64-unknown-linux-gnu");
  const windows = byTarget.get("x86_64-pc-windows-msvc");
  expect(linux, "linux target object missing").toBeTruthy();
  expect(windows, "windows target object missing").toBeTruthy();
  // Same program, same semantic JIR; genuinely different machine output.
  expect(linux!.jir_hash).toBe(windows!.jir_hash);
  expect(linux!.llvm_ir_hash).not.toBe(windows!.llvm_ir_hash);
  expect(contentHash.get("x86_64-unknown-linux-gnu")).not.toBe(
    contentHash.get("x86_64-pc-windows-msvc"),
  );
  for (const variant of [linux!, windows!]) {
    expect(variant.artifact_format).toBe("llvm-object");
    expect(Number(variant.artifact_size_bytes)).toBeGreaterThan(512);
    expect(String(variant.llvm_version)).toMatch(/^\d+\./);
    // The stored object is exactly the compiler's object, under its reported hash.
    // Byte-level ELF/COFF magic is proven by the native ctest
    // `cross_target_objects_and_rejections`, which can read the real files.
    expect(contentHash.get(String(variant.target_triple))).toBe(
      variant.artifact_hash,
    );
    // Final linking needs a toolchain for that target, which this host lacks.
    expect(variant.link_status).toBe("ENVIRONMENT DEPENDENT");
  }
  // Distinct machine formats for one program are genuinely different sizes.
  expect(linux!.artifact_size_bytes).not.toBe(windows!.artifact_size_bytes);

  // ---- MEMORY: LLVM ORC JIT inside the JOCKY worker, on all three endpoints ----
  const memoryHunt = await startInvestigation(
    page,
    String(compilation.id),
    "memory",
    HOSTNAMES,
  );
  // The detail drawer stays open after start; it must show real provenance.
  const memoryDetail = page.getByRole("dialog", {
    name: "Investigation Detail",
  });
  await expect(memoryDetail).toContainText("LLVM_ORC_JIT", { timeout: 60000 });
  await expect(memoryDetail).toContainText("MEMORY / JIT");
  await expect(memoryDetail).toContainText("TRUSTED RELAY");
  await expect(memoryDetail).toContainText("DIRECT");

  const memoryJobs = await list(`hunts/${memoryHunt}/jobs`);
  expect(memoryJobs.length).toBe(3);
  const transportByEndpoint = new Map(
    agents.map((endpoint) => [String(endpoint.id), endpoint.transport_mode]),
  );
  for (const job of memoryJobs) {
    const envelope = obj(job.envelope);
    const progress = obj(job.progress);
    expect(job.status).toBe("SUCCESS");
    expect(obj(envelope.build_manifest).artifact_format).toBe("llvm-ir");
    expect(progress.execution_engine).toBe("LLVM_ORC_JIT");
    expect(Number(progress.worker_pid)).toBeGreaterThan(0);
    expect(Number(progress.execution_duration_ms)).toBeGreaterThan(0);
    const expected = transportByEndpoint.get(String(job.endpoint_id));
    expect(envelope.execution_mode).toBe("memory");
    expect(envelope.transport_mode).toBe(expected);
    expect(progress.transport_mode).toBe(expected);
  }
  // Both transports actually carried a job that produced observations.
  const relayed = memoryJobs.filter(
    (job) => obj(job.envelope).transport_mode === "TRUSTED_RELAY",
  );
  const direct = memoryJobs.filter(
    (job) => obj(job.envelope).transport_mode === "DIRECT",
  );
  expect(relayed.length).toBe(1);
  expect(direct.length).toBe(2);
  // One compiler-generated variant per endpoint, each with its own identity.
  expect(new Set(memoryJobs.map((job) => job.variant_id)).size).toBe(3);

  // ---- NATIVE: a real linked AOT executable on one endpoint ----
  const nativeHunt = await startInvestigation(
    page,
    String(compilation.id),
    "native",
    ["LOCAL-LINUX-01"],
  );
  const nativeJobs = await list(`hunts/${nativeHunt}/jobs`);
  const nativeDetail = page.getByRole("dialog", {
    name: "Investigation Detail",
  });
  await expect(nativeDetail).toContainText("NATIVE_AOT", { timeout: 60000 });
  await expect(nativeDetail).toContainText("NATIVE / AOT");

  expect(nativeJobs.length).toBe(1);
  const nativeEnvelope = obj(nativeJobs[0].envelope);
  const nativeProgress = obj(nativeJobs[0].progress);
  expect(nativeJobs[0].status).toBe("SUCCESS");
  expect(nativeEnvelope.execution_mode).toBe("native");
  expect(obj(nativeEnvelope.build_manifest).artifact_format).toBe(
    "native-worker",
  );
  expect(obj(nativeEnvelope.build_manifest).link_status).toBe("LINKED");
  expect(nativeProgress.execution_engine).toBe("NATIVE_AOT");
  expect(Number(nativeProgress.worker_pid)).toBeGreaterThan(0);
  expect(Number(nativeProgress.execution_duration_ms)).toBeGreaterThan(0);

  // ---- evidence, artifacts and manifests keep the execution provenance ----
  const allJobs = [...memoryJobs, ...nativeJobs];
  const jobIds = new Set(allJobs.map((job) => String(job.id)));
  const observations = await list(`observations?case_id=${testCase.id}`);
  const jobObservations = observations.filter((observation) =>
    jobIds.has(String(observation.job_id)),
  );
  expect(jobObservations.length).toBeGreaterThanOrEqual(4);
  for (const observation of jobObservations) {
    const document = obj(observation.document);
    expect(document.simulation).toBe(false);
    expect(String(document.integrity_hash)).toMatch(/^[0-9a-f]{64}$/);
  }

  const artifacts = await list("artifacts");
  const jobArtifacts = artifacts.filter((artifact) =>
    jobIds.has(String(artifact.job_id)),
  );
  expect(jobArtifacts.length).toBeGreaterThanOrEqual(4);
  for (const artifact of jobArtifacts) {
    expect(Number(artifact.size_bytes)).toBeGreaterThan(0);
    const verification = await post(`artifacts/${artifact.id}/verify`);
    expect(verification.available).toBe(true);
    expect(verification.integrity_valid).toBe(true);
    expect(verification.computed_hash).toBe(artifact.content_hash);
  }

  const jobManifests: Row[] = [];
  for (const job of allJobs) {
    const rows = await list(`manifests?job_id=${job.id}`);
    expect(rows.length, `no evidence manifest for ${String(job.id)}`).toBe(1);
    jobManifests.push(rows[0]);
  }
  for (const manifest of jobManifests) {
    const job = allJobs.find((candidate) => candidate.id === manifest.job_id)!;
    const progress = obj(job.progress);
    const document = obj(manifest.document);
    expect(manifest.signature_verified).toBe(true);
    expect(document.execution_engine).toBe(progress.execution_engine);
    expect(document.worker_pid).toBe(progress.worker_pid);
    expect(Number(document.execution_duration_ms)).toBeGreaterThan(0);
    expect(document.transport_mode).toBe(obj(job.envelope).transport_mode);
    const result = await post(`manifests/${manifest.id}/verify`);
    expect(result.signature_valid).toBe(true);
    expect(result.integrity_valid).toBe(true);
    expect(result.provenance_valid).toBe(true);
  }

  // ---- the relayed endpoint's evidence is genuinely relayed evidence ----
  const relayedManifest = jobManifests.find(
    (manifest) => manifest.job_id === relayed[0].id,
  )!;
  expect(obj(relayedManifest.document).transport_mode).toBe("TRUSTED_RELAY");
  // Endpoint identity lives in the signed document, not on the row, so this is
  // the identity the manifest signature actually covers.
  expect(obj(relayedManifest.document).endpoint_id).toBe(
    relayed[0].endpoint_id,
  );

  // ---- reopened UI still reports execution mode and transport truthfully ----
  await page.goto(`/investigations?id=${memoryHunt}`);
  const reopened = page.getByRole("dialog", { name: "Investigation Detail" });
  await expect(reopened).toContainText("LLVM_ORC_JIT", { timeout: 30000 });
  await expect(reopened).toContainText("MEMORY / JIT");
  await expect(reopened).toContainText("TRUSTED RELAY");
  await expect(reopened).toContainText("DIRECT");
  await expect(reopened).toContainText("SUCCESS");
  await page.reload();
  await expect(reopened).toContainText("LLVM_ORC_JIT");
  await page.goto(`/investigations?id=${nativeHunt}`);
  await expect(
    page.getByRole("dialog", { name: "Investigation Detail" }),
  ).toContainText("NATIVE_AOT");

  await page.goto("/endpoints");
  const agentRow = page.getByRole("row").filter({
    has: page.getByRole("button", { name: "LOCAL-LINUX-02", exact: true }),
  });
  await expect(agentRow).toContainText("TRUSTED RELAY");
  await expect(agentRow).toContainText("ONLINE");
  await expect(agentRow).toContainText("MEMORY / JIT");

  expect(errors).toEqual([]);
});
