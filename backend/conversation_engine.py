"""Small, transparent conversation support rules; not a diagnostic model."""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

from ai_engine import analyze_text, is_distress_text


ISSUE_PATTERNS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("trauma", ("trauma", "flashback", "nightmare", "unsafe", "abuse"), ("trauma_support", "feeling_safe")),
    ("sleep", ("sleep", "insomnia", "can't fall asleep", "cant sleep", "waking up", "nightmares"), ("sleep", "rest")),
    ("academic_stress", ("exam", "exams", "assignment", "deadline", "school", "college", "grades", "study"), ("exam_stress", "academic_pressure")),
    ("burnout", ("burnout", "burnt out", "burned out", "exhausted", "too much work", "overworked"), ("burnout", "workload")),
    ("anxiety", ("anxious", "anxiety", "panic", "worry", "worried", "racing thoughts", "on edge"), ("anxiety", "worry")),
    ("low_mood", ("depressed", "hopeless", "empty", "nothing matters", "low mood", "sad all"), ("low_mood", "low_energy")),
)


REFLECTIONS = {
    "trauma": "It sounds like you have been carrying something difficult. You do not need to share details here; we can stay with what might help you feel safer today.",
    "sleep": "When sleep is unsettled, the rest of life can feel harder too. Has something been making it difficult to wind down lately?",
    "academic_stress": "Study pressure can pile up quickly. Which part feels heaviest right now: the workload, expectations, or something else?",
    "burnout": "It sounds like a lot has been asked of you. What has been taking the most out of you lately?",
    "anxiety": "Worry sounds like it has been taking up a lot of space. When does it tend to feel strongest for you?",
    "low_mood": "That sounds heavy to sit with. What has felt hardest to get through today?",
    "general": "Thank you for sharing that with me. What would feel most helpful to talk through right now?",
}

HESITATION_PATTERN = re.compile(r"\b(?:i don't know|i dont know|idk|not sure|i'm not sure|im not sure|maybe)\b", re.I)

FOLLOW_UPS = {
    "trauma": (
        "What would help you feel a little safer in this moment?",
        "Would you rather focus on what could help today, without going into the details?",
        "Is there someone you trust who helps you feel grounded?",
    ),
    "sleep": (
        "What tends to be on your mind when you are trying to rest?",
        "Has anything changed in your routine around bedtime recently?",
        "Would you rather explore a small wind-down idea or talk about what is keeping you up?",
    ),
    "academic_stress": (
        "Which part feels heaviest today: getting started, keeping up, or the pressure of results?",
        "Is there one deadline that feels most urgent right now?",
        "Would it help to break one piece of the workload into a smaller next step?",
    ),
    "burnout": (
        "What has been asking the most of you lately?",
        "Is there anything you could give yourself permission to pause today?",
        "Would rest, practical help, or simply being heard feel most useful right now?",
    ),
    "anxiety": (
        "When does the worry tend to get loudest for you?",
        "Is there something specific your mind keeps returning to?",
        "Would you like to talk about what is worrying you, or try a grounding moment first?",
    ),
    "low_mood": (
        "What has felt hardest to carry today?",
        "Has anything, even something small, felt a little easier recently?",
        "Would talking about today or thinking about one gentle next step feel better?",
    ),
    "general": (
        "What part of that feels most present for you right now?",
        "Would you like to tell me a little more, or think about what might help next?",
        "What feels like the kindest place to start?",
    ),
}

HESITATION_REPLIES = (
    "That's okay. You don't have to know yet, and there is no right answer. Would it feel easier to pause for a moment, or choose one small thing that might help in the next hour?",
    "Not knowing is completely okay. We can take this one step at a time. Would you rather stay with how it feels, or think about one small next step?",
    "You don't have to figure it all out here. Sometimes being unsure is a good enough place to start. What feels more manageable right now: a pause, or talking a little more?",
)

NEXT_STEPS = {
    "trauma": ["Take a moment to notice one thing that helps you feel grounded", "Consider talking with a trauma-informed professional", "Share only what feels safe to share"],
    "sleep": ["Try a low-pressure wind-down routine", "Notice whether caffeine or screens affect your rest", "A clinician can help if sleep disruption persists"],
    "academic_stress": ["Choose one small task to do next", "Try a short study break with a slower exhale", "Consider asking a trusted person about practical support"],
    "burnout": ["Name one thing that can wait until tomorrow", "Take a short break without needing to earn it", "Consider discussing workload support with someone you trust"],
    "anxiety": ["Try breathing out slowly for longer than you breathe in", "Name five things you can see around you", "Consider reaching out to someone who helps you feel steady"],
    "low_mood": ["Choose one gentle, manageable thing for the next hour", "Consider letting someone you trust know how today feels", "A qualified professional can help you explore ongoing low mood"],
    "general": ["Take one slow breath and notice how your body feels", "Choose one small thing that would make the next hour easier", "Consider checking in with someone you trust"],
}


def extract_conversation_profile(user_messages: list[str]) -> dict[str, Any]:
    text = "\n".join(message.strip() for message in user_messages if message.strip())
    normalized = text.lower()
    matched = [
        (issue, tags)
        for issue, phrases, tags in ISSUE_PATTERNS
        if any(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalized) for phrase in phrases)
    ]
    crisis = is_distress_text(text)
    primary_issue = "crisis_support" if crisis else matched[0][0] if matched else "general"
    keywords = list(dict.fromkeys(tag for _, tags in matched for tag in tags))[:8]
    if crisis:
        keywords = list(dict.fromkeys(["immediate_support", *keywords]))[:8]

    emotion = analyze_text(text) if text else {"dominant_emotion": "neutral", "sentiment_score": 0.0}
    if crisis:
        severity = "high"
    elif len(matched) >= 2 or emotion["sentiment_score"] <= -0.7:
        severity = "moderate"
    elif matched:
        severity = "mild"
    else:
        severity = "low"

    return {
        "primary_issue": primary_issue,
        "severity": severity,
        "keywords": keywords,
        "dominant_emotion": emotion["dominant_emotion"],
        "sentiment_score": emotion["sentiment_score"],
        "crisis_flag": crisis,
    }


def build_chat_reply(
    profile: dict[str, Any],
    user_turn_count: int,
    request_summary: bool,
    latest_user_message: str = "",
) -> dict[str, Any]:
    if profile["crisis_flag"]:
        return {
            "assistant_message": (
                "I'm really glad you told me. I can't assess immediate danger over chat. If you may act on these thoughts "
                "or cannot stay safe, contact local emergency services now or go to the nearest emergency department. "
                "In India, call 112 or Tele-MANAS at 14416. Is there someone nearby you trust who can stay with you?"
            ),
            "wellness_summary": None,
            "recommendation_ready": False,
            "safety_resources_recommended": True,
        }

    issue = profile["primary_issue"]
    follow_ups = FOLLOW_UPS.get(issue, FOLLOW_UPS["general"])
    if HESITATION_PATTERN.search(latest_user_message):
        assistant_message = HESITATION_REPLIES[(user_turn_count - 1) % len(HESITATION_REPLIES)]
    else:
        reflection = REFLECTIONS.get(issue, REFLECTIONS["general"])
        follow_up = follow_ups[(user_turn_count - 1) % len(follow_ups)]
        acknowledgment = reflection.split("?")[0].rstrip(". ") + "."
        assistant_message = f"{acknowledgment} {follow_up}"
    summary_requested = request_summary or user_turn_count >= 2
    summary = None
    if summary_requested:
        themes = [issue.replace("_", " ")] if issue != "general" else ["what has been on your mind"]
        summary = {
            "headline": "A gentle reflection",
            "themes": themes,
            "emotion": profile["dominant_emotion"],
            "reflection": "You have shared that " + themes[0] + " has been part of your week. This is only a reflection of your words, not a clinical assessment.",
            "next_steps": NEXT_STEPS.get(issue, NEXT_STEPS["general"]),
        }
    return {
        "assistant_message": assistant_message,
        "wellness_summary": summary,
        "recommendation_ready": bool(summary and issue != "general"),
        "safety_resources_recommended": False,
    }


async def generate_assistant_message(
    messages: list[dict[str, str]],
    fallback_message: str,
    crisis_flag: bool,
) -> tuple[str, str, str]:
    if crisis_flag:
        return (
            fallback_message,
            "safety_template",
            "This safety reply was generated locally. Chat messages are not saved as a transcript.",
        )

    endpoint = os.getenv("CONVERSATION_MODEL_URL", "").strip()
    api_key = os.getenv("CONVERSATION_MODEL_API_KEY", "").strip()
    model = os.getenv("CONVERSATION_MODEL_NAME", "").strip()
    if not endpoint or not model:
        return (
            fallback_message,
            "local_rules",
            "This reply uses local topic-matching rules. Chat messages are not saved as a transcript.",
        )

    system_prompt = (
        "You are a warm, non-judgmental wellness reflection companion, not a therapist, doctor, or emergency service. "
        "Reply in 2 to 4 short sentences. First acknowledge the feeling in plain language, then ask at most one gentle, "
        "open question. Do not diagnose, assign severity, invent facts, prescribe treatment, or claim a person is monitoring "
        "the chat. Respect boundaries and never pressure someone to disclose more. If the person may be in danger, tell them "
        "to contact local emergency services and a trusted nearby person; do not imply this chat can keep them safe."
    )
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=4.0)) as client:
            response = await client.post(
                endpoint,
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "system", "content": system_prompt}, *messages[-12:]],
                    "temperature": 0.55,
                    "max_tokens": 180,
                },
            )
            response.raise_for_status()
            generated = response.json()["choices"][0]["message"]["content"].strip()
            if not generated or len(generated) > 1600:
                raise ValueError("Model reply was empty or too long")
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return (
            fallback_message,
            "local_rules_fallback",
            "The configured model was unavailable; a local topic-matching reply was used. Messages are not saved as a transcript.",
        )
    return (
        generated,
        "configured_model",
        "This reply was generated by the configured language-model provider. Your chat messages were sent to that provider and are not saved by MindPulse.",
    )