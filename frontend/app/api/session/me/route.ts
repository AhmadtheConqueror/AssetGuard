import { NextResponse } from "next/server";
import { getJwtFromCookies, clearCookie } from "@/lib/auth/session";
import type { SessionUser } from "@/lib/auth/types";

const BACKEND_API_URL = process.env.BACKEND_API_URL;

export async function GET(): Promise<NextResponse> {
  if (!BACKEND_API_URL) {
    return NextResponse.json({ error: "Server misconfiguration." }, { status: 500 });
  }

  const jwt = await getJwtFromCookies();
  if (!jwt) {
    return NextResponse.json({ error: "No session." }, { status: 401 });
  }

  let user: SessionUser;
  try {
    const meRes = await fetch(`${BACKEND_API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${jwt}`, Accept: "application/json" },
      cache: "no-store",
    });

    if (meRes.status === 401) {
      const response = NextResponse.json({ error: "Session expired." }, { status: 401 });
      clearCookie(response);
      return response;
    }

    if (!meRes.ok) {
      return NextResponse.json({ error: "Could not verify session." }, { status: 502 });
    }

    user = (await meRes.json()) as SessionUser;
  } catch {
    return NextResponse.json({ error: "Service unavailable." }, { status: 503 });
  }

  return NextResponse.json({ user });
}
