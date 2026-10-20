// token refresh is handled here; there’s no separate refresh route

import { NextRequest, NextResponse } from "next/server";
import { API_URL } from "@/lib/api/server";
import { NETWORK_ERROR } from "@/lib/api/errors";
import { clearAuthCookies, getTokens, refreshTokens, setAuthCookies, type Tokens } from "@/lib/auth/session";

export const dynamic = "force-dynamic";

const IS_PROD = process.env.NODE_ENV === "production";
// Token-issuing endpoints must never be reachable through the proxy (they'd leak tokens to JS).
const BLOCKED = /^auth\/(token|register|logout)(\/|$)/;
const FORWARD = ["content-type", "x-webhook-event-id", "x-webhook-event-type"];

type Ctx = { params: Promise<{ path: string[] }> };

async function handler(req: NextRequest, { params }: Ctx) {
  const { path } = await params;
  const joined = path.join("/");
  if (BLOCKED.test(joined) || (IS_PROD && joined.startsWith("payments/webhook"))) {
    return NextResponse.json({ message: "Not found." }, { status: 404 });
  }

  // Next strips trailing slashes from incoming URLs; Django needs them.
  const url = `${API_URL}/api/${joined}/${req.nextUrl.search}`;
  const body = req.method === "GET" || req.method === "HEAD" ? undefined : await req.text();

  const send = (access?: string) => {
    const headers = new Headers({ Accept: "application/json" });
    for (const h of FORWARD) {
      const v = req.headers.get(h);
      if (v) headers.set(h, v);
    }
    if (access) headers.set("Authorization", `Bearer ${access}`);
    return fetch(url, { method: req.method, headers, body, cache: "no-store" });
  };

  const { access, refresh } = await getTokens();
  let token = access;
  let fresh: Tokens | null = null;
  let expired = false;

  if (!token && refresh) {
    fresh = await refreshTokens(refresh);
    if (fresh) token = fresh.access;
    else expired = true;
  }

  let upstream: Response;
  try {
    upstream = await send(token);
    if (upstream.status === 401 && refresh && !fresh && !expired) {
      fresh = await refreshTokens(refresh);
      if (fresh) upstream = await send(fresh.access);
      else expired = true;
    }
  } catch {
    return NextResponse.json({ message: NETWORK_ERROR }, { status: 502 });
  }

  if (fresh) await setAuthCookies(fresh);
  if (expired) await clearAuthCookies();

  const text = await upstream.text();
  return new NextResponse(text || null, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
      "Cache-Control": "no-store",
    },
  });
}

export { handler as GET, handler as POST, handler as PATCH, handler as PUT, handler as DELETE };
