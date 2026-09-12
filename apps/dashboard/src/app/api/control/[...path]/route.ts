import { NextRequest, NextResponse } from "next/server";

const routes = new Map([
  ["GET status", "status"],
  ["GET endpoints", "endpoints"],
  ["POST compilations", "compilations"],
  ["POST evidence/verify-observation", "evidence/verify-observation"],
]);

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const route = routes.get(`${request.method} ${path.join("/")}`);
  if (!route)
    return NextResponse.json(
      { detail: "Unknown control-plane route" },
      { status: 404 },
    );
  try {
    const body = request.method === "POST" ? await request.text() : undefined;
    if (body && Buffer.byteLength(body) > 1_048_576)
      return NextResponse.json(
        { detail: "Request exceeds 1 MiB" },
        { status: 413 },
      );
    const response = await fetch(
      `${process.env.JOCKY_API_URL ?? "http://127.0.0.1:8000"}/api/v1/${route}`,
      {
        method: request.method,
        headers: { "Content-Type": "application/json" },
        ...(body === undefined ? {} : { body }),
        cache: "no-store",
        signal: AbortSignal.timeout(5_000),
        redirect: "error",
      },
    );
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      {
        simulation: false,
        code: "JOCKY_E_CONTROL_PLANE_UNAVAILABLE",
        detail:
          "Control plane unavailable. Start the API with make dev-api, then retry.",
        status: 503,
      },
      { status: 503 },
    );
  }
}
export const GET = proxy;
export const POST = proxy;
