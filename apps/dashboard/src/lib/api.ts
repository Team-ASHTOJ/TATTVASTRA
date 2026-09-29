export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/control/${path}`, {
    ...init,
    cache: "no-store",
    signal: AbortSignal.timeout(180_000),
  });
  if (!response.ok) {
    const problem: { detail?: string; message?: string } = await response
      .json()
      .catch(() => ({}));
    throw new ApiError(
      problem.detail ??
        problem.message ??
        `Control plane returned HTTP ${response.status}`,
      response.status,
    );
  }
  return response.json() as Promise<T>;
}
