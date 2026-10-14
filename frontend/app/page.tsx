"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  useEffect(() => router.replace(getToken() ? "/dashboard" : "/auth"), [router]);
  return <div className="page-loading" role="status">Opening your private space...</div>;
}