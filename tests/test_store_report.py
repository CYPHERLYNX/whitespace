"""Store (ledger) and report tests. Filesystem-isolated via tmp dirs."""

import unittest

from whitespace import report, store


def _fake_result(idea="an idea <script>alert(1)</script>"):
    return {
        "idea": idea,
        "queries": ["an idea"],
        "verdict": "CONTESTED",
        "top_score": 0.33,
        "candidates_examined": 4,
        "evidence": [
            {
                "name": "user/similar", "url": "https://example.com/similar",
                "source": "github", "meta": "★ 10", "blurb": "does similar things",
                "score": 0.33, "note": "shares: similar",
            }
        ],
    }


def _fake_record(idea="an idea <script>alert(1)</script>"):
    rec = _fake_result(idea)
    rec["ts"] = "2026-09-30T10:00:00+00:00"
    rec["evidence_full"] = rec["evidence"]
    rec["top_evidence"] = [
        {"name": e["name"], "url": e["url"], "score": e["score"]} for e in rec["evidence"]
    ]
    return rec


class TestStore(unittest.TestCase):
    def setUp(self):
        self._orig = (store.DIR, store.CHECKS_FILE, store.SCAN_FILE)
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        from pathlib import Path
        store.DIR = Path(self.tmp.name)
        store.CHECKS_FILE = store.DIR / "checks.json"
        store.SCAN_FILE = store.DIR / "last_scan.json"

    def tearDown(self):
        store.DIR, store.CHECKS_FILE, store.SCAN_FILE = self._orig
        self.tmp.cleanup()

    def test_save_and_load_roundtrip(self):
        rec = store.save_check(_fake_result())
        checks = store.load_checks()
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]["verdict"], "CONTESTED")
        self.assertEqual(checks[0]["idea"], rec["idea"])
        self.assertEqual(len(checks[0]["evidence_full"]), 1)

    def test_similar_previous_checks_finds_match(self):
        store.save_check(_fake_result("AI agent memory auditor lints memory files"))
        hits = store.similar_previous_checks("AI agent memory auditor for stale instructions")
        self.assertEqual(len(hits), 1)
        self.assertGreater(hits[0]["similarity"], 0.35)

    def test_similar_previous_checks_ignores_dissimilar(self):
        store.save_check(_fake_result("sourdough bread baking timer"))
        hits = store.similar_previous_checks("AI agent memory auditor for stale instructions")
        self.assertEqual(hits, [])

    def test_similar_previous_checks_pairs_right_records(self):
        # regression: rank() sorts, so records must follow their own scores
        store.save_check(_fake_result("sourdough bread baking timer"))
        store.save_check(_fake_result("AI agent memory auditor lints memory files"))
        hits = store.similar_previous_checks("AI agent memory auditor for stale instructions")
        self.assertEqual(len(hits), 1)
        self.assertIn("memory auditor", hits[0]["idea"])
        self.assertGreater(hits[0]["similarity"], 0.35)

    def test_scan_roundtrip(self):
        scan = {"generated_at": "x", "window_days": 14, "sources": {}, "themes": []}
        store.save_scan(scan)
        self.assertEqual(store.load_scan(), scan)


class TestReport(unittest.TestCase):
    def test_build_escapes_and_marks_verdict(self):
        from pathlib import Path
        import tempfile
        out = Path(tempfile.mkdtemp()) / "r.html"
        rec = _fake_record()
        report.build(None, [rec], out)
        text = out.read_text()
        self.assertIn("v-CONTESTED", text)
        self.assertNotIn("<script>alert(1)</script>", text)
        self.assertIn("&lt;script&gt;", text)

    def test_dark_theme_tokens_present(self):
        from pathlib import Path
        import tempfile
        out = Path(tempfile.mkdtemp()) / "r.html"
        report.build(None, [], out)
        text = out.read_text()
        for token in ("#0a0b0d", "#121417", "#e8eaed", "#3ddc84"):
            self.assertIn(token, text)
        self.assertNotIn("linear-gradient", text)


if __name__ == "__main__":
    unittest.main()
