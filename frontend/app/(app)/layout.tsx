import { AppShell } from "@/components/AppShell";
import { SessionProvider } from "@/lib/auth/SessionContext";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <AppShell>{children}</AppShell>
    </SessionProvider>
  );
}
