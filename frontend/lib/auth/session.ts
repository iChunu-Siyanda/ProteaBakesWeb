import { cookies } from "next/headers";
import { API_URL } from "@/lib/api/server";

const ACCESS = "pb_access";
const REFRESH = "pb_refresh";
// sameSite "lax" (not "strict") so the session survives the redirect back from Yoco.
const base = { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax" as const, path: "/" };

export type Tokens = { access: string; refresh: string };

export async function setAuthCookies(t: Tokens) {
  const jar = await cookies();
  jar.set(ACCESS, t.access, { ...base, maxAge: 60 * 14 }); // JWT lasts 15 min
  jar.set(REFRESH, t.refresh, { ...base, maxAge: 60 * 60 * 24 * 7 });
}

export async function clearAuthCookies() {
  const jar = await cookies();
  jar.delete(ACCESS);
  jar.delete(REFRESH);
}

export async function getTokens() {
  const jar = await cookies();
  return { access: jar.get(ACCESS)?.value, refresh: jar.get(REFRESH)?.value };
}

export async function requestTokens(email: unknown, password: unknown) {
  try {
    const res = await fetch(`${API_URL}/api/auth/token/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      cache: "no-store",
    });
    const body: unknown = await res.json().catch(() => null);
    return { ok: res.ok, status: res.status, body };
  } catch {
    return { ok: false, status: 502, body: null as unknown };
  }
}

// Refresh rotates (old token is blacklisted), so parallel requests must share ONE refresh call.
const inflight = new Map<string, Promise<Tokens | null>>();

export function refreshTokens(refresh: string): Promise<Tokens | null> {
  let p = inflight.get(refresh);
  if (!p) {
    p = (async () => {
      try {
        const res = await fetch(`${API_URL}/api/auth/token/refresh/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh }),
          cache: "no-store",
        });
        if (!res.ok) return null;
        const d = await res.json();
        return { access: d.access as string, refresh: (d.refresh as string | undefined) ?? refresh };
      } catch {
        return null;
      }
    })();
    inflight.set(refresh, p);
    setTimeout(() => inflight.delete(refresh), 10_000);
  }
  return p;
}
