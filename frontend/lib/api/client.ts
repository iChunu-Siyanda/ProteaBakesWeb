import { ApiError, NETWORK_ERROR, parseApiError } from "./errors";

type Opts = Omit<RequestInit, "body"> & { json?: unknown };

async function request<T>(url: string, { json, headers, ...rest }: Opts): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, {
      ...rest,
      headers: { ...(json !== undefined ? { "Content-Type": "application/json" } : {}), ...headers },
      body: json !== undefined ? JSON.stringify(json) : undefined,
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, NETWORK_ERROR);
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw parseApiError(res.status, data);
  return data as T;
}

/** Browser -> Django via the proxy. Pass paths WITHOUT /api and WITHOUT trailing slash:
 *  apiFetch("/cart"), apiFetch("/cart/items", { method: "POST", json: {...} }) */
export function apiFetch<T = unknown>(path: string, opts: Opts = {}) {
  return request<T>(`/api/proxy${path}`, opts);
}

/** Cookie-setting auth endpoints (route handlers). */
export function authRequest<T = { ok: true }>(
  action: "login" | "register" | "logout",
  json?: unknown,
) {
  return request<T>(`/api/auth/${action}`, { method: "POST", json });
}
