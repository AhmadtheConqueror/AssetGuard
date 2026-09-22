import { NextRequest, NextResponse } from "next/server";
import { getJwtFromRequest, clearCookie } from "@/lib/auth/session";

const BACKEND_API_URL = process.env.BACKEND_API_URL;

type RouteContext = { params: Promise<{ path: string[] }> };

async function handleRequest(
  request: NextRequest,
  context: RouteContext,
  method: string,
): Promise<NextResponse> {
  if (!BACKEND_API_URL) {
    return NextResponse.json({ error: "Server misconfiguration." }, { status: 500 });
  }

  const jwt = getJwtFromRequest(request);
  if (!jwt) {
    return NextResponse.json({ error: "Unauthenticated." }, { status: 401 });
  }

  // Build target URL — only ever targets BACKEND_API_URL
  const { path } = await context.params;
  const pathSegment = path.join("/");
  const search = request.nextUrl.search ?? "";
  const targetUrl = `${BACKEND_API_URL}/${pathSegment}${search}`;

  // Forward request body for mutating methods
  let bodyInit: BodyInit | null = null;
  if (method === "POST" || method === "PATCH" || method === "PUT" || method === "DELETE") {
    const contentType = request.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      try {
        bodyInit = await request.text();
      } catch {
        bodyInit = null;
      }
    }
  }

  let backendRes: Response;
  try {
    backendRes = await fetch(targetUrl, {
      method,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
      },
      ...(bodyInit !== null ? { body: bodyInit } : {}),
    });
  } catch {
    return NextResponse.json({ error: "Backend unreachable." }, { status: 503 });
  }

  // On 401 from backend — JWT is invalid/expired; clear cookie
  if (backendRes.status === 401) {
    const response = NextResponse.json({ error: "Session expired." }, { status: 401 });
    clearCookie(response);
    return response;
  }

  // On 403 — authenticated but not authorised; do NOT clear cookie
  if (backendRes.status === 403) {
    let body: unknown;
    try { body = await backendRes.json(); } catch { body = { error: "Forbidden." }; }
    return NextResponse.json(body, { status: 403 });
  }

  // Pass through all other responses
  let responseBody: unknown;
  const responseText = await backendRes.text();
  try {
    responseBody = JSON.parse(responseText);
  } catch {
    // Return raw text if not JSON
    return new NextResponse(responseText, {
      status: backendRes.status,
      headers: { "Content-Type": "text/plain" },
    });
  }

  return NextResponse.json(responseBody, { status: backendRes.status });
}

export async function GET(request: NextRequest, context: RouteContext) {
  return handleRequest(request, context, "GET");
}

export async function POST(request: NextRequest, context: RouteContext) {
  return handleRequest(request, context, "POST");
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return handleRequest(request, context, "PATCH");
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return handleRequest(request, context, "DELETE");
}
