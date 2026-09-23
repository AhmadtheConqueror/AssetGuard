"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api/client";
import { useSession } from "@/lib/auth/SessionContext";
import { hasPermission } from "@/lib/auth/permissions";

type HealthState = "checking" | "connected" | "unavailable";

const navigation = [
  { href: "/", label: "Dashboard", marker: "01" },
  { href: "/assets", label: "Assets", marker: "02" },
  { href: "/alerts", label: "Alerts", marker: "03" },
  { href: "/maintenance", label: "Maintenance", marker: "04" },
];

const adminNavigation = [
  { href: "/admin/users", label: "Users", marker: "05" },
];

const pageMeta: Record<string, { eyebrow: string; title: string; description: string }> = {
  "/": { eyebrow: "Control room", title: "Operations overview", description: "A clear starting point for asset reliability work." },
  "/assets": { eyebrow: "Asset register", title: "Assets", description: "Browse the equipment connected to AssetGuard." },
  "/alerts": { eyebrow: "Signal review", title: "Alerts", description: "A focused space for reliability signals and triage." },
  "/maintenance": { eyebrow: "Reliability work", title: "Maintenance", description: "Plan and review work across the asset estate." },
  "/admin/users": { eyebrow: "User administration", title: "Users", description: "Manage AssetGuard accounts and operational roles." },
};

function getPageMeta(pathname: string) {
  if (pathname.startsWith("/assets/")) {
    return { eyebrow: "Asset register", title: "Asset detail", description: "A structured view for asset reliability context." };
  }

  return pageMeta[pathname] ?? pageMeta["/"];
}

function StatusIndicator({ state }: { state: HealthState }) {
  const labels = { checking: "Checking backend", connected: "Backend connected", unavailable: "Backend unavailable" };

  return (
    <div className={`status-indicator status-${state}`} aria-live="polite">
      <span className="status-dot" aria-hidden="true" />
      <span>{labels[state]}</span>
    </div>
  );
}

function UserBlock() {
  const { user, logout } = useSession();

  if (!user) return null;

  return (
    <div className="user-block">
      <div className="user-block-info">
        <span className="user-block-name">{user.full_name}</span>
        <span className="user-block-role">{user.role.toUpperCase()}</span>
      </div>
      <button
        id="sidebar-logout-btn"
        type="button"
        className="logout-button"
        onClick={() => void logout()}
        aria-label="Sign out of AssetGuard"
      >
        Logout
      </button>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user } = useSession();
  const [healthState, setHealthState] = useState<HealthState>("checking");
  const meta = getPageMeta(pathname);
  const visibleNavigation = hasPermission(user, "administerUsers") ? [...navigation, ...adminNavigation] : navigation;

  useEffect(() => {
    let mounted = true;

    getHealth()
      .then(() => {
        if (mounted) setHealthState("connected");
      })
      .catch(() => {
        if (mounted) setHealthState("unavailable");
      });

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <Link href="/" className="brand-mark" aria-label="AssetGuard home">
            <span className="brand-symbol" aria-hidden="true">AG</span>
            <span><strong>AssetGuard</strong><small>Reliability intelligence</small></span>
          </Link>
        </div>
        <div className="nav-section-label">Workspace</div>
        <nav className="primary-nav" aria-label="Primary navigation">
          {visibleNavigation.map((item) => {
            const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

            return (
              <Link key={item.href} href={item.href} aria-current={isActive ? "page" : undefined} className={`nav-link ${isActive ? "nav-link-active" : ""}`}>
                <span className="nav-marker" aria-hidden="true">{item.marker}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <UserBlock />
          <div className="nav-section-label" style={{ marginTop: "16px" }}>System</div>
          <StatusIndicator state={healthState} />
          <p className="sidebar-note">Connected to the AssetGuard API</p>
        </div>
      </aside>
      <main className="main-panel">
        <header className="topbar">
          <div><p className="eyebrow">{meta.eyebrow}</p><h1>{meta.title}</h1><p className="topbar-description">{meta.description}</p></div>
        </header>
        <div className="page-content">{children}</div>
      </main>
    </div>
  );
}
