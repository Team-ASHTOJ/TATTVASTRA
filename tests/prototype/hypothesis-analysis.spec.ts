import { expect, test } from "@playwright/test";

test("Insight keeps findings distinct from READY, PENDING, and FAILED analysis", async ({
  page,
}) => {
  let status: "READY" | "PENDING" | "FAILED" = "READY";
  const analysis = {
    overall_assessment: "The evidence permits several explanations.",
    hypotheses: [1, 2, 3].map((rank) => ({
      rank,
      title: `Plausible explanation ${rank}`,
      support: "LOW",
      what_it_may_mean: "Observed state may be routine.",
      likely_intent: "Intent is not established.",
      success_assessment: {
        status: "NOT_ESTABLISHED",
        explanation: "The report does not establish success.",
      },
      observed_weaknesses: [],
      evidence: [],
      tattvastra_response: [],
      recommended_actions: ["Review persisted evidence"],
      uncertainty: "Visibility is limited.",
    })),
  };
  await page.route("**/api/control/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace(
      "/api/control/domain/",
      "",
    );
    if (path === "auth/me")
      return route.fulfill({ json: { id: "user-1", role: "ANALYST" } });
    if (path === "reports")
      return route.fulfill({
        json: [
          {
            id: "report-1",
            hunt_id: "hunt-1",
            created_at: "2026-09-29T00:00:00Z",
            analysis_status: status,
            analysis_model: "openai/gpt-oss-20b",
            analysis_generated_at:
              status === "READY" ? "2026-09-29T00:01:00Z" : null,
            analysis_error: status === "FAILED" ? "Rate limited" : null,
            analysis_document: status === "READY" ? analysis : null,
          },
        ],
      });
    if (path === "reports/report-1/analysis/retry") {
      status = "PENDING";
      return route.fulfill({
        status: 202,
        json: { id: "report-1", analysis_status: status },
      });
    }
    if (path === "cases")
      return route.fulfill({ json: [{ id: "case-1", title: "Case" }] });
    if (
      path === "findings" &&
      new URL(route.request().url()).searchParams.get("case_id") === "case-1"
    )
      return route.fulfill({
        json: [
          {
            id: "finding-1",
            case_id: "case-1",
            severity: "HIGH",
            title: "Persisted finding",
            rule_key: "RULE-1",
            observation_ids: [],
            created_at: "2026-09-29T00:00:00Z",
          },
        ],
      });
    return route.fulfill({ json: [] });
  });

  await page.goto("/findings?report=report-1");
  await expect(
    page.getByRole("heading", { name: "Evidence-backed Findings" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Persisted finding" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "AI-Assisted Hypothesis Analysis" }),
  ).toBeVisible();
  await expect(
    page.getByText("Generated from persisted investigation evidence.", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(page.locator(".hypothesis-card")).toHaveCount(3);

  status = "PENDING";
  await page.reload();
  await expect(page.getByText("Generating hypothesis analysis…")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Persisted finding" }),
  ).toBeVisible();

  status = "FAILED";
  await page.reload();
  await expect(page.getByText("Analysis unavailable. Rate limited")).toBeVisible();
  await page.getByRole("button", { name: "Retry Analysis" }).click();
  await expect(page.getByText("Generating hypothesis analysis…")).toBeVisible();
});

test("Insight repairs stale report URLs and retries the selected report", async ({
  page,
}) => {
  let availableIds = ["report-new", "report-old"];
  const retriedIds: string[] = [];
  await page.route("**/api/control/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace(
      "/api/control/domain/",
      "",
    );
    if (path === "auth/me")
      return route.fulfill({ json: { id: "user-1", role: "ANALYST" } });
    if (path === "reports")
      return route.fulfill({
        json: availableIds.map((id, index) => ({
          id,
          hunt_id: `hunt-${id}`,
          created_at: `2026-09-2${9 - index}T00:00:00Z`,
          analysis_status: "FAILED",
          analysis_error: "Structured response invalid",
          analysis_model: "openai/gpt-oss-20b",
          analysis_generated_at: null,
          analysis_document: null,
        })),
      });
    const retry = path.match(/^reports\/(report-[^/]+)\/analysis\/retry$/);
    if (retry) {
      retriedIds.push(retry[1]);
      if (retry[1] === "report-old") {
        availableIds = ["report-new"];
        return route.fulfill({ status: 404, json: { detail: "Resource not found" } });
      }
      return route.fulfill({ status: 202, json: { id: retry[1] } });
    }
    if (path === "cases") return route.fulfill({ json: [] });
    return route.fulfill({ json: [] });
  });

  await page.goto("/findings?report=stale-report");
  await expect(page).toHaveURL(/report=report-new/);
  await expect(page.getByLabel("Investigation report")).toHaveValue("report-new");
  await page.getByLabel("Investigation report").selectOption("report-old");
  await expect(page).toHaveURL(/report=report-old/);
  await expect(page.getByLabel("Investigation report")).toHaveValue("report-old");
  await page.getByRole("button", { name: "Retry Analysis" }).click();
  await expect(
    page.getByRole("alert").filter({
      hasText: "This investigation report is no longer available.",
    }),
  ).toBeVisible();
  await expect(page).toHaveURL(/report=report-new/);
  await expect(page.getByLabel("Investigation report")).toHaveValue("report-new");
  expect(retriedIds).toEqual(["report-old"]);
});
