"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowDown, ArrowRight, Heart, Mic, RotateCcw, Send, ShieldCheck, Siren, Sparkles, VolumeX } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { CrisisModal } from "@/components/crisis-modal";
import { DoctorDirectory } from "@/components/DoctorDirectory";

type ChatTurn = { role: "user" | "assistant"; content: string };
type ConversationProfile = {
  primary_issue: string;
  severity: "low" | "mild" | "moderate" | "high";
  keywords: string[];
  dominant_emotion: string;
  sentiment_score?: number;
  crisis_flag: boolean;
};
type WellnessSummary = { headline: string; themes: string[]; emotion: string; reflection: string; next_steps: string[] };
type ChatResponse = {
  session_id: string;
  assistant_message: string;
  wellness_summary: WellnessSummary | null;
  recommendation_ready: boolean;
  safety_resources_recommended: boolean;
  profile: ConversationProfile;
  reply_source: string;
  processing_notice: string;
};

const STARTER_MESSAGE: ChatTurn = {
  role: "assistant",
  content: "Hi, I'm here with you. You can start anywhere. What's been taking up the most space in your mind lately?",
};
const QUICK_REPLIES = ["Feeling burnt out", "Can't sleep", "Overwhelmed with exams"];

type SpeechRecognitionResultLike = { 0: { transcript: string } };
type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<SpeechRecognitionResultLike> }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};
type SpeechWindow = Window & {
  SpeechRecognition?: new () => SpeechRecognitionLike;
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
};

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatTurn[]>([STARTER_MESSAGE]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [typing, setTyping] = useState(false);
  const [error, setError] = useState("");
  const [processingNotice, setProcessingNotice] = useState("");
  const [profile, setProfile] = useState<ConversationProfile | null>(null);
  const [summary, setSummary] = useState<WellnessSummary | null>(null);
  const [summaryRequested, setSummaryRequested] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [crisisOpen, setCrisisOpen] = useState(false);
  const [directoryOpen, setDirectoryOpen] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const transcriptEnd = useRef<HTMLDivElement>(null);
  const recognition = useRef<SpeechRecognitionLike | null>(null);
  const userTurnCount = messages.filter((message) => message.role === "user").length;

  useEffect(() => {
    const speechWindow = window as SpeechWindow;
    setVoiceSupported(Boolean(speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition));
  }, []);

  useEffect(() => {
    transcriptEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, typing]);

  async function sendMessage(content: string, requestSummary = false) {
    const cleanContent = content.trim();
    if (!cleanContent || busy) return;
    const nextMessages: ChatTurn[] = [...messages, { role: "user", content: cleanContent }];
    setMessages(nextMessages);
    setDraft("");
    setBusy(true);
    setTyping(true);
    setError("");
    try {
      const response = await api<ChatResponse>("/api/chat", {
        method: "POST",
        body: JSON.stringify({ messages: nextMessages.slice(-24), request_summary: requestSummary, session_id: sessionId }),
      });
      setSessionId(response.session_id);
      setProfile(response.profile);
      setSummary(response.wellness_summary);
      setProcessingNotice(response.processing_notice);
      setMessages([...nextMessages, { role: "assistant", content: response.assistant_message }]);
      if (response.safety_resources_recommended) setCrisisOpen(true);
    } catch (cause) {
      setMessages(nextMessages);
      setError(cause instanceof ApiError ? cause.message : "I couldn't connect just now. Your message has not been saved. Please try again.");
    } finally {
      setTyping(false);
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(draft);
  }

  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage(draft);
    }
  }

  function startVoiceInput() {
    const speechWindow = window as SpeechWindow;
    const Recognition = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
    if (!Recognition) return;
    recognition.current?.stop();
    const instance = new Recognition();
    instance.lang = "en-IN";
    instance.interimResults = false;
    instance.onresult = (event) => setDraft((current) => `${current}${current ? " " : ""}${event.results[0][0].transcript}`);
    instance.onerror = () => { setListening(false); setError("Voice input was unavailable. You can type instead."); };
    instance.onend = () => setListening(false);
    recognition.current = instance;
    setListening(true);
    instance.start();
  }

  function resetConversation() {
    recognition.current?.stop();
    setMessages([STARTER_MESSAGE]);
    setProfile(null);
    setSummary(null);
    setSummaryRequested(false);
    setSessionId(undefined);
    setDirectoryOpen(false);
    setError("");
  }

  function requestReflection() {
    setSummaryRequested(true);
    void sendMessage("Could you reflect back what you've heard so far?", true);
  }

  const moodTone = profile?.dominant_emotion ?? "calm";

  return (
    <div className={`companion-shell tone-${moodTone}`}>
      <header className="companion-heading">
        <div className="companion-title-group">
          <div className="companion-avatar" aria-hidden="true"><Heart size={20} /></div>
          <div><span className="eyebrow companion-eyebrow"><span className="eyebrow-dot" /> YOUR WELLNESS COMPANION</span><h1>A little space to talk.</h1></div>
        </div>
        <div className="companion-heading-actions">
          <span className="privacy-pill"><ShieldCheck size={14} /> Private conversation</span>
          <button className="icon-button reset-chat" onClick={resetConversation} aria-label="Start a new conversation" title="Start a new conversation"><RotateCcw size={17} /></button>
        </div>
      </header>

      <div className="companion-grid">
        <section className="chat-panel" aria-label="Conversation with your wellness companion">
          <div className="chat-context"><Sparkles size={15} /><span>A gentle check-in. No forms, no labels, no pressure to share more than you want.</span></div>
          <div className="message-list" aria-live="polite" aria-relevant="additions text">
            <AnimatePresence initial={false}>
              {messages.map((message, index) => (
                <motion.div
                  key={`${index}-${message.role}`}
                  className={`message-row ${message.role === "user" ? "message-user" : "message-companion"}`}
                  initial={{ opacity: 0, y: 12, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.24, ease: "easeOut" }}
                  layout
                >
                  {message.role === "assistant" && <span className="message-avatar"><Heart size={13} /></span>}
                  <div className="message-bubble"><p>{message.content}</p><time>{message.role === "assistant" ? "Companion" : "You"}</time></div>
                </motion.div>
              ))}
            </AnimatePresence>
            <AnimatePresence>
              {typing && <motion.div className="message-row message-companion" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <span className="message-avatar"><Heart size={13} /></span>
                <div className="typing-bubble" role="status" aria-label="Companion is thinking"><i /><i /><i /></div>
              </motion.div>}
            </AnimatePresence>
            <div ref={transcriptEnd} />
          </div>

          {messages.length === 1 && <div className="quick-replies" aria-label="Suggested conversation starters">
            <span className="quick-replies-label">You could start with</span>
            {QUICK_REPLIES.map((reply) => <button key={reply} className="quick-reply" disabled={busy} onClick={() => void sendMessage(reply)}>{reply}<ArrowRight size={13} /></button>)}
          </div>}

          {error && <p className="chat-error" role="alert">{error}</p>}
          <form className="chat-composer" onSubmit={submit}>
            <label className="sr-only" htmlFor="companion-message">Write a message to your companion</label>
            <textarea id="companion-message" value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={onComposerKeyDown} maxLength={2000} rows={2} placeholder="Share whatever feels okay..." disabled={busy} />
            <div className="composer-toolbar">
              <div className="composer-hints"><span><LockIcon /> No transcript is saved by MindPulse.</span>{voiceSupported && <span className="voice-hint"><VolumeX size={13} /> Voice is processed by your browser.</span>}</div>
              <div className="composer-actions">
                {voiceSupported && <button className={`voice-button ${listening ? "voice-active" : ""}`} type="button" onClick={startVoiceInput} aria-label={listening ? "Listening for speech" : "Use voice input"} title="Use voice input"><Mic size={16} /></button>}
                <button className="send-button" type="submit" disabled={busy || !draft.trim()} aria-label="Send message">{busy ? <span className="send-spinner" /> : <Send size={16} />}</button>
              </div>
            </div>
          </form>
          <p className="processing-notice" role="note">{processingNotice || "MindPulse does not save a chat transcript. If a hosted language model is configured, messages are sent to that provider for a reply."}</p>
          <p className="chat-disclaimer">MindPulse offers supportive reflection, not diagnosis or emergency monitoring. If you may be in immediate danger, use the SOS resources.</p>
        </section>

        <aside className="companion-side">
          <section className="side-note-card mood-card">
            <span className="side-card-icon"><Sparkles size={16} /></span>
            <span className="eyebrow">A SMALL REFLECTION</span>
            <h2>{profile ? `You sound ${profile.dominant_emotion}.` : "You set the pace."}</h2>
            <p>{profile ? "This is a language pattern, not a diagnosis. It may not capture how you feel." : "There is no score to reach. You can pause, change the subject, or leave whenever you like."}</p>
            {profile && <span className="pattern-tag">Topic: {profile.primary_issue.replaceAll("_", " ")}</span>}
          </section>

          <AnimatePresence>
            {summary && <motion.section className="wellness-summary" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <span className="eyebrow"><Sparkles size={13} /> {summary.headline}</span>
              <h2>What I'm hearing</h2>
              <p>{summary.reflection}</p>
              <div className="summary-themes">{summary.themes.map((theme) => <span key={theme}>{theme}</span>)}</div>
              <strong>Gentle next steps</strong>
              <ul>{summary.next_steps.map((step) => <li key={step}>{step}</li>)}</ul>
              <p className="summary-footnote">Only a reflection of this chat. It is not a clinical assessment.</p>
            </motion.section>}
          </AnimatePresence>

          {userTurnCount >= 1 && !summary && !summaryRequested && !profile?.crisis_flag && <button className="reflection-button" disabled={busy} onClick={requestReflection}><Sparkles size={16} /> Reflect back what you've shared <ArrowRight size={15} /></button>}

          {summary && profile && profile.primary_issue !== "general" && !profile.crisis_flag && <button className="find-specialist-button" onClick={() => setDirectoryOpen((current) => !current)} aria-expanded={directoryOpen}><Heart size={16} />{directoryOpen ? "Hide specialist matches" : "Explore professional support"}<ArrowDown className={directoryOpen ? "arrow-rotated" : ""} size={15} /></button>}
        </aside>
      </div>

      {directoryOpen && profile && <DoctorDirectory profile={profile} onClose={() => setDirectoryOpen(false)} />}

      <button className="sos-float" onClick={() => setCrisisOpen(true)} aria-label="Open immediate support resources"><Siren size={17} /><span>Need urgent support?</span></button>
      <CrisisModal open={crisisOpen} onClose={() => setCrisisOpen(false)} />
    </div>
  );
}

function LockIcon() {
  return <ShieldCheck size={13} aria-hidden="true" />;
}