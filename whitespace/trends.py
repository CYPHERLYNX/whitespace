"""Trend radar: this week's AI-tool landscape from public, keyless sources.

Providers (all keyless, all degrade to [] with a warning instead of failing):
  - GitHub: repositories about AI created in the last N days, sorted by stars
    (unauthenticated search API).
  - Hacker News: front-page stories matching AI keywords, plus recent Show HN
    launches about AI (Algolia API).
  - Product Hunt: recent AI launches, via the community-curated awesome-product-hunt
    ledger (raw GitHub content — far more stable than scraping producthunt.com).

`scan()` returns {"generated_at", "sources": {name: {"items": [...], "status": ...}},
"themes": [...]}. Each item: {"source", "name", "url", "blurb", "meta"}.
"""

from __future__ import annotations

import datetime as dt
import re
import urllib.parse

from . import sources
from .sources import RateLimited, SourceUnavailable

AI_KEYWORDS = (
    "ai", "llm", "gpt", "claude", "agent", "agents", "agentic", "mcp",
    "diffusion", "tts", "voice", "rag", "embedding", "inference", "copilot",
    "genai", "generative",
)

# Deterministic theme map: keyword hits -> theme label. Order matters for display.
THEMES: list[tuple[str, tuple[str, ...]]] = [
    ("AI coding agents", ("coding agent", "code agent", "dev agent", "copilot", "cursor")),
    ("Agent skills & plugins", ("skill", "plugin")),
    ("MCP & tool infrastructure", ("mcp", "model context protocol", "tool call")),
    ("Agent memory & context", ("memory", "context window", "context")),
    ("AI security", ("security", "secure", "jailbreak", "injection", "red team", "pentest")),
    ("Voice AI", ("voice", "speech", "tts", "stt", "call")),
    ("Media generation", ("video", "image generat", "diffusion", "music")),
    ("Local & small models", ("local", "on-device", "ollama", "quant")),
    ("Evals & observability", ("eval", "observ", "benchmark", "tracing")),
]


def _ai_relevant(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in AI_KEYWORDS)


def _theme_of(text: str) -> list[str]:
    t = text.lower()
    return [label for label, kws in THEMES if any(k in t for k in kws)] or ["Other AI"]


# ---------------------------------------------------------------- GitHub ---

def github_trends(days: int = 14, per_page: int = 25) -> tuple[list[dict], str]:
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    query = f"AI created:>{since} stars:>15"
    url = (
        "https://api.github.com/search/repositories?q="
        + urllib.parse.quote(query)
        + f"&sort=stars&order=desc&per_page={per_page}"
    )
    try:
        data = sources.fetch_json(url)
    except (SourceUnavailable, RateLimited) as exc:
        return [], f"unavailable ({exc})"
    items = []
    for r in data.get("items", []):
        blurb = r.get("description") or ""
        items.append(
            {
                "source": "github",
                "name": r.get("full_name", "?"),
                "url": r.get("html_url", ""),
                "blurb": blurb,
                "meta": f"★ {r.get('stargazers_count', 0)} · {r.get('language') or '—'}",
                "themes": _theme_of(r.get("full_name", "") + " " + blurb),
            }
        )
    return items, "ok"


# ------------------------------------------------------------ Hacker News ---

def _hn(url: str) -> list[dict]:
    data = sources.fetch_json(url)
    out = []
    for h in data.get("hits", []):
        title = h.get("title") or ""
        if not _ai_relevant(title):
            continue
        out.append(
            {
                "source": "hn",
                "name": title,
                "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                "blurb": "",
                "meta": f"{h.get('points', 0)} points · {h.get('num_comments', 0)} comments",
                "themes": _theme_of(title),
            }
        )
    return out


def hn_trends(limit: int = 30) -> tuple[list[dict], str]:
    try:
        week_ago = int((dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).timestamp())
        front = _hn("https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=60")
        show = _hn(
            "https://hn.algolia.com/api/v1/search?tags=show_hn"
            f"&numericFilters=created_at_i>{week_ago}&hitsPerPage=40"
        )
        seen, items = set(), []
        for it in front + show:
            if it["name"] not in seen:
                seen.add(it["name"])
                items.append(it)
        return items[:limit], "ok"
    except (SourceUnavailable, RateLimited) as exc:
        return [], f"unavailable ({exc})"


# ----------------------------------------------------------- Product Hunt ---

_PH_ROW = re.compile(
    r"\|\s*`(\d{2}-\d{2}-\d{2})`\s*\|\s*\[([^\]]+)\]\((https://www\.producthunt\.com/[^)]+)\)"
    r"\s*\|\s*([^|]*?)\s*(?:\||$)"
)


def producthunt_trends(days: int = 14, limit: int = 25) -> tuple[list[dict], str]:
    """Recent AI launches via the awesome-product-hunt ledger (public, stable)."""
    url = "https://raw.githubusercontent.com/fmerian/awesome-product-hunt/main/README.md"
    try:
        text = sources.fetch(url)
    except (SourceUnavailable, RateLimited) as exc:
        return [], f"unavailable ({exc})"
    cutoff = dt.date.today() - dt.timedelta(days=days)
    items = []
    for m in _PH_ROW.finditer(text):
        datestr, name, link, tagline = m.groups()
        try:
            launched = dt.datetime.strptime("20" + datestr, "%Y-%m-%d").date()
        except ValueError:
            continue
        if launched < cutoff:
            continue
        blob = f"{name} {tagline}"
        if not _ai_relevant(blob):
            continue
        items.append(
            {
                "source": "producthunt",
                "name": name.strip(),
                "url": link.strip(),
                "blurb": tagline.strip(),
                "meta": f"launched {launched.isoformat()}",
                "themes": _theme_of(blob),
            }
        )
        if len(items) >= limit:
            break
    return items, "ok (via awesome-product-hunt ledger)"


# ------------------------------------------------------------------ scan ---

def scan(days: int = 14) -> dict:
    gh, gh_status = github_trends(days)
    hn, hn_status = hn_trends()
    ph, ph_status = producthunt_trends(days)

    theme_counts: dict[str, int] = {}
    for it in gh + hn + ph:
        for theme in it.get("themes", ["Other AI"]):
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
    themes = sorted(theme_counts.items(), key=lambda p: p[1], reverse=True)

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "window_days": days,
        "sources": {
            "github": {"items": gh, "status": gh_status},
            "hackernews": {"items": hn, "status": hn_status},
            "producthunt": {"items": ph, "status": ph_status},
        },
        "themes": [{"theme": t, "count": c} for t, c in themes],
    }
