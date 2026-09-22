import { NextResponse } from "next/server";

const BACKEND_API_URL = process.env.BACKEND_API_URL;

/**
 * Public health check proxy — no auth required.
 * Forwards to FastAPI /health so the sidebar health indicator
 * works without needing a valid session.
 */
export async function GET(): Promise<NextResponse> {
  if (!BACKEND_API_URL) {
    return NextResponse.json({ status: "misconfigured" }, { status: 500 });
  }

  try {
    const res = await fetch(`${BACKEND_API_URL}/health`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });

    const body = (await res.json()) as unknown;
    return NextResponse.json(body, { status: res.status });
  } catch {
    return NextResponse.json({ status: "unavailable" }, { status: 503 });
  }
}
