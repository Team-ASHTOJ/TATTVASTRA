import { expect, test, type Page } from "@playwright/test";

const fingerprint = "ENV-7A21C9";
const provenance = {
  job_id: "job-1",
  hunt_id: "hunt-1",
  variant_id: "variant-00000001",
  endpoint_id: "endpoint-1",
  endpoint_hostname: "LOCAL-LINUX-01",
  endpoint_platform: "linux",
  endpoint_architecture: "x86_64",
  transport_mode: "DIRECT",
  program: "comprehensive-endpoint-sweep",
  variant_seed: "000000000000002a",
  artifact_sha256: "a".repeat(64),
  jir_sha256: "b".repeat(64),
  llvm_ir_hash: "c".repeat(64),
  source_sha256: "d".repeat(64),
  structural_fingerprint: "FP-12",
  execution_mode: "memory",
  execution_status: "SUCCESS",
  runtime_ms: 184,
  cpu_percent: null,
  peak_memory_bytes: null,
  collector_counts: { processes: 18, connections: 96, drivers: 15 },
  simulation: false,
  simulation_label: null,
  measurement_source: "JOB_DERIVED",
};

function run(
  id: string,
  variant: string,
  overrides: Record<string, unknown> = {},
) {
  return {
    id,
    created_at: `2026-10-03T00:00:0${id.slice(-1)}Z`,
    variant_id: variant,
    endpoint_id: "endpoint-1",
    recorded_by: "fixture-operator",
    simulation: false,
    simulation_label: null,
    observations: {
      ...provenance,
      variant_id: variant,
      environment: "fixture policy",
      environment_fingerprint: fingerprint,
      security_product_label: "Fixture Product",
      security_product_version: "1.2.3",
      realtime_protection: "ENABLED",
      correctness: "PASS",
      alert_observed: "NO",
      ...overrides,
    },
  };
}

const candidate = {
  ...provenance,
  id: "job-1",
  created_at: "2026-10-03T00:00:00Z",
};

async function mockLab(
  page: Page,
  rows: ReturnType<typeof run>[],
  candidates: (typeof candidate)[] = [candidate],
  onPost?: (body: Record<string, unknown>) => void,
) {
  await page.route("**/api/control/domain/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    let body: unknown = [];
    if (path.endsWith("/compatibility-runs/candidates")) body = candidates;
    else if (path.endsWith("/compatibility-runs/job-preview"))
      body = provenance;
    else if (path.endsWith("/auth/me"))
      body = { id: "fixture-user", role: "ADMIN", username: "fixture" };
    else if (
      path.endsWith("/compatibility-runs") &&
      request.method() === "POST"
    ) {
      const submitted = request.postDataJSON() as Record<string, unknown>;
      onPost?.(submitted);
      body = run("9", String(submitted.variant_id), {
        ...submitted,
        ...provenance,
        correctness: "PASS",
        security_product_label: submitted.security_product_label,
        alert_observed: submitted.alert_observed,
        environment_fingerprint: "ENV-BASE01",
      });
      const index = rows.findIndex((row) => row.id === "9");
      if (index >= 0) rows[index] = body as ReturnType<typeof run>;
      else rows.push(body as ReturnType<typeof run>);
    } else if (path.endsWith("/compatibility-runs")) body = rows;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

test("recorded measurement renders the lab instrument and exact disclaimer", async ({
  page,
}) => {
  await mockLab(page, [run("1", "variant-a")]);
  await page.goto("/compatibility");
  await expect(
    page.getByRole("heading", { name: "Compatibility Lab" }),
  ).toBeVisible();
  await expect(page.getByLabel("Compatibility Signal")).toBeVisible();
  await expect(page.getByText("LOCAL-LINUX-01").first()).toBeVisible();
  await expect(
    page.getByText(
      "Compatibility measurement: no alert observed in this tested environment.",
    ),
  ).toBeVisible();
  await expect(
    page.getByText("ENVIRONMENT-SPECIFIC · NO UNIVERSAL BYPASS CLAIM"),
  ).toBeVisible();
});

test("analyze immediately records a job-derived baseline with click fallback", async ({
  page,
}) => {
  await mockLab(page, []);
  await page.goto("/compatibility");
  const job = page.getByRole("button", {
    name: /comprehensive-endpoint-sweep/,
  });
  const transfer = await page.evaluateHandle(() => new DataTransfer());
  await job.dispatchEvent("dragstart", { dataTransfer: transfer });
  await page.locator(".compat-bench").dispatchEvent("dragover", {
    dataTransfer: transfer,
  });
  await page.locator(".compat-bench").dispatchEvent("drop", {
    dataTransfer: transfer,
  });
  await expect(page.getByText("READY TO AUTO-RESOLVE")).toBeVisible();
  await job.click();
  await page.getByRole("button", { name: "Analyze Execution" }).click();
  await expect(page.locator(".compat-automation-counts")).toContainText(
    "12 AUTO-DERIVED FIELDS",
  );
  await expect(page.getByText("Artifact SHA-256")).toBeVisible();
  await expect(page.getByText(/processes/i).first()).toBeVisible();
  await expect(page.getByText("Peak RSS")).toBeVisible();
  await expect(page.getByText("MEASUREMENT RECORDED")).toBeVisible();
  await expect(page.locator(".compat-axis-list")).toContainText(
    "EXECUTION COMPATIBILITY",
  );
  await expect(page.locator(".compat-axis-list")).toContainText(
    "SEMANTIC CORRECTNESS",
  );
  await expect(page.locator(".compat-axis-list")).toContainText("NOT ASSESSED");
  await expect(page.locator(".compat-history-list > button")).toHaveCount(1);
  await job.click();
  await page.getByRole("button", { name: "Analyze Execution" }).click();
  await expect(page.locator(".compat-history-list > button")).toHaveCount(1);
});

test("security observation enriches the baseline without client-derived overrides", async ({
  page,
}) => {
  const rows: ReturnType<typeof run>[] = [];
  const submissions: Record<string, unknown>[] = [];
  await mockLab(page, rows, [candidate], (body) => {
    submissions.push(body);
  });
  await page.goto("/compatibility");
  await page
    .getByRole("button", { name: /comprehensive-endpoint-sweep/ })
    .click();
  await page.getByRole("button", { name: "Analyze Execution" }).click();
  await page.getByRole("button", { name: /Add Security Observation/ }).click();
  await page
    .getByRole("dialog")
    .getByLabel("Security Product")
    .fill("Recorded Product");
  await page
    .getByRole("dialog")
    .getByLabel("Exact Product Version")
    .fill("1.2.3");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Save Measurement" })
    .click();
  await expect
    .poll(() => submissions.at(-1)?.security_product_label)
    .toBe("Recorded Product");
  expect(submissions).toHaveLength(2);
  expect(submissions.at(-1)).not.toHaveProperty("artifact_sha256");
  expect(submissions.at(-1)).not.toHaveProperty("runtime_ms");
  expect(submissions.at(-1)).not.toHaveProperty("collector_counts");
  await expect(page.locator(".compat-history-list > button")).toHaveCount(1);
});

test("comparison includes only an identical server fingerprint", async ({
  page,
}) => {
  await mockLab(page, [
    run("1", "variant-a"),
    run("2", "variant-b", { structural_fingerprint: "FP-18" }),
    run("3", "variant-c", {
      environment_fingerprint: "ENV-OTHER1",
      structural_fingerprint: "FP-21",
    }),
  ]);
  await page.goto("/compatibility");
  await page.locator(".compat-history-list > button").nth(2).click();
  const comparison = page.locator(".compat-comparison");
  await expect(comparison).toBeVisible();
  await expect(comparison).toContainText("FP-18");
  await expect(comparison).not.toContainText("FP-21");
  await expect(comparison).not.toContainText("best");
});

test("empty lab is actionable and mobile layout has no horizontal overflow", async ({
  page,
}) => {
  await mockLab(page, [], []);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/compatibility");
  await expect(
    page.getByRole("heading", { name: "No compatibility measurements yet" }),
  ).toBeVisible();
  await expect(
    page.getByText("No completed executions are available yet."),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Open Investigations" }),
  ).toBeVisible();
  const overflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth >
      document.documentElement.clientWidth,
  );
  expect(overflow).toBe(false);
});

test("bench keeps its horizontal execution strip and contained instrument layout", async ({
  page,
}) => {
  const candidates = [0, 1, 2, 3].map((index) => ({
    ...candidate,
    job_id: `job-${index + 1}`,
    id: `job-${index + 1}`,
    endpoint_hostname: `LOCAL-LINUX-0${index + 1}`,
    program: `execution-${index + 1}`,
    variant_id: `variant-${index + 1}`,
  }));
  await mockLab(page, [run("1", "variant-a")], candidates);

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 1280, height: 800 },
    { width: 1024, height: 768 },
    { width: 768, height: 1024 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/compatibility");
    await expect(page.locator(".compat-candidate-strip")).toBeVisible();
    await expect(page.locator(".compat-chain li")).toHaveCount(5);
    await expect(page.locator(".compat-main-bench")).toBeVisible();

    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth,
    );
    expect(overflow, JSON.stringify(viewport)).toBe(false);

    const contained = await page
      .locator(".compat-candidate-strip")
      .evaluate((strip) => {
        const panel = strip.closest(".compat-bench-panel");
        if (!panel) return false;
        const stripBox = strip.getBoundingClientRect();
        const panelBox = panel.getBoundingClientRect();
        return (
          stripBox.left >= panelBox.left && stripBox.right <= panelBox.right
        );
      });
    expect(contained).toBe(true);
  }
});
