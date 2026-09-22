import { NextResponse } from "next/server";
import { getJwtFromCookies, clearCookie } from "@/lib/auth/session";

const BACKEND_API_URL = process.env.BACKEND_API_URL;

export async function POST(): Promise<NextResponse> {
  const jwt = await getJwtFromCookies();

  // Best-effort: await the backend logout but never let a failure
  // prevent local session destruction.
  if (jwt && BACKEND_API_URL) {
    try {
      await fetch(`${BACKEND_API_URL}/api/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${jwt}`, Accept: "application/json" },
      });
    } catch {
      // Backend logout failure must not prevent local cookie deletion
    }
  }

  // Always clear the cookie regardless of backend acknowledgement
  const response = NextResponse.json({ ok: true });
  clearCookie(response);
  return response;
}
