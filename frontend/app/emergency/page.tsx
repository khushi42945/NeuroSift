import Link from "next/link";
import { ArrowLeft, ArrowUpRight, Clock3, HeartHandshake, Phone, Siren } from "lucide-react";

const resources = [
  {
    name: "Tele-MANAS",
    label: "Government of India, 24/7 mental health support",
    phone: "14416",
    dial: "14416",
    detail: "Free, confidential mental health support and referral to services across India.",
    tone: "resource-green",
  },
  {
    name: "Vandrevala Foundation",
    label: "Mental health crisis support in India",
    phone: "+91 9999 666 555",
    dial: "+919999666555",
    detail: "Call or WhatsApp for emotional support. Check the official site for current hours and options.",
    tone: "resource-coral",
  },
  {
    name: "iCALL",
    label: "Tata Institute of Social Sciences counselling service",
    phone: "+91 91529 87821",
    dial: "+919152987821",
    detail: "Counselling and information by phone and email. Service hours may change; check the official site.",
    tone: "resource-blue",
  },
];

export default function EmergencyPage() {
  return (
    <div className="page-wrap support-page">
      <Link className="back-link" href="/dashboard"><ArrowLeft size={16} /> Back to your week</Link>
      <section className="support-heading">
        <span className="eyebrow coral-text"><span className="eyebrow-dot coral-dot" /> SUPPORT, WHEN YOU NEED IT</span>
        <h1>Someone is here<br /><em>to listen.</em></h1>
        <p>You deserve real support from a real person. Choose an option that feels comfortable for you.</p>
      </section>
      <section className="urgent-band" aria-labelledby="urgent-title">
        <div className="urgent-icon"><Siren size={22} /></div>
        <div className="urgent-copy"><h2 id="urgent-title">In immediate danger?</h2><p>If you or someone else may be in immediate danger, call local emergency services or go to the nearest emergency department. In India, call 112.</p></div>
        <a className="urgent-call" href="tel:112"><Phone size={17} /> Call 112</a>
      </section>
      <div className="support-section-heading"><span>INDIA-BASED SUPPORT</span><span>Always check current availability</span></div>
      <section className="resource-list" aria-label="Mental health support services">
        {resources.map((resource, index) => (
          <article className="resource-row" key={resource.name}>
            <span className={`resource-index ${resource.tone}`}>0{index + 1}</span>
            <div className="resource-main"><h2>{resource.name}</h2><span className="resource-label">{resource.label}</span><p>{resource.detail}</p></div>
            <a className="resource-phone" href={`tel:${resource.dial}`} aria-label={`Call ${resource.name} at ${resource.phone}`}><Phone size={16} />{resource.phone}</a>
          </article>
        ))}
      </section>
      <section className="therapist-band">
        <div className="therapist-icon"><HeartHandshake size={21} /></div>
        <div><span className="eyebrow">ONGOING CARE</span><h2>Looking for a counsellor or therapist?</h2><p>iCALL can help you explore counselling options. Tele-MANAS can also guide you toward local mental health services.</p><div className="referral-links"><a href="https://icallhelpline.org/" target="_blank" rel="noreferrer">iCALL service information <ArrowUpRight size={15} /></a><a href="https://telemanas.mohfw.gov.in/" target="_blank" rel="noreferrer">Tele-MANAS <ArrowUpRight size={15} /></a></div></div>
      </section>
      <p className="support-footnote"><Clock3 size={14} /> If you are outside India, contact your local crisis line or emergency service. Numbers, eligibility, and service hours can change; verify details with each organization.</p>
    </div>
  );
}