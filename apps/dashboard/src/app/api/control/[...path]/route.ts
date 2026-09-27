import { NextRequest, NextResponse } from "next/server";

const routes = new Map([
  ["GET status", "status"],
  ["GET endpoints", "endpoints"],
  ["POST compilations", "compilations"],
  ["POST evidence/verify-observation", "evidence/verify-observation"],
]);
const domains = new Set([
  "auth",
  "demo",
  "observations",
  "jobs",
  "cases",
  "scripts",
  "compilations",
  "variants",
  "build-runs",
  "build-capabilities",
  "endpoints",
  "local-agent",
  "local-agents",
  "hunts",
  "artifacts",
  "manifests",
  "findings",
  "timeline",
  "graph",
  "benchmarks",
  "compatibility-runs",
  "reports",
  "events",
  "audit",
]);

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const persistent = path[0] === "domain";
  const parts = persistent ? path.slice(1) : path;
  const route = persistent
    ? domains.has(parts[0] ?? "") &&
      parts.every((p) => /^[a-zA-Z0-9-]+$/.test(p))
      ? parts.join("/")
      : undefined
    : routes.get(`${request.method} ${parts.join("/")}`);
  if (!route)
    return NextResponse.json(
      { detail: "Unknown control-plane route" },
      { status: 404 },
    );
  const mutating = !["GET", "HEAD"].includes(request.method);
  if (mutating) {
    const origin = request.headers.get("origin");
    let sameOrigin = origin === request.nextUrl.origin;
    if (!sameOrigin && origin) {
      try {
        sameOrigin = new URL(origin).host === request.headers.get("host");
      } catch {
        sameOrigin = false;
      }
    }
    if (!sameOrigin)
      return NextResponse.json(
        { detail: "Same-origin request required" },
        { status: 403 },
      );
  }
  try {
    const body = mutating ? await request.text() : undefined;
    if (body && Buffer.byteLength(body) > 1_048_576)
      return NextResponse.json(
        { detail: "Request exceeds 1 MiB" },
        { status: 413 },
      );
    const session = request.cookies.get("jocky_session")?.value;
    const streaming = persistent && route === "events";
    const response = await fetch(
      `${process.env.JOCKY_API_URL ?? "http://127.0.0.1:8000"}/api/${persistent ? "" : "v1/"}${route}${request.nextUrl.search}`,
      {
        method: request.method,
        headers: {
          "Content-Type": "application/json",
          ...(session ? { Authorization: `Bearer ${session}` } : {}),
          ...(request.headers.has("last-event-id")
            ? { "Last-Event-ID": request.headers.get("last-event-id")! }
            : {}),
        },
        ...(body === undefined ? {} : { body }),
        cache: "no-store",
        signal: streaming ? request.signal : AbortSignal.timeout(180_000),
        redirect: "error",
      },
    );
    if (persistent && route === "auth/login" && response.ok) {
      const login = await response.json();
      const result = NextResponse.json({
        user: login.user,
        expires_at: login.expires_at,
      });
      result.cookies.set("jocky_session", login.access_token, {
        httpOnly: true,
        sameSite: "strict",
        secure: request.nextUrl.protocol === "https:",
        path: "/",
        maxAge: 3600,
      });
      result.headers.set("Cache-Control", "no-store");
      return result;
    }
    if (streaming && response.status === 401) {
      const result = new NextResponse(
        'event: auth.expired\ndata: {"detail":"Session expired"}\n\n',
        {
          status: 200,
          headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
          },
        },
      );
      result.cookies.delete("jocky_session");
      return result;
    }
    const result = new NextResponse(response.body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        ...(response.headers.has("content-disposition")
          ? { "Content-Disposition": "attachment" }
          : {}),
      },
    });
    if (route === "auth/logout" || response.status === 401)
      result.cookies.delete("jocky_session");
    return result;
  } catch {
    return NextResponse.json(
      {
        simulation: false,
        code: "JOCKY_E_CONTROL_PLANE_UNAVAILABLE",
        detail:
          "Control plane unavailable. Start the API with make dev-api or docker compose up --build, then retry.",
        status: 503,
      },
      { status: 503 },
    );
  }
}
export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
