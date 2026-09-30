"""Trend-radar tests with mocked HTTP (no network)."""

import unittest
from unittest.mock import patch

from whitespace import sources, trends


GH_FIXTURE = {
    "items": [
        {
            "full_name": "acme/voicepilot",
            "html_url": "https://github.com/acme/voicepilot",
            "description": "Open source voice AI agent for phone calls",
            "stargazers_count": 900,
            "language": "Python",
        },
        {
            "full_name": "acme/breadcalc",
            "html_url": "https://github.com/acme/breadcalc",
            "description": "sourdough hydration calculator",
            "stargazers_count": 12,
            "language": "JS",
        },
    ]
}

HN_FIXTURE = {
    "hits": [
        {
            "title": "Show HN: Local LLM memory layer for coding agents",
            "url": "https://example.com/mem",
            "objectID": "1",
            "points": 210,
            "num_comments": 80,
        },
        {
            "title": "Show HN: my mechanical keyboard",
            "url": "https://example.com/kb",
            "objectID": "2",
            "points": 30,
            "num_comments": 5,
        },
    ]
}

PH_FIXTURE = """
| `26-09-15` | [VoicePilot](https://www.producthunt.com/posts/voicepilot) | AI voice agents for sales calls |
| `26-09-10` | [BreadCalc](https://www.producthunt.com/posts/breadcalc) | sourdough hydration math |
| `25-01-01` | [OldTool](https://www.producthunt.com/posts/oldtool) | AI chatbot from last year |
"""


class TestTrends(unittest.TestCase):
    def test_github_parses_and_labels_themes(self):
        with patch.object(sources, "fetch_json", return_value=GH_FIXTURE):
            items, status = trends.github_trends()
        self.assertEqual(status, "ok")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["source"], "github")
        self.assertIn("Voice AI", items[0]["themes"])
        self.assertIn("★ 900", items[0]["meta"])

    def test_hn_filters_non_ai_and_dedupes(self):
        with patch.object(sources, "fetch_json", return_value=HN_FIXTURE):
            items, status = trends.hn_trends()
        self.assertEqual(status, "ok")
        titles = [i["name"] for i in items]
        self.assertTrue(any("memory layer" in t for t in titles))
        self.assertFalse(any("keyboard" in t for t in titles))

    def test_producthunt_parses_ledger_filters_ai_and_window(self):
        with patch.object(sources, "fetch", return_value=PH_FIXTURE):
            items, status = trends.producthunt_trends(days=30)
        self.assertTrue(status.startswith("ok"))
        names = [i["name"] for i in items]
        self.assertIn("VoicePilot", names)
        self.assertNotIn("BreadCalc", names)   # not AI
        self.assertNotIn("OldTool", names)     # outside the window

    def test_source_failure_degrades_gracefully(self):
        with patch.object(sources, "fetch_json",
                          side_effect=sources.SourceUnavailable("down")):
            items, status = trends.github_trends()
        self.assertEqual(items, [])
        self.assertIn("unavailable", status)

    def test_scan_aggregates_theme_counts(self):
        with patch.object(sources, "fetch_json",
                          side_effect=[GH_FIXTURE, HN_FIXTURE, HN_FIXTURE]), \
             patch.object(sources, "fetch", return_value=PH_FIXTURE):
            scan = trends.scan(days=30)
        self.assertIn("themes", scan)
        theme_names = [t["theme"] for t in scan["themes"]]
        self.assertIn("Voice AI", theme_names)
        # counts sorted desc
        counts = [t["count"] for t in scan["themes"]]
        self.assertEqual(counts, sorted(counts, reverse=True))


if __name__ == "__main__":
    unittest.main()
