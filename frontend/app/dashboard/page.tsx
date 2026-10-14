"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChatInterface } from "@/components/ChatInterface";
import { getToken } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();

  useEffect(() => {
    if (!getToken()) router.replace("/auth");
  }, [router]);

  return <div className="page-wrap companion-page"><ChatInterface /></div>;
}