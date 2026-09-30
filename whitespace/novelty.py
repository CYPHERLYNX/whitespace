"""Novelty gate: does this idea already exist?

Pipeline (deterministic, keyless, no LLM):
  1. expand_queries() reframes the idea into several search vocabularies —
     the raw idea, its significant keywords, and a "keywords + open source"
     variant (different communities describe the same thing differently).
  2. Keyword variants are searched against three keyless JSON APIs:
       GitHub repository search  — prior art in code
       Hacker News (Algolia)     — prior art in discussion / Show HN
       npm registry search       — prior art in shipped packages
     Every source degrades gracefully; a dead source yields [] not a crash.
     (Deliberately no HTML web scraping: general search engines bot-wall
     server-side requests, so results would be flaky. The three JSON
     sources above are stable and cover code, conversation, and packages.)
  3. Candidates are ranked against the idea with local TF-IDF cosine similarity.
  4. A verdict is issued from the top score plus a name-overlap tripwire:

       OCCUPIED   top_score >= 0.50 or strong name overlap — a direct
                  equivalent exists; the evidence names it.
       CONTESTED  top_score >= 0.28 — related work exists; room to
                  differentiate, evidence shows where.
       GREENFIELD otherwise — nothing close found in the searched sources.

The verdict is a *starting point backed by evidence*, not a legal judgment —
every check prints the ranked candidates with scores and URLs so a human can
audit the call. Similarity is lexical; genuinely novel framings of old ideas
can score low, and coincidental word overlap can score high. The evidence
table is the real output; the verdict is a headline.
"""

from __future__ import annotations

import urllib.parse

from . import scoring, sources
from .sources import RateLimited, SourceUnavailable

OCCUPIED_THRESHOLD = 0.50
CONTESTED_THRESHOLD = 0.28
NAME_OVERLAP_TRIPWIRE = 0.70


def expand_queries(idea: str) -> list[str]:
    kws = scoring.keywords(idea, top_n=10)
    core = " ".join(kws[:6]) or idea[:80]
    queries = [idea.strip()[:160]]
    if core.lower() not in queries[0].lower():
        queries.append(core)
    queries.append(core + " open source")
    # de-dupe, keep order
    seen, out = set(), []
    for q in queries:
        if q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out


def _github(query: str, per_page: int = 8) -> list[dict]:
    url = (
        "https://api.github.com/search/repositories?q="
        + urllib.parse.quote(query)
        + f"&sort=stars&order=desc&per_page={per_page}"
    )
    try:
        data = sources.fetch_json(url)
    except (SourceUnavailable, RateLimited):
        return []
    out = []
    for r in data.get("items", []):
        name = r.get("full_name", "?")
        desc = r.get("description") or ""
        out.append(
            {
                "source": "github",
                "name": name,
                "url": r.get("html_url", ""),
                "blurb": desc,
                "meta": f"★ {r.get('stargazers_count', 0)}",
                "text": f"{name} {desc}",
            }
        )
    return out


def _hn(query: str, per_page: int = 8) -> list[dict]:
    url = (
        "https://hn.algolia.com/api/v1/search?query="
        + urllib.parse.quote(query)
        + f"&tags=story&hitsPerPage={per_page}"
    )
    try:
        data = sources.fetch_json(url)
    except (SourceUnavailable, RateLimited):
        return []
    out = []
    for h in data.get("hits", []):
        title = h.get("title") or ""
        out.append(
            {
                "source": "hackernews",
                "name": title,
                "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                "blurb": "",
                "meta": f"{h.get('points', 0)} points",
                "text": title,
            }
        )
    return out


def _npm(query: str, per_page: int = 8) -> list[dict]:
    """Shipped packages: npm registry search is keyless JSON and stable."""
    url = (
        "https://registry.npmjs.org/-/v1/search?text="
        + urllib.parse.quote(query)
        + f"&size={per_page}"
    )
    try:
        data = sources.fetch_json(url)
    except (SourceUnavailable, RateLimited):
        return []
    out = []
    for obj in data.get("objects", []):
        pkg = obj.get("package", {})
        name = pkg.get("name", "?")
        desc = pkg.get("description") or ""
        links = pkg.get("links", {}) or {}
        kws = " ".join(pkg.get("keywords", []) or [])
        out.append(
            {
                "source": "npm",
                "name": name,
                "url": links.get("npm") or links.get("homepage") or "",
                "blurb": desc,
                "meta": f"v{pkg.get('version', '?')}",
                "text": f"{name} {desc} {kws}",
            }
        )
    return out


def _dedupe(cands: list[dict]) -> list[dict]:
    seen, out = set(), []
    for c in cands:
        key = (c["source"], c["url"] or c["name"])
        if key not in seen and c["name"].strip():
            seen.add(key)
            out.append(c)
    return out


def _differentiation_note(idea: str, cand: dict) -> str:
    idea_kw = set(scoring.keywords(idea, 10))
    cand_kw = set(scoring.tokenize(cand.get("text", "")))
    shared = sorted(idea_kw & cand_kw)
    if not shared:
        return "adjacent — little vocabulary overlap with the idea"
    if len(shared) >= 4:
        return "direct overlap on: " + ", ".join(shared[:6])
    return "shares: " + ", ".join(shared)


def check(idea: str) -> dict:
    idea = idea.strip()
    kws = scoring.keywords(idea, top_n=10)
    # Short conjunctive queries: GitHub ANDs every term, so fewer terms
    # recall more; HN/npm tolerate a couple more.
    gh_query = " ".join(kws[:3]) or idea[:80]
    hn_query = " ".join(kws[:5]) or idea[:80]
    npm_query = " ".join(kws[:4]) or idea[:80]
    queries = [idea, gh_query, npm_query]

    candidates: list[dict] = []
    candidates += _github(gh_query)
    candidates += _hn(hn_query)
    candidates += _npm(npm_query)
    candidates = _dedupe(candidates)

    ranked = scoring.rank(idea, candidates)
    evidence = []
    for cand, score in ranked[:8]:
        evidence.append(
            {
                "name": cand["name"],
                "url": cand["url"],
                "source": cand["source"],
                "meta": cand.get("meta", ""),
                "blurb": (cand.get("blurb") or "")[:220],
                "score": round(score, 3),
                "note": _differentiation_note(idea, cand),
            }
        )

    top_score = evidence[0]["score"] if evidence else 0.0
    name_hit = any(
        scoring.keyword_overlap(idea, e["name"]) >= NAME_OVERLAP_TRIPWIRE
        for e in evidence[:5]
    )
    if top_score >= OCCUPIED_THRESHOLD or name_hit:
        verdict = "OCCUPIED"
    elif top_score >= CONTESTED_THRESHOLD:
        verdict = "CONTESTED"
    else:
        verdict = "GREENFIELD"

    return {
        "idea": idea,
        "queries": queries,
        "verdict": verdict,
        "top_score": top_score,
        "candidates_examined": len(candidates),
        "evidence": evidence,
    }
