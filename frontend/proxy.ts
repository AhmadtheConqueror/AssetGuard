import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME } from "@/lib/auth/session";

const PROTECTED_PATHS = ["/", "/assets", "/alerts", "/maintenance"];

function isProtected(pathname: string): boolean {
  return PROTECTED_PATHS.some(
    (p) => pathname === p || (p !== "/" && pathname.startsWith(p + "/")),
  );
}

export function proxy(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const hasSession = Boolean(request.cookies.get(COOKIE_NAME)?.value);

  // Authenticated user visiting /login → send to dashboard
  if (pathname === "/login" && hasSession) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  // Unauthenticated user visiting a protected route → send to login
  if (isProtected(pathname) && !hasSession) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all paths EXCEPT:
     * - /api/* (Next.js route handlers)
     * - /_next/* (Next.js internals)
     * - /favicon.ico, /robots.txt, and static files
     */
    "/((?!api|_next/static|_next/image|favicon.ico|robots.txt).*)",
  ],
};
