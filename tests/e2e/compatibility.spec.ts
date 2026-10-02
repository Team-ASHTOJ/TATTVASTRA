import { expect, test, type Page } from "@playwright/test";

const same = {
  compilation_id: "comp-1",
  jir_sha256: "a".repeat(64),
  environment: "fixture policy",
  os_name: "Fixture OS",
  os_version: "1",
  architecture: "x86_64",
  security_product_label: "Fixture Product",
  security_product_version: "1.2.3",
  realtime_protection: "ENABLED",
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
    endpoint_id: null,
    recorded_by: "fixture-operator",
    simulation: true,
    simulation_label: "TEST_FIXTURE",
    observations: {
      ...same,
      measurement_source: "OPERATOR_RECORDED",
      variant_seed: "1234567890abcdef",
      artifact_sha256: id.repeat(64).slice(0, 64),
      structural_fingerprint: `FP-${id}`,
      correctness: "PASS",
      execution_status: "SUCCESS",
      alert_observed: "NO",
      runtime_ms: 184,
      peak_memory_bytes: null,
      collector_counts: null,
      notes: "fixture only",
      ...overrides,
    },
  };
}

async function mock(page: Page, rows: ReturnType<typeof run>[]) {
  await page.route("**/api/control/domain/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const body = path.endsWith("/compatibility-runs")
      ? rows
      : path.endsWith("/auth/me")
        ? { id: "fixture-user", role: "VIEWER", username: "fixture" }
        : [];
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

test("selected compatibility run renders exact environment disclaimer and persisted data", async ({
  page,
}) => {
  await mock(page, [run("1", "variant-a")]);
  await page.goto("/compatibility");
  await expect(
    page.getByRole("heading", { name: "Compatibility Lab" }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Compatibility measurement: no alert observed in this tested environment.",
    ),
  ).toBeVisible();
  await expect(page.getByText("Fixture Product")).toBeVisible();
  await expect(page.getByText("DEMO/SIMULATED · TEST_FIXTURE")).toBeVisible();
  await expect(page.getByText("UNAVAILABLE").first()).toBeVisible();
});

test("comparison excludes different recorded security environments", async ({
  page,
}) => {
  await mock(page, [
    run("1", "variant-a"),
    run("2", "variant-b"),
    run("3", "variant-c", { security_product_version: "other-version" }),
  ]);
  await page.goto("/compatibility");
  await page.getByLabel("Selected compatibility run").selectOption("1");
  const table = page.locator(".compat-table");
  await expect(table.locator("thead th")).toHaveCount(3);
  await expect(table).not.toContainText("FP-3");
  await expect(table).toContainText("FP-2");
});

test("empty lab does not invent a compatibility measurement", async ({
  page,
}) => {
  await mock(page, []);
  await page.goto("/compatibility");
  await expect(
    page.getByRole("heading", {
      name: "No compatibility measurements recorded",
    }),
  ).toBeVisible();
  await expect(page.getByText("Fixture Product")).toHaveCount(0);
  await expect(
    page.getByText(
      "Compatibility measurement: no alert observed in this tested environment.",
    ),
  ).toHaveCount(0);
});

test("linked job previews persisted execution metrics as read-only", async ({
  page,
}) => {
  await page.route("**/api/control/domain/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const body = path.endsWith("/compatibility-runs/job-preview")
      ? {
          execution_status: "SUCCESS",
          runtime_ms: 184,
          cpu_percent: null,
          peak_memory_bytes: null,
          collector_counts: { processes: 2 },
          endpoint_id: "endpoint-1",
          endpoint_hostname: "fixture-endpoint",
          measurement_source: "JOB_DERIVED",
        }
      : path.endsWith("/compatibility-runs")
        ? []
        : path.endsWith("/auth/me")
          ? { id: "fixture-user", role: "ADMIN" }
          : path.endsWith("/variants")
            ? [{ id: "variant-1", simulation: true }]
            : path.endsWith("/endpoints")
              ? [{ id: "endpoint-1", hostname: "fixture-endpoint" }]
              : path.endsWith("/hunts")
                ? [{ id: "hunt-1" }]
                : path.endsWith("/hunts/hunt-1/jobs")
                  ? [
                      {
                        id: "job-1",
                        variant_id: "variant-1",
                        endpoint_id: "endpoint-1",
                        status: "SUCCESS",
                      },
                    ]
                  : [];
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
  await page.goto("/compatibility");
  await page.getByLabel("Compatibility variant").selectOption("variant-1");
  await page.getByLabel("Compatibility job").selectOption("job-1");
  await expect(
    page.getByText("JOB DERIVED — execution metrics are read-only"),
  ).toBeVisible();
  await expect(page.getByLabel("Job-derived execution status")).toHaveValue(
    "SUCCESS",
  );
  await expect(page.locator('input[name="runtime_ms"]')).toHaveValue("184");
  await expect(page.locator('input[name="runtime_ms"]')).toHaveAttribute(
    "readonly",
    "",
  );
  await expect(page.locator('input[name="peak_memory_bytes"]')).toHaveValue("");
});
