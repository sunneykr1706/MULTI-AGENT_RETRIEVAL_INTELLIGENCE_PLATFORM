"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { getAccessToken } from "@/lib/api";

const PUBLIC_ROUTES = new Set(["/login", "/register"]);

function isExpired(token: string | null): boolean {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (!payload?.exp) return true;
    return Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  const isPublic = useMemo(() => PUBLIC_ROUTES.has(pathname), [pathname]);

  useEffect(() => {
    const token = getAccessToken();

    if (isPublic) {
      if (token && !isExpired(token)) {
        router.replace("/chat");
        return;
      }
      setReady(true);
      return;
    }

    if (!token || isExpired(token)) {
      router.replace("/login");
      return;
    }

    setReady(true);
  }, [isPublic, router, pathname]);

  if (!ready) {
    return (
      <div className="flex items-center justify-center w-full h-screen" style={{ background: "var(--background)" }}>
        <div className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-2 h-2 rounded-full typing-dot"
              style={{ background: "var(--accent)", animationDelay: `${i * 0.2}s` }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (isPublic) {
    return <main className="flex-1 flex flex-col overflow-hidden">{children}</main>;
  }

  return (
    <>
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">{children}</main>
    </>
  );
}
