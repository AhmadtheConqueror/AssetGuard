"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { SessionUser } from "./types";

interface SessionContextValue {
  user: SessionUser | null;
  isLoading: boolean;
  logout: () => Promise<void>;
}

const SessionContext = createContext<SessionContextValue>({
  user: null,
  isLoading: true,
  logout: async () => {},
});

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<SessionUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    fetch("/api/session/me", { credentials: "same-origin" })
      .then(async (res) => {
        if (!mounted) return;
        if (res.ok) {
          const data = (await res.json()) as { user: SessionUser };
          setUser(data.user);
        } else {
          setUser(null);
          // 401 means session is gone — middleware will handle redirect on next navigation
        }
      })
      .catch(() => {
        if (mounted) setUser(null);
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch("/api/session/logout", { method: "POST", credentials: "same-origin" });
    } catch {
      // Network failure — proceed with local state clear
    }
    setUser(null);
    router.push("/login");
  }, [router]);

  return (
    <SessionContext.Provider value={{ user, isLoading, logout }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionContextValue {
  return useContext(SessionContext);
}
