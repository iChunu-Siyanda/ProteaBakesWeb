import { NextResponse } from "next/server";
import { NETWORK_ERROR } from "@/lib/api/errors";
import { requestTokens, setAuthCookies, type Tokens } from "@/lib/auth/session";

export async function POST(req: Request) {
  const input = await req.json().catch(() => null);
  const r = await requestTokens(input?.email, input?.password);
  if (!r.ok) {
    if (r.status === 502) return NextResponse.json({ message: NETWORK_ERROR }, { status: 502 });
    if (r.status === 401) return NextResponse.json({ message: "Incorrect email or password." }, { status: 401 });
    return NextResponse.json(r.body ?? {}, { status: r.status });
  }
  await setAuthCookies(r.body as Tokens);
  return NextResponse.json({ ok: true });
}
