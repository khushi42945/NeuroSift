import unittest

from ai_engine import analyze_text, score_assessment, severity_for_gad7, severity_for_phq9


class SeverityTests(unittest.TestCase):
    def test_phq9_boundaries(self):
        self.assertEqual([severity_for_phq9(score) for score in (0, 5, 10, 15, 20)],
                         ["Minimal", "Mild", "Moderate", "Moderately Severe", "Severe"])

    def test_gad7_boundaries(self):
        self.assertEqual([severity_for_gad7(score) for score in (0, 5, 10, 15)],
                         ["Minimal", "Mild", "Moderate", "Severe"])

    def test_phq9_question_nine_flags_immediately(self):
        result = score_assessment("PHQ-9", [0, 0, 0, 0, 0, 0, 0, 0, 1])
        self.assertTrue(result["crisis_flag"])
        self.assertEqual(result["severity_category"], "Minimal")

    def test_high_score_without_self_harm_answer_is_not_crisis_flagged(self):
        result = score_assessment("PHQ-9", [3, 3, 3, 3, 3, 3, 3, 3, 0])
        self.assertEqual(result["severity_category"], "Severe")
        self.assertFalse(result["crisis_flag"])

    def test_invalid_answer_count_is_rejected(self):
        with self.assertRaises(ValueError):
            score_assessment("GAD-7", [0] * 6)

    def test_journal_fallback_and_distress_detection(self):
        result = analyze_text("I feel anxious and hopeless. I might hurt myself.")
        self.assertEqual(result["dominant_emotion"], "sadness")
        self.assertEqual(result["sentiment_score"], -1.0)
        self.assertTrue(result["crisis_flag"])


if __name__ == "__main__":
    unittest.main()