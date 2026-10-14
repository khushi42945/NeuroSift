"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { setToken } from "@/lib/api";

export default function AuthCallbackPage() {
  const router = useRouter();
  useEffect(() => {
    const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
    if (token) {
      setToken(token);
      router.replace("/dashboard");
    } else {
      router.replace("/auth?error=google");
    }
  }, [router]);
  return <div className="page-loading" role="status">Finishing secure sign-in...</div>;
}