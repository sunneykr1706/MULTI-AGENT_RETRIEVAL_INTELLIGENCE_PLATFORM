"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getAccessToken } from "@/lib/api";

function isExpired(token: string | null): boolean {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return !payload?.exp || Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
}

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = getAccessToken();
    router.replace(token && !isExpired(token) ? "/chat" : "/login");
  }, [router]);

  return null;
}
