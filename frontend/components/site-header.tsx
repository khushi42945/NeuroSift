"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Activity, ArrowUpRight, LogOut, Moon, Sun } from "lucide-react";
import { clearToken, getToken } from "@/lib/api";
import { useEffect, useState } from "react";

const navigation = [
  { href: "/dashboard", label: "Companion" },
  { href: "/emergency", label: "Support" },
  { href: "/auth", label: "Sign in / account" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const [signedIn, setSignedIn] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    setSignedIn(Boolean(getToken()));
    const savedTheme = window.localStorage.getItem("mindpulse_theme");
    const nextTheme = savedTheme === "dark" ? "dark" : "light";
    setTheme(nextTheme);
    document.documentElement.dataset.theme = nextTheme;
  }, [pathname]);

  function toggleTheme() {
    const nextTheme = theme === "light" ? "dark" : "light";
    setTheme(nextTheme);
    document.documentElement.dataset.theme = nextTheme;
    window.localStorage.setItem("mindpulse_theme", nextTheme);
  }

  function signOut() {
    clearToken();
    router.push("/auth");
  }

  return (
    <header className="site-header">
      <Link className="brand" href={signedIn ? "/dashboard" : "/auth"} aria-label="MindPulse home">
        <span className="brand-mark"><Activity size={17} strokeWidth={2.5} /></span>
        <span>mindpulse<span className="brand-period">.</span></span>
      </Link>
      {signedIn ? (
        <nav className="site-nav" aria-label="Main navigation">
          {navigation.map((item) => (
            <Link key={item.href} href={item.href} className={pathname.startsWith(item.href) ? "nav-link active" : "nav-link"}>
              {item.label}
            </Link>
          ))}
          <button className="nav-signout" onClick={signOut} aria-label="Sign out" title="Sign out"><LogOut size={16} /><span>Sign out</span></button>
        </nav>
      ) : (
        <Link className="header-link" href="/auth">Your private space <ArrowUpRight size={15} /></Link>
      )}
      <button className="theme-toggle" onClick={toggleTheme} aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`} title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}>
        {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
      </button>
    </header>
  );
}