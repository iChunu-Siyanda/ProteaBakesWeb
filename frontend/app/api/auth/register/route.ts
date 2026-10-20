import { NextResponse } from "next/server";
import { API_URL } from "@/lib/api/server";
import { NETWORK_ERROR } from "@/lib/api/errors";
import { requestTokens, setAuthCookies, type Tokens } from "@/lib/auth/session";

export async function POST(req: Request) {
  const input = await req.json().catch(() => null);
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/auth/register/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ message: NETWORK_ERROR }, { status: 502 });
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) return NextResponse.json(data ?? {}, { status: res.status });

  const login = await requestTokens(input?.email, input?.password);
  if (login.ok) {
    await setAuthCookies(login.body as Tokens);
    return NextResponse.json({ ok: true, authenticated: true }, { status: 201 });
  }
  return NextResponse.json({ ok: true, authenticated: false }, { status: 201 });
}
