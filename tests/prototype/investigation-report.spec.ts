import { expect, test } from "@playwright/test";

const report = {
  report: { id: "report-1", hunt_id: "hunt-1", status: "SUCCESS" },
  artifact: {
    id: "artifact-report",
    content_hash: "a".repeat(64),
    size_bytes: 100,
  },
  download_url: "/api/artifacts/artifact-report/content",
  document: {
    schema_version: "1.0.0",
    report_identity: {
      report_id: "report-1",
      investigation_id: "hunt-1",
      case_id: "case-1",
      generated_at: "2026-09-29T00:00:00Z",
      generated_by: "analyst",
      report_artifact_hash: "a".repeat(64),
      schema_version: "1.0.0",
    },
    investigation: {
      id: "hunt-1",
      case_id: "case-1",
      case_title: "Focused report test",
      status: "SUCCESS",
      simulation: false,
    },
    executive_summary: {
      text: "This investigation completed with no persisted findings.",
      metrics: {
        endpoints: 1,
        successful_jobs: 1,
        jobs: 1,
        observations: 0,
        findings: 0,
        evidence_artifacts: 0,
        verified_manifests: 0,
      },
    },
    intent: {
      program: "focused-report",
      target_endpoint_ids: ["endpoint-1"],
      execution_mode: "memory",
      enforcement: "MONITORED",
      declared_capabilities: ["system.read"],
    },
    semantic_plan: {
      available: true,
      operations: [
        {
          operation: "collect",
          collector: "system",
          description: "Collect system metadata",
        },
      ],
    },
    endpoint_results: [
      {
        job_id: "job-1",
        endpoint_id: "endpoint-1",
        hostname: "LOCAL-LINUX-01",
        platform: "linux",
        architecture: "x86_64",
        status: "SUCCESS",
        execution_mode: "memory",
        observation_count: 0,
        artifact_count: 0,
      },
    ],
    findings: [],
    observation_summary: [],
    timeline: [],
    compiler_provenance: {
      compilation_id: "compilation-1",
      executions: [{ job_id: "job-1", execution_mode: "memory" }],
    },
    evidence_integrity: {
      manifests: [],
      artifacts: [],
      observation_integrity_hashes: [],
      audit_chain_verification: { integrity_valid: false },
    },
    source: {
      version: 1,
      source_hash: "b".repeat(64),
      text: 'hunt "focused-report" {}',
    },
    limitations: ["Runtime metadata is unavailable for this historical job."],
    simulation: false,
    simulation_label: null,
  },
};

test("Investigation Detail opens the dedicated forensic report", async ({
  page,
}) => {
  await page.route("**/api/control/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace(
      "/api/control/domain/",
      "",
    );
    if (path === "auth/me")
      return route.fulfill({ json: { id: "user-1", role: "ADMIN" } });
    if (path === "cases")
      return route.fulfill({
        json: [
          {
            id: "case-1",
            title: "Focused report test",
            simulation: false,
          },
        ],
      });
    if (path === "endpoints")
      return route.fulfill({
        json: [
          {
            id: "endpoint-1",
            hostname: "LOCAL-LINUX-01",
            target_os: "linux",
            target_arch: "x86_64",
            simulation: false,
            status: "ONLINE",
          },
        ],
      });
    if (path === "hunts")
      return route.fulfill({
        json: [
          {
            id: "hunt-1",
            case_id: "case-1",
            compilation_id: "compilation-1",
            endpoint_ids: ["endpoint-1"],
            status: "SUCCESS",
            simulation: false,
          },
        ],
      });
    if (path === "compilations")
      return route.fulfill({
        json: [
          {
            id: "compilation-1",
            script_version_id: "version-1",
            status: "SUCCESS",
          },
        ],
      });
    if (path === "scripts")
      return route.fulfill({
        json: [{ id: "script-1", case_id: "case-1", name: "focused-report" }],
      });
    if (path === "scripts/script-1/versions")
      return route.fulfill({
        json: [{ id: "version-1", script_id: "script-1", version: 1 }],
      });
    if (path === "hunts/hunt-1/jobs")
      return route.fulfill({
        json: [
          {
            id: "job-1",
            hunt_id: "hunt-1",
            endpoint_id: "endpoint-1",
            status: "SUCCESS",
          },
        ],
      });
    if (path === "hunts/hunt-1/report")
      return route.fulfill({
        status: route.request().method() === "POST" ? 201 : 200,
        json: report,
      });
    if (path === "local-agents") return route.fulfill({ json: [] });
    if (path === "events")
      return route.fulfill({ contentType: "text/event-stream", body: "" });
    return route.fulfill({ json: [] });
  });

  await page.goto("/investigations?id=hunt-1");
  const detail = page.getByRole("dialog", { name: "Investigation Detail" });
  await expect(detail.getByRole("heading", { name: "Outcome" })).toBeVisible();
  await detail
    .getByRole("button", { name: "Open Investigation Report" })
    .click();
  await expect(page).toHaveURL(/\/investigations\/hunt-1\/report$/);
  await expect(
    page.getByRole("heading", { name: "Forensic Investigation Report" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Findings" })).toBeVisible();
  await expect(page.getByText("does not establish the absence")).toBeVisible();
  await expect(page.getByText('hunt "focused-report" {}')).toBeVisible();
  await expect(page.getByText("Not reported")).toHaveCount(0);

  await page.evaluate(() => {
    window.print = () =>
      document.body.setAttribute("data-print-called", "true");
  });
  await page.getByRole("button", { name: "Print / Save PDF" }).click();
  await expect(page.locator("body")).toHaveAttribute(
    "data-print-called",
    "true",
  );
});
