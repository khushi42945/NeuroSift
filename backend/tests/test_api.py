import os
import unittest
from datetime import timedelta

os.environ.setdefault("AUTO_CREATE_SCHEMA", "false")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import DailyLog, utc_now
from seed_data import seed_demo_profiles


test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


def override_get_db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = override_get_db


class APITests(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=test_engine)
        Base.metadata.create_all(bind=test_engine)
        with TestSession() as session:
            seed_demo_profiles(session)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        Base.metadata.drop_all(bind=test_engine)

    def register(self):
        response = self.client.post(
            "/api/auth/register",
            json={"email": "person@example.com", "password": "a-private-password"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["access_token"]

    def test_register_login_and_guest_identity(self):
        token = self.register()
        headers = {"Authorization": f"Bearer {token}"}
        self.assertEqual(self.client.get("/api/me", headers=headers).status_code, 200)
        self.assertEqual(self.client.post("/api/auth/login", json={
            "email": "PERSON@example.com", "password": "a-private-password",
        }).status_code, 200)
        guest = self.client.post("/api/auth/guest")
        self.assertEqual(guest.status_code, 201)
        guest_token = guest.json()["access_token"]
        self.assertEqual(guest_token.count("."), 4)
        guest_profile = self.client.get("/api/me", headers={"Authorization": f"Bearer {guest_token}"})
        self.assertTrue(guest_profile.json()["is_guest"])
        self.assertIsNone(guest_profile.json()["email"])

    def test_journal_is_analyzed_saved_and_encrypted(self):
        token = self.register()
        response = self.client.post(
            "/api/analyze-entry",
            headers={"Authorization": f"Bearer {token}"},
            json={"text": "I feel hopeless and sad today.", "mood_tag": "Low"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["dominant_emotion"], "sadness")
        with test_engine.connect() as connection:
            stored_text = connection.execute(text("SELECT journal_text FROM daily_logs")).scalar_one()
        self.assertNotIn("hopeless", stored_text)
        logs = self.client.get("/api/logs", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(logs.json()[0]["mood_tag"], "Low")

    def test_explicit_distress_creates_owned_alert(self):
        token = self.register()
        response = self.client.post(
            "/api/analyze-entry",
            headers={"Authorization": f"Bearer {token}"},
            json={"text": "I might hurt myself."},
        )
        self.assertTrue(response.json()["crisis_flag"])
        alerts = self.client.get("/api/risk-alerts", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(alerts.json()[0]["alert_level"], "Red")

    def test_phq9_question_nine_triggers_red_flag(self):
        token = self.register()
        response = self.client.post(
            "/api/assess/phq9",
            headers={"Authorization": f"Bearer {token}"},
            json={"assessment_type": "PHQ-9", "answers": [0, 0, 0, 0, 0, 0, 0, 0, 1]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["severity_category"], "Minimal")
        self.assertTrue(response.json()["crisis_flag"])

    def test_gad7_score_appears_as_stress_data(self):
        token = self.register()
        headers = {"Authorization": f"Bearer {token}"}
        assessment = self.client.post(
            "/api/assess/gad7",
            headers=headers,
            json={"assessment_type": "GAD-7", "answers": [2, 2, 2, 2, 2, 2, 2]},
        )
        self.assertEqual(assessment.status_code, 200, assessment.text)
        self.assertEqual(assessment.json()["severity_category"], "Moderate")
        trend = self.client.get("/api/trends/summary", headers=headers).json()
        self.assertEqual(len(trend["points"]), 7)
        self.assertAlmostEqual(trend["points"][-1]["stress_score"], 66.7, places=1)

    def test_trend_returns_seven_days_and_detects_a_decline(self):
        token = self.register()
        profile = self.client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).json()
        today = utc_now().date()
        with TestSession() as session:
            for offset in range(7):
                session.add(DailyLog(
                    user_id=profile["id"],
                    entry_date=today - timedelta(days=6 - offset),
                    journal_text="A private note",
                    mood_tag="Low",
                    sentiment_score=0.5 - (offset * 0.25),
                    dominant_emotion="sadness",
                ))
            session.commit()
        response = self.client.get("/api/trends/summary", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(len(data["points"]), 7)
        self.assertIsNotNone(data["points"][-1]["moving_average"])
        self.assertEqual(data["trend"], "declining")
        self.assertEqual(data["risk_level"], "Amber")

    def test_protected_routes_require_a_token(self):
        self.assertEqual(self.client.get("/api/logs").status_code, 401)

    def test_chat_extracts_issue_and_surfaces_summary(self):
        token = self.register()
        response = self.client.post(
            "/api/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"messages": [
                {"role": "user", "content": "I'm overwhelmed by exams and assignments."},
                {"role": "assistant", "content": "Which part feels heaviest?"},
                {"role": "user", "content": "The workload and grades have me worried."},
            ]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["profile"]["primary_issue"], "academic_stress")
        self.assertIsNotNone(response.json()["wellness_summary"])

    def test_chat_crisis_does_not_offer_routine_matching(self):
        token = self.register()
        headers = {"Authorization": f"Bearer {token}"}
        chat = self.client.post("/api/chat", headers=headers, json={
            "messages": [{"role": "user", "content": "I might hurt myself."}],
        })
        self.assertTrue(chat.json()["safety_resources_recommended"])
        matching = self.client.post("/api/doctors/recommend", headers=headers, json={
            "primary_issue": "crisis_support", "severity": "high", "keywords": ["immediate_support"],
        })
        self.assertEqual(matching.json()["doctors"], [])
        self.assertTrue(matching.json()["safety_first"])

    def test_doctor_matching_filters_and_marks_demo_profiles(self):
        token = self.register()
        response = self.client.post(
            "/api/doctors/recommend",
            headers={"Authorization": f"Bearer {token}"},
            json={"primary_issue": "sleep", "severity": "mild", "keywords": ["sleep", "rest"], "session_mode": "online"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertTrue(data["doctors"])
        self.assertIn("sleep", data["doctors"][0]["headline"].lower())
        self.assertTrue(all(doctor["is_demo"] and not doctor["is_verified"] for doctor in data["doctors"]))
        self.assertIn("fictional", data["note"].lower())

    def test_doctor_filters_include_specialty_rating_language_and_experience(self):
        token = self.register()
        response = self.client.post(
            "/api/doctors/recommend",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "primary_issue": "anxiety",
                "severity": "mild",
                "keywords": ["anxiety"],
                "specialty": "Anxiety",
                "min_experience": 5,
                "session_mode": "online",
                "language": "English",
                "min_rating": 4.8,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([doctor["display_name"] for doctor in response.json()["doctors"]], ["Aanya Sen (Demo)"])


if __name__ == "__main__":
    unittest.main()