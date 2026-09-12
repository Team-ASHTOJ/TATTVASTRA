export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/control/${path}`, {
    ...init,
    cache: "no-store",
    signal: AbortSignal.timeout(10_000),
  });
  if (!response.ok) {
    const problem: { detail?: string } = await response
      .json()
      .catch(() => ({}));
    throw new Error(
      problem.detail ?? `Control plane returned HTTP ${response.status}`,
    );
  }
  return response.json() as Promise<T>;
}
