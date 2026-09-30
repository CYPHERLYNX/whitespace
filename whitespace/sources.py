"""Keyless HTTP helpers.

Everything whitespace talks to is public and keyless: the GitHub REST API
(unauthenticated), the Hacker News Algolia API, DuckDuckGo's HTML endpoint, and
raw GitHub content. Polite by default: short timeouts, a real User-Agent, and
explicit errors when a source rate-limits or disappears so callers can degrade
gracefully instead of crashing.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

USER_AGENT = "whitespace-ai/0.1.0 (+https://github.com/CYPHERLYNX/whitespace)"


class SourceUnavailable(Exception):
    """The source could not be reached or returned an unexpected status."""


class RateLimited(Exception):
    """The source asked us to slow down (HTTP 403/429 on keyless endpoints)."""


def fetch(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429):
            raise RateLimited(f"{url} -> HTTP {exc.code}") from exc
        raise SourceUnavailable(f"{url} -> HTTP {exc.code}") from exc
    except Exception as exc:  # DNS, TLS, timeouts, refused connections
        raise SourceUnavailable(f"{url}: {exc}") from exc


def fetch_json(url: str, timeout: int = 15) -> dict | list:
    return json.loads(fetch(url, timeout))
