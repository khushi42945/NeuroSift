"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, Heart, ShieldCheck } from "lucide-react";
import { ApiError, api, getToken } from "@/lib/api";
import { CrisisModal } from "@/components/crisis-modal";

const options = ["Not at all", "Several days", "More than half the days", "Nearly every day"];
const questionSets = {
  "PHQ-9": [
    "Little interest or pleasure in doing things",
    "Feeling down, depressed, or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself, or that you are a failure or have let yourself or your family down",
    "Trouble concentrating on things, such as reading or watching television",
    "Moving or speaking so slowly that other people could have noticed, or being unusually fidgety or restless",
    "Thoughts that you would be better off dead, or of hurting yourself in some way",
  ],
  "GAD-7": [
    "Feeling nervous, anxious, or on edge",
    "Not being able to stop or control worrying",
    "Worrying too much about different things",
    "Trouble relaxing",
    "Being so restless that it is hard to sit still",
    "Becoming easily annoyed or irritable",
    "Feeling afraid, as if something awful might happen",
  ],
};

type AssessmentResult = { total_score: number; severity_category: string; crisis_flag: boolean; support_resources_recommended: boolean; recommendation: string; disclaimer: string };

export default function AssessmentPage() {
  const router = useRouter();
  const [type, setType] = useState<keyof typeof questionSets>("PHQ-9");
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<number[]>([]);
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [crisisOpen, setCrisisOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const questions = questionSets[type];
  const runningScore = answers.reduce((total, answer) => total + answer, 0);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/auth");
      return;
    }
    const selected = new URLSearchParams(window.location.search).get("type");
    if (selected === "GAD-7" || selected === "PHQ-9") setType(selected);
  }, [router]);

  function changeType(next: keyof typeof questionSets) {
    setType(next);
    setStep(0);
    setAnswers([]);
    setResult(null);
    setError("");
  }

  async function finishAssessment(nextAnswers: number[]) {
    setBusy(true);
    setError("");
    try {
      const nextResult = await api<AssessmentResult>(`/api/assess/${type.replace("-", "").toLowerCase()}`, {
        method: "POST",
        body: JSON.stringify({ assessment_type: type, answers: nextAnswers }),
      });
      setResult(nextResult);
      if (nextResult.crisis_flag || nextResult.support_resources_recommended && ["Severe", "Moderately Severe"].includes(nextResult.severity_category)) setCrisisOpen(true);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) router.replace("/auth");
      else setError(cause instanceof Error ? cause.message : "Your answers could not be submitted.");
    } finally {
      setBusy(false);
    }
  }

  function answerQuestion(value: number) {
    const updated = [...answers];
    updated[step] = value;
    setAnswers(updated);
    if (step === questions.length - 1) void finishAssessment(updated);
    else setStep(step + 1);
  }

  return (
    <div className="assessment-page page-wrap">
      <Link className="back-link" href="/dashboard"><ArrowLeft size={16} /> Back to your week</Link>
      <div className="assessment-frame">
        <div className="assessment-aside"><span className="eyebrow"><span className="eyebrow-dot" /> YOUR CHOICE, ALWAYS</span><h1>A check-in,<br /><em>not a label.</em></h1><p>These questions are used in standard screening tools. Your answers can help you notice a pattern, but they cannot diagnose anything.</p><div className="aside-rule" /><div className="aside-note"><ShieldCheck size={18} /><span>Your answers are private and visible only to you.</span></div><div className="aside-note"><Heart size={18} /><span>You can pause or leave at any time.</span></div></div>
        <section className="question-panel" aria-live="polite">
          {result ? <div className="result-view"><span className="result-check"><Check size={22} /></span><span className="eyebrow">SCREENING COMPLETE</span><h2>Your score is {result.total_score}.</h2><div className="severity-badge">{result.severity_category} range</div><p>{result.recommendation}</p><p className="result-disclaimer">{result.disclaimer}</p><div className="result-actions"><button className="button button-primary" onClick={() => { setResult(null); setAnswers([]); setStep(0); }}>Take another check-in <ArrowRight size={16} /></button><Link className="button button-outline" href="/dashboard">Return to your week</Link></div></div> : <>
            <div className="type-switch" role="group" aria-label="Screening type"><button className={type === "PHQ-9" ? "type-button chosen" : "type-button"} onClick={() => changeType("PHQ-9")}>PHQ-9 <span>Mood</span></button><button className={type === "GAD-7" ? "type-button chosen" : "type-button"} onClick={() => changeType("GAD-7")}>GAD-7 <span>Anxiety</span></button></div>
            <div className="progress-head"><span>QUESTION {step + 1} OF {questions.length}</span><span>Score so far: {runningScore}</span></div><div className="progress-track"><span style={{ width: `${((step + 1) / questions.length) * 100}%` }} /></div>
            <span className="question-window">Over the last 2 weeks, how often have you been bothered by:</span><h2 className="question-text">{questions[step]}?</h2>
            {step === 8 && type === "PHQ-9" && <p className="safety-note" role="note">If you may be in immediate danger, pause and reach out to local emergency services or someone you trust.</p>}
            <div className="answer-list" role="group" aria-label="Choose how often">
              {options.map((option, index) => <button key={option} className="answer-option" disabled={busy} onClick={() => answerQuestion(index)}><span className="answer-radio" />{option}<ArrowRight size={15} /></button>)}
            </div>
            {busy && <p className="form-status" role="status">Saving your answers...</p>}
            {error && <p className="form-error" role="alert">{error}</p>}
            <div className="question-footer"><span>Answer for what feels true, not what you think is expected.</span>{step > 0 && <button className="text-button" onClick={() => setStep(step - 1)}>Previous question</button>}</div>
          </>}
        </section>
      </div>
      <CrisisModal open={crisisOpen} onClose={() => setCrisisOpen(false)} />
    </div>
  );
}