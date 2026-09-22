"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { SessionUser } from "@/lib/auth/types";

type LoginState = "idle" | "signing-in" | "invalid-credentials" | "unavailable";

export default function LoginPage() {
  const router = useRouter();
  const [loginState, setLoginState] = useState<LoginState>("idle");
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  // Auto-focus email on mount
  useEffect(() => {
    emailRef.current?.focus();
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const email = emailRef.current?.value.trim() ?? "";
    const password = passwordRef.current?.value ?? "";

    if (!email || !password) return;

    setLoginState("signing-in");

    try {
      const res = await fetch("/api/session/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ email, password }),
      });

      if (res.status === 401) {
        setLoginState("invalid-credentials");
        // Clear password only — keep email for correction
        if (passwordRef.current) passwordRef.current.value = "";
        passwordRef.current?.focus();
        return;
      }

      if (res.status === 503 || res.status === 502 || !res.ok) {
        setLoginState("unavailable");
        return;
      }

      // Success — user data returned but we don't store token anywhere client-side
      await res.json() as { user: SessionUser };

      router.replace("/");
    } catch {
      setLoginState("unavailable");
    }
  }

  const isSubmitting = loginState === "signing-in";

  return (
    <div className="login-page" id="login-page">
      <div className="login-card">
        <div className="login-brand">
          <span className="brand-symbol" aria-hidden="true">AG</span>
          <div>
            <strong>AssetGuard</strong>
            <small>Reliability intelligence</small>
          </div>
        </div>

        <div className="login-intro">
          <h1>Sign in</h1>
          <p>Access the AssetGuard operations platform.</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit} noValidate id="login-form">
          <div className="login-field">
            <label htmlFor="login-email">Email address</label>
            <input
              id="login-email"
              ref={emailRef}
              type="email"
              name="email"
              autoComplete="email"
              required
              disabled={isSubmitting}
              placeholder="you@example.com"
            />
          </div>

          <div className="login-field">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              ref={passwordRef}
              type="password"
              name="password"
              autoComplete="current-password"
              required
              disabled={isSubmitting}
              placeholder="••••••••"
            />
          </div>

          {loginState === "invalid-credentials" && (
            <div className="login-error" role="alert" aria-live="assertive" id="login-error">
              Invalid email or password.
            </div>
          )}

          {loginState === "unavailable" && (
            <div className="login-error login-error-unavailable" role="alert" aria-live="assertive" id="login-error">
              Service unavailable. Please try again.
            </div>
          )}

          <button
            id="login-submit"
            type="submit"
            className="login-submit"
            disabled={isSubmitting}
            aria-busy={isSubmitting}
          >
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
