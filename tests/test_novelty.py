"""Novelty-gate tests with mocked providers (no network)."""

import unittest
from unittest.mock import patch

from whitespace import novelty


def _cand(source, name, blurb, meta=""):
    return {
        "source": source, "name": name, "url": "https://example.com/" + name,
        "blurb": blurb, "meta": meta, "text": f"{name} {blurb}",
    }


OCCUPIED_CANDS = [
    _cand("github", "user/stalebrain",
          "Linter for AI agent memory files. Detects stale instructions in MEMORY.md",
          "★ 1200"),
    _cand("github", "user/memory-doctor",
          "Diagnose bloated agent memory files and wasted context tokens", "★ 800"),
    _cand("web", "ctxlint — agent memory linter",
          "Static analysis for Claude Code memory files", ""),
]

GREENFIELD_CANDS = [
    _cand("github", "user/sourdough-timer", "Bread baking timer with hydration math", "★ 12"),
    _cand("hackernews", "Show HN: my mechanical keyboard build", "", "40 points"),
]


class TestNovelty(unittest.TestCase):
    def test_occupied_verdict(self):
        with patch.object(novelty, "_github", return_value=OCCUPIED_CANDS), \
             patch.object(novelty, "_hn", return_value=[]), \
             patch.object(novelty, "_npm", return_value=[]):
            res = novelty.check("AI agent memory auditor that lints memory files for staleness")
        self.assertEqual(res["verdict"], "OCCUPIED")
        self.assertGreaterEqual(res["top_score"], novelty.OCCUPIED_THRESHOLD)
        self.assertTrue(res["evidence"])
        self.assertIn("stalebrain", res["evidence"][0]["name"])

    def test_greenfield_verdict(self):
        with patch.object(novelty, "_github", return_value=GREENFIELD_CANDS), \
             patch.object(novelty, "_hn", return_value=[]), \
             patch.object(novelty, "_npm", return_value=[]):
            res = novelty.check("AI tool opportunity radar with automated prior-art novelty gate")
        self.assertEqual(res["verdict"], "GREENFIELD")
        self.assertLess(res["top_score"], novelty.CONTESTED_THRESHOLD)

    def test_contested_verdict(self):
        cands = [_cand("github", "user/trend-digest",
                       "Weekly newsletter digest of AI tool news and launches", "★ 300")]
        with patch.object(novelty, "_github", return_value=cands), \
             patch.object(novelty, "_hn", return_value=[]), \
             patch.object(novelty, "_npm", return_value=[]):
            res = novelty.check("AI tool trend radar that scans launches and digests them weekly")
        self.assertEqual(res["verdict"], "CONTESTED")
        self.assertGreaterEqual(res["top_score"], novelty.CONTESTED_THRESHOLD)
        self.assertLess(res["top_score"], novelty.OCCUPIED_THRESHOLD)

    def test_empty_sources_is_greenfield_with_zero_candidates(self):
        with patch.object(novelty, "_github", return_value=[]), \
             patch.object(novelty, "_hn", return_value=[]), \
             patch.object(novelty, "_npm", return_value=[]):
            res = novelty.check("some idea")
        self.assertEqual(res["verdict"], "GREENFIELD")
        self.assertEqual(res["candidates_examined"], 0)
        self.assertEqual(res["evidence"], [])

    def test_query_expansion_produces_variants(self):
        qs = novelty.expand_queries("AI agent memory auditor that lints memory files")
        self.assertGreaterEqual(len(qs), 2)
        self.assertTrue(any("open source" in q for q in qs))

    def test_differentiation_notes_are_mechanical(self):
        with patch.object(novelty, "_github", return_value=OCCUPIED_CANDS), \
             patch.object(novelty, "_hn", return_value=[]), \
             patch.object(novelty, "_npm", return_value=[]):
            res = novelty.check("AI agent memory auditor that lints memory files for staleness")
        notes = [e["note"] for e in res["evidence"]]
        self.assertTrue(any("overlap" in n or "shares" in n for n in notes))


if __name__ == "__main__":
    unittest.main()
