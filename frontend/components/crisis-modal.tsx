"use client";

import { useEffect } from "react";
import { ArrowUpRight, X } from "lucide-react";

export function CrisisModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="dialog-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="crisis-dialog" role="alertdialog" aria-modal="true" aria-labelledby="crisis-title" aria-describedby="crisis-description">
        <button className="dialog-close" onClick={onClose} aria-label="Close support options"><X size={19} /></button>
        <span className="eyebrow coral-text">You deserve support</span>
        <h2 id="crisis-title">You do not have to face this alone.</h2>
        <p id="crisis-description">If you may be in immediate danger, call your local emergency number or go to the nearest emergency department. In India, call 112.</p>
        <div className="dialog-resource">
          <div><strong>Tele-MANAS</strong><span>India, 24/7 mental health support</span></div>
          <a href="tel:14416">14416 <ArrowUpRight size={14} /></a>
        </div>
        <div className="dialog-resource">
          <div><strong>Vandrevala Foundation</strong><span>India, mental health crisis support</span></div>
          <a href="tel:+919999666555">Call <ArrowUpRight size={14} /></a>
        </div>
        <a className="dialog-secondary" href="/emergency">See all support options <ArrowUpRight size={15} /></a>
      </section>
    </div>
  );
}