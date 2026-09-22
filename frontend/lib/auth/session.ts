/**
 * Server-only session cookie utilities.
 * Never import this file from client components.
 */
import { cookies } from "next/headers";
import type { NextRequest, NextResponse } from "next/server";

export const COOKIE_NAME = "ag_session";

const isProduction = process.env.NODE_ENV === "production";

/**
 * Write the JWT into an HttpOnly session cookie on the given response.
 * maxAge must be supplied from the backend `expires_in` value.
 */
export function setCookie(response: NextResponse, jwt: string, maxAge: number): void {
  response.cookies.set(COOKIE_NAME, jwt, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: isProduction,
    maxAge,
  });
}

/**
 * Clear the session cookie on the given response.
 */
export function clearCookie(response: NextResponse): void {
  response.cookies.set(COOKIE_NAME, "", {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: isProduction,
    maxAge: 0,
  });
}

/**
 * Read the JWT from an incoming NextRequest's cookies.
 * Used in middleware and route handlers that receive a NextRequest.
 */
export function getJwtFromRequest(request: NextRequest): string | null {
  return request.cookies.get(COOKIE_NAME)?.value ?? null;
}

/**
 * Read the JWT from the Next.js cookies() store.
 * Used inside server components and route handlers that use the cookies() API.
 */
export async function getJwtFromCookies(): Promise<string | null> {
  const store = await cookies();
  return store.get(COOKIE_NAME)?.value ?? null;
}
