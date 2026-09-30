import unittest

from whitespace import scoring


class TestScoring(unittest.TestCase):
    def test_similar_texts_score_high(self):
        a = "AI agent memory auditor that lints MEMORY.md files for stale instructions"
        b = "memory-doctor: lints your AI agent's memory files and finds stale context"
        score = scoring.rank(a, [{"text": b}])[0][1]
        self.assertGreaterEqual(score, 0.50, f"expected high similarity, got {score}")

    def test_dissimilar_texts_score_low(self):
        a = "AI agent memory auditor that lints MEMORY.md files for stale instructions"
        b = "a sourdough bread baking timer with hydration calculator"
        score = scoring.rank(a, [{"text": b}])[0][1]
        self.assertLess(score, 0.15, f"expected low similarity, got {score}")

    def test_ranking_orders_best_first(self):
        idea = "voice AI agent testing harness with simulated callers"
        cands = [
            {"text": "a recipe manager for soups"},
            {"text": "Cekura automated QA for voice AI agents with simulated conversations"},
        ]
        ranked = scoring.rank(idea, cands)
        self.assertIn("Cekura", ranked[0][0]["text"])
        self.assertGreater(ranked[0][1], ranked[1][1])

    def test_keyword_overlap_name_tripwire(self):
        idea = "dynamic sandbox that detonates AI agent skills"
        self.assertGreaterEqual(
            scoring.keyword_overlap(idea, "nyuwayskillsandbox dynamic sandbox for AI agent skills"),
            0.5,
        )
        self.assertLess(scoring.keyword_overlap(idea, "sourdough starter tracker"), 0.3)

    def test_empty_candidate_text_scores_zero(self):
        ranked = scoring.rank("some idea", [{"text": ""}])
        self.assertEqual(ranked[0][1], 0.0)


if __name__ == "__main__":
    unittest.main()
