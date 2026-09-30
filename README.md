# whitespace

**Find the whitespace in the AI tool market.**

A zero-dependency, keyless CLI for AI-tool builders that combines an **AI-tool
trend radar** with an **automated novelty gate**. No API keys, no LLM, no
accounts — every source is public, every result is deterministic, and every
verdict ships with the evidence behind it.

```
$ whitespace check "AI agent memory auditor that lints MEMORY.md files for staleness"

[GREENFIELD]  top similarity 0.164 · 16 candidates

evidence
  0.164  @shadcn/lint
         https://www.npmjs.com/package/@shadcn/lint
         shares: agent, lint
  0.126  xerj-org/xerj
         https://github.com/xerj-org/xerj
         direct overlap on: agent, audit, memory, token
  ...
```

## Why this exists

Builders waste weeks on ideas that already shipped. Existing "did this exist?"
workflows are prompt-based agent skills that need a host and an LLM, or
trend digests that never answer the novelty question. whitespace is one
standalone product that does both: it watches what's launching, and it gates
your idea against what's already out there — locally, reproducibly, in CI if
you want.

## Commands

```bash
whitespace scan [--days 14] [--json out.json]
```
Collects this week's AI-tool signals from GitHub, Hacker News, and Product
Hunt, clusters them into themes, and prints the landscape. Saved to
`~/.whitespace/last_scan.json`.

```bash
whitespace check "your one-line idea" [--json out.json]
```
The novelty gate. Reframes your idea into several search vocabularies, searches
prior art across code (GitHub), discussion (Hacker News), and shipped packages
(npm), ranks candidates with local TF-IDF similarity, and returns a verdict:

| Verdict | Meaning |
|---|---|
| `GREENFIELD` | Nothing close surfaced in the searched sources. |
| `CONTESTED` | Related work exists — the evidence table shows exactly where, and where the room is. |
| `OCCUPIED` | A direct equivalent exists. The top rows name it. |

Every check is appended to a local ledger (`~/.whitespace/checks.json`), so
re-checking an idea opens with its history and tells you what changed.

```bash
whitespace ledger [--limit 10]      # past checks
whitespace report [--out report.html]  # dark HTML dossier: radar + ledger
```

## Install

Requires Python 3.10+. Zero third-party dependencies — the standard library is
the whole stack.

```bash
git clone https://github.com/CYPHERLYNX/whitespace
cd whitespace
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## How the verdict works

1. **Query expansion** — the idea is reframed into keyword variants, because
   different communities describe the same thing differently ("memory auditor"
   vs "context linter").
2. **Multi-source search** — short keyword queries hit three keyless JSON APIs:
   GitHub repository search, the Hacker News Algolia API, and the npm registry
   search API. Each source degrades to "unavailable" instead of crashing the run.
3. **Local ranking** — candidates are scored against the idea with TF-IDF
   cosine similarity (stdlib only), plus a conservative English stemmer so
   "lints" matches "linter".
4. **Verdict** — `OCCUPIED` at similarity ≥ 0.50 (or strong name overlap),
   `CONTESTED` at ≥ 0.28, otherwise `GREENFIELD`.

The thresholds are heuristics, not law. Similarity here is **lexical**, not
semantic: it reliably catches "same words, same problem" and is honest about
the rest. The evidence table — ranked candidates with scores, links, and a
mechanical read of the overlap — is the real output. The verdict is a
headline. Audit the top rows before you build.

## Honest limitations

- `GREENFIELD` means "nothing close in the searched sources", not "nothing
  exists". A differently-worded equivalent can slip through.
- General web search is deliberately excluded: search engines bot-wall
  server-side requests, which would make results flaky. Code, discussion, and
  package registries are the stable, keyless surface.
- Product Hunt coverage comes via the community-curated
  `awesome-product-hunt` ledger rather than scraping producthunt.com.
- Unauthenticated GitHub search is rate-limited (~10 requests/minute); heavy
  use should space out checks.

## Design

The HTML dossier uses a restrained dark system — near-black `#0a0b0d`,
panel `#121417`, muted green accent — no gradients, no template glow. The
terminal output is ANSI-colored for dark terminals and respects `NO_COLOR`.

## Development

```bash
python -m unittest discover -s tests   # 22 tests, stdlib only, no network
```

```
whitespace/
├── whitespace/
│   ├── cli.py        # scan | check | ledger | report
│   ├── trends.py     # trend radar providers + theme clustering
│   ├── novelty.py    # query expansion, providers, verdict logic
│   ├── scoring.py    # TF-IDF + cosine + stemming, stdlib only
│   ├── sources.py    # keyless HTTP helpers with graceful degradation
│   ├── store.py      # ~/.whitespace JSON ledger
│   └── report.py     # self-contained dark HTML dossier
└── tests/            # mocked providers, no network
```

## License

MIT — see [LICENSE](LICENSE).
