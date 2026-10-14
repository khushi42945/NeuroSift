import unittest
from unittest.mock import patch

from conversation_engine import build_chat_reply, extract_conversation_profile, generate_assistant_message


class ConversationEngineTests(unittest.TestCase):
    def test_academic_stress_is_tagged_and_reflected(self):
        profile = extract_conversation_profile(["My exams are piling up and I can't keep up with the workload."])
        self.assertEqual(profile["primary_issue"], "academic_stress")
        self.assertIn("exam_stress", profile["keywords"])
        reply = build_chat_reply(profile, user_turn_count=2, request_summary=False)
        self.assertIsNotNone(reply["wellness_summary"])
        self.assertTrue(reply["recommendation_ready"])

    def test_explicit_self_harm_is_crisis_first(self):
        profile = extract_conversation_profile(["I want to end my life."])
        reply = build_chat_reply(profile, user_turn_count=5, request_summary=True)
        self.assertEqual(profile["severity"], "high")
        self.assertTrue(reply["safety_resources_recommended"])
        self.assertFalse(reply["recommendation_ready"])
        self.assertIsNone(reply["wellness_summary"])

    def test_indirect_self_harm_language_uses_crisis_response(self):
        profile = extract_conversation_profile(["I wish I could just not wake up tomorrow."])
        reply = build_chat_reply(profile, user_turn_count=1, request_summary=False)
        self.assertTrue(profile["crisis_flag"])
        self.assertTrue(reply["safety_resources_recommended"])

    def test_sleep_topics_are_not_diagnosed(self):
        profile = extract_conversation_profile(["I can't sleep well before work."])
        reply = build_chat_reply(profile, user_turn_count=1, request_summary=False)
        self.assertEqual(profile["primary_issue"], "sleep")
        self.assertIsNone(reply["wellness_summary"])
        self.assertIn("sleep", reply["assistant_message"].lower())

    def test_crisis_reply_bypasses_configured_model(self):
        import asyncio

        with patch.dict("os.environ", {"CONVERSATION_MODEL_URL": "https://invalid.example/chat", "CONVERSATION_MODEL_NAME": "test"}):
            result = asyncio.run(generate_assistant_message([], "Get urgent help now.", crisis_flag=True))
        self.assertEqual(result[0], "Get urgent help now.")
        self.assertEqual(result[1], "safety_template")

    def test_unconfigured_model_uses_local_reply(self):
        import asyncio

        with patch.dict("os.environ", {"CONVERSATION_MODEL_URL": "", "CONVERSATION_MODEL_NAME": ""}):
            result = asyncio.run(generate_assistant_message([], "A gentle local reply.", crisis_flag=False))
        self.assertEqual(result[0], "A gentle local reply.")
        self.assertEqual(result[1], "local_rules")

    def test_reply_changes_when_user_says_they_do_not_know(self):
        profile = extract_conversation_profile(["I feel burnt out."])
        first = build_chat_reply(profile, 1, False, "Feeling burnt out")
        follow_up = build_chat_reply(profile, 2, False, "I don't know")
        self.assertNotEqual(first["assistant_message"], follow_up["assistant_message"])
        self.assertIn("Not knowing is completely okay", follow_up["assistant_message"])

    def test_follow_up_varies_across_turns(self):
        profile = extract_conversation_profile(["My exams are overwhelming."])
        first = build_chat_reply(profile, 1, False, "My exams are overwhelming")
        second = build_chat_reply(profile, 2, False, "The deadlines are hard")
        self.assertNotEqual(first["assistant_message"], second["assistant_message"])


if __name__ == "__main__":
    unittest.main()