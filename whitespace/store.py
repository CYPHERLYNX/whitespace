"""Local ledger: every novelty check is recorded so re-checks open with history.

Stored at ~/.whitespace/checks.json — a plain JSON array, human-readable,
never leaves the machine. Mirrors the "checked ideas persist" habit of good
prior-art workflows: when you re-check an idea, whitespace shows you what the
verdict was last time and whether it changed.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from . import scoring

DIR = Path.home() / ".whitespace"
CHECKS_FILE = DIR / "checks.json"
SCAN_FILE = DIR / "last_scan.json"


def _read_checks() -> list[dict]:
    try:
        return json.loads(CHECKS_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_check(result: dict) -> dict:
    DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "idea": result["idea"],
        "verdict": result["verdict"],
        "top_score": result["top_score"],
        "candidates_examined": result["candidates_examined"],
        "top_evidence": [
            {"name": e["name"], "url": e["url"], "score": e["score"]}
            for e in result["evidence"][:3]
        ],
        # full ranked evidence so reports stay auditable without re-running
        "evidence_full": result["evidence"][:8],
    }
    checks = _read_checks()
    checks.append(record)
    CHECKS_FILE.write_text(json.dumps(checks, indent=2))
    return record


def load_checks() -> list[dict]:
    return _read_checks()


def similar_previous_checks(idea: str, limit: int = 3) -> list[dict]:
    """Past checks for a similar idea, most similar first."""
    checks = _read_checks()
    if not checks:
        return []
    ranked = scoring.rank(idea, [{"text": c["idea"]} for c in checks])
    # ranked[i] corresponds to checks[i]; order by score desc
    order = sorted(range(len(checks)), key=lambda i: -ranked[i][1])
    out = []
    for i in order[:limit]:
        if ranked[i][1] > 0.35:
            rec = dict(checks[i])
            rec["similarity"] = round(ranked[i][1], 3)
            out.append(rec)
    return out


def save_scan(scan: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    SCAN_FILE.write_text(json.dumps(scan, indent=2))


def load_scan() -> dict | None:
    try:
        return json.loads(SCAN_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None
