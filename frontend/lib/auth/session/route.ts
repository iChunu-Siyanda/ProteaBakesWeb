import { NextResponse } from "next/server";
import { getTokens } from "@/lib/auth/session";

export const dynamic = "force-dynamic";

export async function GET() {
  const { access, refresh } = await getTokens();
  return NextResponse.json(
    { authenticated: Boolean(access || refresh) },
    { headers: { "Cache-Control": "no-store" } },
  );
}
