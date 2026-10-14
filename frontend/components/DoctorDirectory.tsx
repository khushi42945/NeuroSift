"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUpRight, BadgeCheck, BriefcaseBusiness, CalendarClock, Languages, MapPin, SlidersHorizontal, Star, Video, X } from "lucide-react";
import { ApiError, api } from "@/lib/api";

type ProfileContext = { primary_issue: string; severity: string; keywords: string[] };
type Therapist = {
  id: number;
  display_name: string;
  credentials: string;
  headline: string;
  specialties: string[];
  years_experience: number;
  session_fee_inr: number;
  languages: string[];
  session_modes: string[];
  rating: number;
  review_count: number;
  bio: string;
  booking_url: string | null;
  is_verified: boolean;
  is_demo: boolean;
  match_reasons: string[];
};
type DirectoryResult = { doctors: Therapist[]; safety_first: boolean; note: string };

export function DoctorDirectory({ profile, onClose }: { profile: ProfileContext; onClose: () => void }) {
  const [results, setResults] = useState<DirectoryResult | null>(null);
  const [mode, setMode] = useState("");
  const [language, setLanguage] = useState("");
  const [minimumExperience, setMinimumExperience] = useState("0");
  const [specialty, setSpecialty] = useState("");
  const [minimumRating, setMinimumRating] = useState("0");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    api<DirectoryResult>("/api/doctors/recommend", {
      method: "POST",
      body: JSON.stringify({
        primary_issue: profile.primary_issue,
        severity: profile.severity,
        keywords: profile.keywords,
        session_mode: mode || null,
        language: language || null,
        min_experience: Number(minimumExperience),
        specialty: specialty || null,
        min_rating: Number(minimumRating),
      }),
    }).then((data) => { if (active) { setResults(data); setError(""); } })
      .catch((cause) => { if (active) setError(cause instanceof ApiError ? cause.message : "We couldn't load matching profiles right now."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [profile, mode, language, minimumExperience, specialty, minimumRating]);

  return (
    <motion.section className="directory-panel" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} aria-labelledby="directory-title">
      <div className="directory-heading">
        <div><span className="eyebrow"><span className="eyebrow-dot" /> A NEXT STEP, IF YOU WANT ONE</span><h2 id="directory-title">People who may understand.</h2><p>Matched to topics you chose to share. You decide whether to explore further.</p></div>
        <button className="icon-button" onClick={onClose} aria-label="Close professional support matches"><X size={18} /></button>
      </div>
      <div className="directory-demo-notice" role="note"><span><BadgeCheck size={16} /> Demo directory</span><p>These sample profiles, credentials, ratings, and fees are fictional and unverified. Booking is disabled; do not use these listings to seek care.</p></div>

      <div className="directory-filters" aria-label="Filter sample profiles">
        <span className="filter-label"><SlidersHorizontal size={14} /> Filter examples</span>
        <label>Session mode<select value={mode} onChange={(event) => setMode(event.target.value)}><option value="">Any mode</option><option value="online">Online</option><option value="in_person">In person</option></select></label>
        <label>Language<select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="">Any language</option><option>English</option><option>Hindi</option><option>Tamil</option><option>Bengali</option><option>Malayalam</option></select></label>
        <label>Experience<select value={minimumExperience} onChange={(event) => setMinimumExperience(event.target.value)}><option value="0">Any experience</option><option value="5">5+ years</option><option value="10">10+ years</option></select></label>
        <label>Specialty<select value={specialty} onChange={(event) => setSpecialty(event.target.value)}><option value="">Any specialty</option><option value="Academic stress">Academic stress</option><option value="Anxiety">Anxiety</option><option value="CBT">CBT</option><option value="Burnout">Burnout</option><option value="Sleep">Sleep health</option><option value="Trauma">Trauma-informed</option></select></label>
        <label>Rating<select value={minimumRating} onChange={(event) => setMinimumRating(event.target.value)}><option value="0">Any rating</option><option value="4.7">4.7+</option><option value="4.9">4.9+</option></select></label>
      </div>

      {loading && <div className="directory-status" role="status"><span className="send-spinner" /> Finding relevant examples...</div>}
      {error && <p className="directory-error" role="alert">{error}</p>}
      {!loading && results?.safety_first && <p className="directory-safety">Immediate human support is more appropriate than routine matching right now. Please use the SOS resources.</p>}
      {!loading && results && !results.safety_first && results.doctors.length === 0 && <p className="directory-status">No sample profiles match those filters. Try widening your search.</p>}

      <AnimatePresence mode="popLayout">
        {!loading && results?.doctors.map((therapist, index) => (
          <motion.article className="therapist-card" key={therapist.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ delay: index * 0.05 }}>
            <div className={`therapist-avatar therapist-avatar-${index % 5}`} aria-hidden="true">{therapist.display_name.split(" ").slice(0, 2).map((part) => part[0]).join("")}</div>
            <div className="therapist-details">
              <div className="therapist-name-row"><div><span className="demo-label">SAMPLE PROFILE</span><h3>{therapist.display_name}</h3></div><span className="therapist-rating"><Star size={14} fill="currentColor" /> {therapist.rating.toFixed(1)} <small>({therapist.review_count})</small></span></div>
              <p className="therapist-headline">{therapist.headline}</p>
              <p className="therapist-credentials">{therapist.credentials}</p>
              <p className="therapist-bio">{therapist.bio}</p>
              <div className="therapist-meta"><span><BriefcaseBusiness size={14} /> {therapist.years_experience} years</span><span><Languages size={14} /> {therapist.languages.join(", ")}</span><span>{therapist.session_modes.includes("online") ? <Video size={14} /> : <MapPin size={14} />} {therapist.session_modes.map((item) => item === "in_person" ? "In person" : "Online").join(" / ")}</span></div>
              <div className="therapist-tags">{therapist.specialties.slice(0, 3).map((specialty) => <span key={specialty}>{specialty}</span>)}</div>
            </div>
            <div className="therapist-action"><strong>INR {therapist.session_fee_inr.toLocaleString("en-IN")}</strong><small>sample fee</small>{therapist.is_verified && therapist.booking_url ? <a href={therapist.booking_url} target="_blank" rel="noreferrer"><CalendarClock size={15} /> Book consultation</a> : <button disabled title="Demo listings cannot be booked"><CalendarClock size={15} /> Booking unavailable</button>}</div>
            <div className="match-reasons"><ArrowUpRight size={13} /> {therapist.match_reasons.join(" / ")}</div>
          </motion.article>
        ))}
      </AnimatePresence>
      {results && <p className="directory-disclaimer">{results.note} A real provider directory requires independently verified credentials, current availability, and a functioning booking workflow.</p>}
    </motion.section>
  );
}