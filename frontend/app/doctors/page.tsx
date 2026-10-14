"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, HeartHandshake } from "lucide-react";
import { DoctorDirectory } from "@/components/DoctorDirectory";
import { getToken } from "@/lib/api";

const DIRECTORY_PROFILE = {
  primary_issue: "general",
  severity: "low",
  keywords: [],
};

export default function DoctorsPage() {
  const router = useRouter();

  useEffect(() => {
    if (!getToken()) router.replace("/auth");
  }, [router]);

  return (
    <div className="page-wrap consultation-page">
      <Link className="back-link" href="/dashboard"><ArrowLeft size={16} /> Back to companion</Link>
      <header className="consultation-heading">
        <span className="consultation-icon"><HeartHandshake size={20} /></span>
        <div>
          <span className="eyebrow"><span className="eyebrow-dot" /> PROFESSIONAL SUPPORT</span>
          <h1>Explore consultation options.</h1>
          <p>Browse sample profiles and filter by specialty, language, experience, rating, and session mode.</p>
        </div>
      </header>
      <DoctorDirectory profile={DIRECTORY_PROFILE} onClose={() => router.push("/dashboard")} />
    </div>
  );
}