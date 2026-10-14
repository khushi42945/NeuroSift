from sqlalchemy import select
from sqlalchemy.orm import Session

from models import TherapistProfile


DEMO_PROFILES = [
    {
        "display_name": "Aanya Sen (Demo)",
        "credentials": "Sample profile; credentials not verified",
        "headline": "Youth anxiety and academic stress",
        "specialties": ["Anxiety", "Academic stress", "CBT"],
        "focus_areas": ["anxiety", "academic_stress", "exam_stress", "worry"],
        "years_experience": 8,
        "session_fee_inr": 1200,
        "languages": ["English", "Hindi", "Bengali"],
        "session_modes": ["online", "in_person"],
        "rating": 4.8,
        "review_count": 42,
        "bio": "Example profile focused on practical coping skills for study pressure, worry, and transitions into working life.",
    },
    {
        "display_name": "Kabir Rao (Demo)",
        "credentials": "Sample profile; credentials not verified",
        "headline": "Burnout, boundaries, and work stress",
        "specialties": ["Burnout", "Work stress", "Mindfulness"],
        "focus_areas": ["burnout", "workload", "anxiety", "low_energy"],
        "years_experience": 11,
        "session_fee_inr": 1600,
        "languages": ["English", "Hindi", "Kannada"],
        "session_modes": ["online"],
        "rating": 4.9,
        "review_count": 67,
        "bio": "Example profile centered on sustainable routines, work boundaries, and recovery from prolonged stress.",
    },
    {
        "display_name": "Mira Thomas (Demo)",
        "credentials": "Sample profile; credentials not verified",
        "headline": "Sleep and anxiety support",
        "specialties": ["Sleep health", "Anxiety", "CBT-I"],
        "focus_areas": ["sleep", "rest", "anxiety", "worry"],
        "years_experience": 6,
        "session_fee_inr": 1000,
        "languages": ["English", "Malayalam", "Tamil"],
        "session_modes": ["online", "in_person"],
        "rating": 4.7,
        "review_count": 31,
        "bio": "Example profile for people exploring sleep routines, nighttime worry, and ways to feel more settled.",
    },
    {
        "display_name": "Leela Fernandes (Demo)",
        "credentials": "Sample profile; credentials not verified",
        "headline": "Trauma-informed and identity-affirming care",
        "specialties": ["Trauma-informed care", "Life transitions", "LGBTQIA+ affirming"],
        "focus_areas": ["trauma", "trauma_support", "feeling_safe", "low_mood"],
        "years_experience": 13,
        "session_fee_inr": 1800,
        "languages": ["English", "Konkani", "Hindi"],
        "session_modes": ["online"],
        "rating": 4.9,
        "review_count": 58,
        "bio": "Example profile emphasizing choice, pacing, and emotional safety during difficult life experiences.",
    },
    {
        "display_name": "Devika Iyer (Demo)",
        "credentials": "Sample profile; credentials not verified",
        "headline": "Low mood, confidence, and life changes",
        "specialties": ["Low mood", "Self-esteem", "Young adults"],
        "focus_areas": ["low_mood", "low_energy", "academic_stress", "anxiety"],
        "years_experience": 9,
        "session_fee_inr": 1400,
        "languages": ["English", "Tamil", "Telugu"],
        "session_modes": ["online", "in_person"],
        "rating": 4.6,
        "review_count": 39,
        "bio": "Example profile for young adults navigating low mood, confidence changes, and demanding transitions.",
    },
]


def seed_demo_profiles(db: Session) -> None:
    if db.scalar(select(TherapistProfile.id).where(TherapistProfile.is_demo.is_(True)).limit(1)):
        return
    db.add_all(TherapistProfile(**profile, is_demo=True, is_verified=False) for profile in DEMO_PROFILES)
    db.commit()