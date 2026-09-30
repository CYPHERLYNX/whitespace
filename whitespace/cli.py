"""Command line interface: scan | check | ledger | report."""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__, novelty, report, store, trends

# --- terminal styling (dark-terminal friendly, NO_COLOR respected) ---

_NO_COLOR = os.environ.get("NO_COLOR") is not None


def _st(code: str, text: str) -> str:
    return text if _NO_COLOR else f"\033[{code}m{text}\033[0m"


def bold(t: str) -> str:
    return _st("1", t)


def dim(t: str) -> str:
    return _st("2", t)


VERDICT_COLOR = {"GREENFIELD": "32", "CONTESTED": "33", "OCCUPIED": "31"}


def verdict_badge(v: str) -> str:
    return _st(f"1;{VERDICT_COLOR.get(v, '37')}", f"[{v}]")


# --- commands ---


def cmd_scan(args: argparse.Namespace) -> int:
    print(bold("whitespace scan") + dim(f"  — last {args.days} days"))
    scan = trends.scan(days=args.days)
    store.save_scan(scan)
    print()
    print(bold("themes"))
    for t in scan["themes"][:10]:
        bar = "█" * min(t["count"], 24)
        print(f"  {t['theme']:<28} {_st('32', bar)} {dim(str(t['count']))}")
    print()
    for key, label in (("github", "GitHub"), ("hackernews", "Hacker News"),
                       ("producthunt", "Product Hunt")):
        s = scan["sources"][key]
        print(bold(label) + dim(f"  · {len(s['items'])} items · {s['status']}"))
        for it in s["items"][:8]:
            print(f"  {_st('36', '→')} {it['name']}")
            if it.get("blurb"):
                print(f"    {dim(it['blurb'][:110])}")
        print()
    print(dim(f"saved → {store.SCAN_FILE}"))
    if args.json:
        with open(args.json, "w") as f:
            json.dump(scan, f, indent=2)
        print(dim(f"json  → {args.json}"))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    idea = args.idea
    if not idea.strip():
        print('error: describe the idea, e.g. whitespace check "my tool idea"')
        return 2
    prev = store.similar_previous_checks(idea)
    if prev and not args.json:
        print(dim("previously checked:"))
        for p in prev:
            print(f"  {p['ts'][:10]}  {verdict_badge(p['verdict'])}  {p['idea'][:70]}")
        print()
    print(bold("checking: ") + idea)
    print(dim("queries: " + " / ".join(novelty.expand_queries(idea))))
    result = novelty.check(idea)
    store.save_check(result)

    print()
    summary = (f"top similarity {result['top_score']:.3f} · "
               f"{result['candidates_examined']} candidates")
    print(f"{verdict_badge(result['verdict'])}  {dim(summary)}")
    print()
    if result["evidence"]:
        print(bold("evidence"))
        for e in result["evidence"][:8]:
            print(f"  {e['score']:.3f}  {e['name']}")
            print(f"         {dim(e['url'])}")
            if e.get("note"):
                print(f"         {dim(e['note'])}")
    else:
        print(dim("no candidates surfaced — nothing to compare against."))
    print()
    print(dim("how to read this: lexical similarity over names/descriptions; "
              "the table is the verdict's evidence, audit the top rows."))
    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=2)
        print(dim(f"json → {args.json}"))
    return 0


def cmd_ledger(args: argparse.Namespace) -> int:
    checks = store.load_checks()
    if not checks:
        print(dim("ledger is empty — run ") + bold("whitespace check \"your idea\""))
        return 0
    print(bold(f"novelty ledger  ({len(checks)} checks)"))
    for c in checks[-args.limit:]:
        score = f"{c['top_score']:.2f}"
        print(f"  {c['ts'][:16]}  {verdict_badge(c['verdict'])}  "
              f"{dim(score)}  {c['idea'][:64]}")
    print(dim(f"\nstored at {store.CHECKS_FILE}"))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    scan = store.load_scan()
    checks = store.load_checks()
    out = report.build(scan, checks, args.out)
    print(bold("report → ") + str(out))
    if not scan:
        print(dim("note: no scan data — run `whitespace scan` for the radar section."))
    return 0


# --- entry point ---


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="whitespace",
        description="Find the whitespace in the AI tool market: trend radar + "
                    "automated novelty gate. Keyless, local, deterministic.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="scan this week's AI-tool trends")
    s.add_argument("--days", type=int, default=14, help="lookback window (default: 14)")
    s.add_argument("--json", default=None, help="also write raw JSON here")
    s.set_defaults(func=cmd_scan)

    c = sub.add_parser("check", help='novelty-gate an idea: whitespace check "my idea"')
    c.add_argument("idea", help="one-line description of the tool idea")
    c.add_argument("--json", default=None, help="write full result JSON here")
    c.set_defaults(func=cmd_check)

    lg = sub.add_parser("ledger", help="list past novelty checks")
    lg.add_argument("--limit", type=int, default=10)
    lg.set_defaults(func=cmd_ledger)

    r = sub.add_parser("report", help="render the dark HTML dossier")
    r.add_argument("--out", default="whitespace-report.html")
    r.set_defaults(func=cmd_report)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
