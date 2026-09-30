"""Local text similarity: TF-IDF vectors + cosine similarity, stdlib only.

Used to rank prior-art candidates against an idea. This is a *lexical* measure —
it catches "same words, same problem" reliably and is honest about what it is.
It does not understand semantics; the verdict thresholds in novelty.py are tuned
for that limitation (high bar for OCCUPIED, evidence always shown).
"""

from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+")

_STOPWORDS = frozenset(
    """
    a an the and or for with from that this these those are was were has have had
    will would could should its it is to of in on at as by be been into over
    under between through during about into out off up down new use using used
    based via app tool tools platform system open source free best top your you
    our we they their them then than also just can not no yes all any more most
    how what when where which who why
    """.split()
)


def _stem(word: str) -> str:
    """Conservative English stemmer. Crude but deterministic and symmetric —
    both sides of every comparison are stemmed the same way, which is what
    matters for matching "lints" with "linter" or "memories" with "memory"."""
    if word.endswith("ies") and len(word) > 5:
        return word[:-3] + "y"
    for suffix in ("ing", "ed", "ness"):
        if word.endswith(suffix) and len(word) > len(suffix) + 3:
            return word[: -len(suffix)]
    if word.endswith("es") and len(word) > 5:
        return word[:-2]
    if word.endswith("s") and len(word) > 4 and not word.endswith("ss"):
        return word[:-1]
    for suffix in ("er", "or"):
        if word.endswith(suffix) and len(word) > len(suffix) + 3:
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> list[str]:
    toks = _TOKEN_RE.findall(text.lower())
    return [_stem(t) for t in toks if len(t) >= 3 and t not in _STOPWORDS]


def keywords(text: str, top_n: int = 12) -> list[str]:
    """Most significant terms in a text, by raw frequency."""
    counts = Counter(tokenize(text))
    return [w for w, _ in counts.most_common(top_n)]


def _idf(corpus_tokens: list[list[str]]) -> dict[str, float]:
    n = len(corpus_tokens)
    df: Counter[str] = Counter()
    for toks in corpus_tokens:
        for t in set(toks):
            df[t] += 1
    # smoothed idf; a term in every doc still carries a little weight
    return {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}


def _vector(toks: list[str], idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(toks)
    total = sum(counts.values()) or 1
    vec: dict[str, float] = {}
    for t, c in counts.items():
        # sublinear tf dampens repetition spam
        vec[t] = (1.0 + math.log(c)) * idf.get(t, 1.0) / total
    return vec


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def rank(idea: str, candidates: list[dict]) -> list[tuple[dict, float]]:
    """Rank candidate dicts (each with a 'text' field) against the idea text.

    Returns (candidate, score) sorted by score descending, score in [0, 1].
    """
    docs = [tokenize(idea)] + [tokenize(c.get("text", "")) for c in candidates]
    idf = _idf(docs)
    idea_vec = _vector(docs[0], idf)
    scored = []
    for cand, toks in zip(candidates, docs[1:]):
        scored.append((cand, cosine(idea_vec, _vector(toks, idf))))
    scored.sort(key=lambda p: p[1], reverse=True)
    return scored


def keyword_overlap(a: str, b: str) -> float:
    """Fraction of a's keywords that also appear in b. Catches name-level hits."""
    ka, kb = set(keywords(a, 8)), set(tokenize(b))
    if not ka:
        return 0.0
    return len(ka & kb) / len(ka)
