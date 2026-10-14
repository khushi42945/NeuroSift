"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Eye, EyeOff, Fingerprint, LockKeyhole, Sparkles } from "lucide-react";
import { ApiError, signIn } from "@/lib/api";

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await signIn(mode === "login" ? "/api/auth/login" : "/api/auth/register", { email, password });
      router.push("/dashboard");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "We could not sign you in. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function continueAsGuest() {
    setError("");
    setBusy(true);
    try {
      await signIn("/api/auth/guest");
      router.push("/dashboard");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "A guest session could not be created.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-layout">
      <section className="auth-intro">
        <span className="eyebrow"><span className="eyebrow-dot" /> A quieter kind of check-in</span>
        <h1>Your well-being,<br /><em>in your own words.</em></h1>
        <p>A private place to notice patterns, check in with yourself, and find a next step that feels right.</p>
        <div className="auth-note"><Fingerprint size={19} /><span>Your journal stays yours. Entries are encrypted before storage.</span></div>
        <div className="intro-orbit" aria-hidden="true"><span /><span /><span /></div>
      </section>
      <section className="auth-panel" aria-labelledby="auth-heading">
        <div className="auth-panel-top"><span className="eyebrow">A space for you</span><Sparkles size={19} /></div>
        <h2 id="auth-heading">{mode === "login" ? "Welcome back." : "Start with a check-in."}</h2>
        <p className="panel-subtitle">{mode === "login" ? "Pick up where you left off." : "Make a private account in a moment."}</p>
        <div className="auth-tabs" role="tablist" aria-label="Account access">
          <button role="tab" aria-selected={mode === "login"} className={mode === "login" ? "auth-tab selected" : "auth-tab"} onClick={() => { setMode("login"); setError(""); }}>Log in</button>
          <button role="tab" aria-selected={mode === "register"} className={mode === "register" ? "auth-tab selected" : "auth-tab"} onClick={() => { setMode("register"); setError(""); }}>Create account</button>
        </div>
        <form className="auth-form" onSubmit={submit}>
          <label htmlFor="email">Email address</label>
          <input id="email" type="email" autoComplete="email" required maxLength={320} value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" />
          <label htmlFor="password">Password</label>
          <div className="password-field">
            <LockKeyhole size={17} aria-hidden="true" />
            <input id="password" type={showPassword ? "text" : "password"} autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={8} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" />
            <button className="password-toggle" type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button>
          </div>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="button button-primary auth-submit" disabled={busy} type="submit">{busy ? "One moment..." : mode === "login" ? "Log in" : "Create my account"}<ArrowRight size={17} /></button>
        </form>
        <div className="auth-divider"><span>or</span></div>
        <button className="button button-outline guest-button" disabled={busy} onClick={continueAsGuest}><Fingerprint size={18} /> Continue as an anonymous guest</button>
        <a className="google-link" href="/api/auth/google">Continue with Google <ArrowRight size={15} /></a>
        <p className="privacy-footnote">By continuing, you agree to use MindPulse as a self-reflection tool, not as a medical diagnosis.</p>
      </section>
    </div>
  );
}