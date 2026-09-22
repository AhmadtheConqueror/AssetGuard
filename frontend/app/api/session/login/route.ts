import { NextRequest, NextResponse } from "next/server";
import { setCookie } from "@/lib/auth/session";
import type { SessionUser } from "@/lib/auth/types";

const BACKEND_API_URL = process.env.BACKEND_API_URL;

interface LoginRequestBody {
  email: string;
  password: string;
}

interface BackendLoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

type BackendMeResponse = SessionUser;


export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!BACKEND_API_URL) {
    return NextResponse.json({ error: "Server misconfiguration." }, { status: 500 });
  }

  let body: LoginRequestBody;
  try {
    body = (await request.json()) as LoginRequestBody;
  } catch {
    return NextResponse.json({ error: "Invalid request body." }, { status: 400 });
  }

  const { email, password } = body;

  if (!email || !password) {
    return NextResponse.json({ error: "Email and password are required." }, { status: 400 });
  }

  // --- Call backend login ---
  let loginData: BackendLoginResponse;
  try {
    const loginRes = await fetch(`${BACKEND_API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (loginRes.status === 401 || loginRes.status === 403) {
      return NextResponse.json({ error: "Invalid email or password." }, { status: 401 });
    }

    if (!loginRes.ok) {
      return NextResponse.json({ error: "Authentication service error." }, { status: 502 });
    }

    loginData = (await loginRes.json()) as BackendLoginResponse;
  } catch {
    return NextResponse.json({ error: "Service unavailable. Please try again." }, { status: 503 });
  }

  const jwt = loginData.access_token;
  if (!jwt) {
    return NextResponse.json({ error: "Authentication service error." }, { status: 502 });
  }

  const expiresIn = loginData.expires_in;
  if (!Number.isFinite(expiresIn) || expiresIn <= 0) {
    return NextResponse.json({ error: "Authentication service error." }, { status: 502 });
  }

  // --- Fetch user profile using the new token ---
  let user: BackendMeResponse;
  try {
    const meRes = await fetch(`${BACKEND_API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${jwt}`, Accept: "application/json" },
    });

    if (!meRes.ok) {
      return NextResponse.json({ error: "Authentication service error." }, { status: 502 });
    }

    user = (await meRes.json()) as BackendMeResponse;
  } catch {
    return NextResponse.json({ error: "Service unavailable. Please try again." }, { status: 503 });
  }

  // --- Return sanitised user — JWT stays server-side ---
  const response = NextResponse.json({ user });
  setCookie(response, jwt, expiresIn);
  return response;
}
