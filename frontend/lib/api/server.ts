import { ApiError, NETWORK_ERROR, parseApiError } from "./errors";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

/** Server-side GET for public endpoints (products, categories). path: "/products/" */
export async function apiGet<T>(path: string, opts: { revalidate?: number } = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api${path}`, {
      headers: { Accept: "application/json" },
      next: { revalidate: opts.revalidate ?? 60 },
    });
  } catch {
    throw new ApiError(0, NETWORK_ERROR);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) throw parseApiError(res.status, body);
  return body as T;
}
