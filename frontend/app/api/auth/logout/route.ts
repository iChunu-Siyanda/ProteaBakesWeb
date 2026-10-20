import { NextResponse } from "next/server";
import { API_URL } from "@/lib/api/server";
import { clearAuthCookies, getTokens } from "@/lib/auth/session";

export async function POST() {
  const { access, refresh } = await getTokens();
  if (refresh) {
    await fetch(`${API_URL}/api/auth/logout/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(access ? { Authorization: `Bearer ${access}` } : {}),
      },
      body: JSON.stringify({ refresh }),
      cache: "no-store",
    }).catch(() => null);
  }
  await clearAuthCookies();
  return NextResponse.json({ ok: true });
}
