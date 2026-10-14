"""Deterministic screening scores and optional journal emotion analysis.

Screening results support reflection and are not a diagnosis or substitute for
care from a qualified professional.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from functools import lru_cache
from typing import Any


PHQ9_LABELS = (
    "Not at all",
    "Several days",
    "More than half the days",
    "Nearly every day",
)

PHQ9_QUESTIONS = (
    "Little interest or pleasure in doing things",
    "Feeling down, depressed, or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself, or that you are a failure or have let yourself or your family down",
    "Trouble concentrating on things, such as reading or watching television",
    "Moving or speaking so slowly that other people could have noticed, or being unusually fidgety or restless",
    "Thoughts that you would be better off dead, or of hurting yourself in some way",
)

GAD7_QUESTIONS = (
    "Feeling nervous, anxious, or on edge",
    "Not being able to stop or control worrying",
    "Worrying too much about different things",
    "Trouble relaxing",
    "Being so restless that it is hard to sit still",
    "Becoming easily annoyed or irritable",
    "Feeling afraid, as if something awful might happen",
)

_DISTRESS_PATTERNS = (
    re.compile(r"\b(?:suicid(?:e|al)|kill myself|end my life|take my own life)\b", re.I),
    re.compile(r"\b(?:hurt|harm|cut) myself\b", re.I),
    re.compile(r"\b(?:can't|cannot|do not|don't) go on\b", re.I),
    re.compile(r"\b(?:want|wish|hope)\s+(?:i\s+)?(?:could\s+)?(?:just\s+)?(?:die|be dead|not wake up|not be alive)\b", re.I),
    re.compile(r"\b(?:better off dead|wish i was dead|wish i were dead|don't want to live)\b", re.I),
)

_EMOTION_WORDS = {
    "sadness": {"sad", "hopeless", "empty", "lonely", "down", "grief", "depressed"},
    "anxiety": {"anxious", "worried", "panic", "nervous", "overwhelmed", "afraid"},
    "anger": {"angry", "frustrated", "irritated", "furious", "annoyed"},
    "joy": {"happy", "grateful", "joyful", "excited", "content", "hopeful"},
    "calm": {"calm", "peaceful", "relaxed", "safe", "steady"},
}
_POSITIVE_WORDS = _EMOTION_WORDS["joy"] | _EMOTION_WORDS["calm"] | {"good", "better", "well", "love"}
_NEGATIVE_WORDS = (
    _EMOTION_WORDS["sadness"]
    | _EMOTION_WORDS["anxiety"]
    | _EMOTION_WORDS["anger"]
    | {"bad", "worse", "tired", "stress", "stressed", "difficult", "hard"}
)


def severity_for_phq9(score: int) -> str:
    if score <= 4:
        return "Minimal"
    if score <= 9:
        return "Mild"
    if score <= 14:
        return "Moderate"
    if score <= 19:
        return "Moderately Severe"
    return "Severe"


def severity_for_gad7(score: int) -> str:
    if score <= 4:
        return "Minimal"
    if score <= 9:
        return "Mild"
    if score <= 14:
        return "Moderate"
    return "Severe"


def is_distress_text(text: str) -> bool:
    return any(pattern.search(text) for pattern in _DISTRESS_PATTERNS)


def score_assessment(assessment_type: str, answers: list[int]) -> dict[str, Any]:
    kind = assessment_type.upper()
    expected_count = 9 if kind == "PHQ-9" else 7 if kind == "GAD-7" else 0
    if not expected_count:
        raise ValueError("assessment_type must be PHQ-9 or GAD-7")
    if len(answers) != expected_count or any(answer not in range(4) for answer in answers):
        raise ValueError(f"{kind} requires {expected_count} answers from 0 to 3")

    total = sum(answers)
    severity = severity_for_phq9(total) if kind == "PHQ-9" else severity_for_gad7(total)
    crisis_flag = kind == "PHQ-9" and answers[8] > 0
    return {
        "assessment_type": kind,
        "total_score": total,
        "severity_category": severity,
        "crisis_flag": crisis_flag,
        "recommendation": (
            "Please connect with immediate, local crisis support. You do not have to manage this alone."
            if crisis_flag
            else "Consider sharing these results with a trusted person or qualified health professional."
            if total >= 10
            else "Small, supportive steps can help. Consider a grounding exercise, regular rest, and checking in with someone you trust."
        ),
    }


@lru_cache(maxsize=1)
def _emotion_pipeline() -> Any | None:
    model = os.getenv("HF_EMOTION_MODEL", "").strip()
    if not model:
        return None
    try:
        from transformers import pipeline

        return pipeline("text-classification", model=model, top_k=None)
    except Exception:
        return None


def analyze_text(text: str) -> dict[str, Any]:
    tokens = re.findall(r"[a-z']+", text.lower())
    counts = Counter(tokens)
    positive = sum(counts[word] for word in _POSITIVE_WORDS)
    negative = sum(counts[word] for word in _NEGATIVE_WORDS)
    valence = (positive - negative) / max(positive + negative, 1)
    emotion_counts = {
        emotion: sum(counts[word] for word in words)
        for emotion, words in _EMOTION_WORDS.items()
    }

    model = _emotion_pipeline()
    if model is not None and text.strip():
        try:
            predictions = model(text[:4000], truncation=True)
            labels = predictions[0] if predictions and isinstance(predictions[0], list) else predictions
            model_emotion = max(labels, key=lambda item: item["score"])["label"].lower()
            emotion = model_emotion if model_emotion in _EMOTION_WORDS else (model_emotion or "neutral")
        except Exception:
            emotion = max(emotion_counts, key=emotion_counts.get) if any(emotion_counts.values()) else "neutral"
    else:
        emotion = max(emotion_counts, key=emotion_counts.get) if any(emotion_counts.values()) else "neutral"

    return {
        "sentiment_score": round(max(-1.0, min(1.0, valence)), 3),
        "dominant_emotion": emotion,
        "crisis_flag": is_distress_text(text),
        "analysis_source": "transformers" if model is not None else "local_fallback",
    }