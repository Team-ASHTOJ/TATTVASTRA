import { expect, test } from "@playwright/test";

test("Insight presents three deterministic investigation hypotheses", async ({
  page,
}) => {
  await page.route("**/api/control/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace(
      "/api/control/domain/",
      "",
    );
    if (path === "auth/me")
      return route.fulfill({ json: { id: "user-1", role: "ANALYST" } });
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

  await page.goto("/findings?report=ignored-while-analysis-is-static");
  await expect(
    page.getByRole("heading", { name: "Evidence-backed Findings" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Persisted finding" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Investigation Hypothesis Analysis" }),
  ).toBeVisible();
  await expect(page.getByText("AI ANALYSIS")).toBeVisible();
  await expect(page.locator(".hypothesis-card")).toHaveCount(3);
  await expect(
    page.getByRole("heading", {
      name: "Unauthorized Service Used as an Initial Foothold",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Container or Runtime Masquerading for Command Execution",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Reconnaissance Followed by Persistence Preparation",
    }),
  ).toBeVisible();
  await expect(page.getByText("NOT ESTABLISHED")).toHaveCount(0);
  await expect(page.getByText("Retry Analysis")).toHaveCount(0);
});
