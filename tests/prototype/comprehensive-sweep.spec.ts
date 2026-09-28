import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { languageExamples } from "../../apps/dashboard/src/lib/language-examples";

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

test("comprehensive endpoint sweep produces real observations", async ({
  page,
}) => {
  test.setTimeout(240000);
  await page.goto("/login");
  await page.getByLabel("Organization UUID").fill(organization);
  await page.getByLabel("Username", { exact: true }).fill("admin");
  await page
    .getByLabel("Password", { exact: true })
    .fill(env.JOCKY_BOOTSTRAP_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);

  const get = async (path: string) =>
    (await page.request.get(`/api/control/domain/${path}`)).json();
  const post = (path: string, data?: unknown) =>
    page.request.post(`/api/control/domain/${path}`, {
      headers: { Origin: "http://127.0.0.1:13000" },
      ...(data ? { data } : {}),
    });
  const status = await get("local-agent/status?slot=1");
  if (!["ONLINE", "STALE", "WAITING_FOR_HEARTBEAT"].includes(status.state))
    expect((await post("local-agent/start?slot=1")).ok()).toBe(true);
  await expect
    .poll(
      async () =>
        (await get("endpoints")).find(
          (endpoint: {
            hostname: string;
            status: string;
            simulation: boolean;
          }) =>
            endpoint.hostname === "LOCAL-LINUX-01" &&
            endpoint.status === "ONLINE" &&
            endpoint.simulation === false,
        ),
      { timeout: 90000, intervals: [2000] },
    )
    .toBeTruthy();

  const source = languageExamples.find(
    (example) => example.name === "Comprehensive Endpoint Sweep",
  )!.source;
  const cases = await get("cases");
  const caseRecord =
    cases.find(
      (item: { simulation: boolean; title: string }) =>
        !item.simulation && item.title === "Operator Programs",
    ) ??
    (await (
      await post("cases", {
        simulation: false,
        title: "Operator Programs",
        description: "Authorized operator programs",
      })
    ).json());
  const script = await (
    await post("scripts", {
      case_id: caseRecord.id,
      name: "comprehensive-endpoint-sweep",
      source,
    })
  ).json();
  const compilation = await (await post(`scripts/${script.id}/compile`)).json();
  expect(compilation.status).toBe("SUCCESS");

  const huntsBefore = (await get("hunts")).map(
    (hunt: { id: string }) => hunt.id,
  );
  await page.goto("/investigations?new=1");
  const wizard = page.getByRole("dialog", { name: "New Investigation" });
  await wizard
    .getByLabel("Investigation compilation")
    .selectOption(compilation.id);
  await wizard.getByRole("button", { name: "Next", exact: true }).click();
  await wizard.getByRole("checkbox", { name: /LOCAL-LINUX-01/ }).check();
  await wizard.getByRole("button", { name: "Next", exact: true }).click();
  await wizard.getByLabel("Execution mode").selectOption("memory");
  await wizard.getByRole("button", { name: "Next", exact: true }).click();
  await wizard
    .getByRole("button", { name: "Start Investigation", exact: true })
    .click();

  let huntId = "";
  await expect
    .poll(
      async () => {
        const hunt = (await get("hunts")).find(
          (item: { id: string }) => !huntsBefore.includes(item.id),
        );
        if (!hunt) return "";
        huntId = hunt.id;
        return (await get(`hunts/${huntId}/jobs`))[0]?.status ?? "";
      },
      { timeout: 180000, intervals: [2000] },
    )
    .toBe("SUCCESS");

  const job = (await get(`hunts/${huntId}/jobs`))[0];
  const observations = (
    await get(`observations?case_id=${caseRecord.id}`)
  ).filter((observation: { job_id: string }) => observation.job_id === job.id);
  expect(observations.length).toBeGreaterThan(0);
  expect(
    new Set(
      observations.map(
        (observation: { collector: string }) => observation.collector,
      ),
    ),
  ).toEqual(
    new Set([
      "system",
      "users",
      "processes",
      "interfaces",
      "connections",
      "routes",
      "drivers",
    ]),
  );
  expect(
    observations.every(
      (observation: { document: { simulation: boolean } }) =>
        observation.document.simulation === false,
    ),
  ).toBe(true);
});
