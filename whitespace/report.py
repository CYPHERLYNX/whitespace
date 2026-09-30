"""Dark HTML dossier: the morning briefing as a single self-contained file.

Design tokens (deliberately restrained — no gradients, no neon):
  bg        #0a0b0d   panel  #121417   line   #22262c
  text      #e8eaed   muted  #9aa1ab   faint  #5f6670
  accent    #3ddc84 (muted green — the "greenfield" signal)
  warn      #f5b942   bad    #f26d6d
Type: system stack, tight headings, uppercase micro-labels. Everything inline,
zero external assets — the file works from disk, over email, anywhere.
"""

from __future__ import annotations

import datetime as dt
import html
from pathlib import Path

CSS = """
:root{
  --bg:#0a0b0d; --panel:#121417; --panel2:#171a1f; --line:#22262c;
  --text:#e8eaed; --muted:#9aa1ab; --faint:#5f6670;
  --accent:#3ddc84; --warn:#f5b942; --bad:#f26d6d;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);
  font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,
  "Helvetica Neue",Arial,sans-serif;
  -webkit-font-smoothing:antialiased;padding:0 0 80px}
.wrap{max-width:1060px;margin:0 auto;padding:0 28px}
header.top{border-bottom:1px solid var(--line);padding:44px 0 30px;margin-bottom:36px}
.kicker{font-size:11px;letter-spacing:.22em;color:var(--accent);
  text-transform:uppercase;font-weight:600;margin-bottom:12px}
h1{font-size:34px;font-weight:700;letter-spacing:-.02em;margin-bottom:8px}
.sub{color:var(--muted);font-size:15px;max-width:640px}
.meta-row{display:flex;gap:18px;margin-top:16px;color:var(--faint);font-size:12.5px}
.meta-row b{color:var(--muted);font-weight:600}
h2.sec{font-size:12px;letter-spacing:.18em;text-transform:uppercase;
  color:var(--muted);font-weight:600;margin:44px 0 18px;
  padding-bottom:10px;border-bottom:1px solid var(--line)}
.theme{display:flex;align-items:center;gap:14px;padding:9px 0;
  border-bottom:1px solid #16191d}
.theme .t-name{width:220px;flex:none;font-weight:600;font-size:14px}
.theme .t-bar{flex:1;height:8px;background:#1a1d22;border-radius:4px;overflow:hidden}
.theme .t-fill{height:100%;background:var(--accent);border-radius:4px;opacity:.85}
.theme .t-n{width:36px;text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}
.src-head{display:flex;align-items:baseline;gap:10px;margin:26px 0 12px}
.src-head h3{font-size:16px;font-weight:650}
.src-head .st{font-size:12px;color:var(--faint)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:16px 18px;margin-bottom:10px}
.card:hover{border-color:#2e333b}
.card .c-name{font-weight:650;font-size:14.5px;margin-bottom:4px}
.card .c-name a{color:var(--text);text-decoration:none}
.card .c-name a:hover{color:var(--accent);text-decoration:underline}
.card .c-blurb{color:var(--muted);font-size:13.5px;margin-bottom:8px}
.card .c-foot{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.pill{font-size:11px;color:var(--muted);background:var(--panel2);
  border:1px solid var(--line);border-radius:20px;padding:2px 10px}
.pill.src{color:var(--faint)}
.check{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:22px;margin-bottom:18px}
.check .idea{font-size:17px;font-weight:650;margin:10px 0 4px;letter-spacing:-.01em}
.check .q{color:var(--faint);font-size:12.5px;margin-bottom:14px}
.verdict{display:inline-block;font-size:11.5px;font-weight:700;letter-spacing:.14em;
  text-transform:uppercase;border-radius:6px;padding:5px 12px;border:1px solid}
.v-GREENFIELD{color:var(--accent);border-color:#1d4a33;background:#0e1a13}
.v-CONTESTED{color:var(--warn);border-color:#4d3d17;background:#1a1509}
.v-OCCUPIED{color:var(--bad);border-color:#4d1f1f;background:#1c0f0f}
table.ev{width:100%;border-collapse:collapse;margin-top:14px;font-size:13.5px}
table.ev th{text-align:left;font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--faint);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--line)}
table.ev td{padding:10px;border-bottom:1px solid #16191d;vertical-align:top}
table.ev tr:last-child td{border-bottom:none}
table.ev a{color:var(--text);text-decoration:none;border-bottom:1px dotted #3a3f47}
table.ev a:hover{color:var(--accent)}
.score{font-variant-numeric:tabular-nums;color:var(--muted);white-space:nowrap}
.note{color:var(--faint);font-size:12.5px}
.empty{color:var(--faint);padding:18px;border:1px dashed var(--line);
  border-radius:10px;text-align:center;font-size:13.5px}
footer{margin-top:56px;padding-top:20px;border-top:1px solid var(--line);
  color:var(--faint);font-size:12.5px;max-width:720px}
footer b{color:var(--muted)}
@media(max-width:640px){.theme .t-name{width:140px}h1{font-size:26px}}
"""


def _ev_rows(evidence: list[dict]) -> str:
    rows = []
    for e in evidence:
        rows.append(
            "<tr>"
            f"<td><a href=\"{html.escape(e['url'])}\">{html.escape(e['name'])}</a>"
            f"<div class=\"note\">{html.escape(e['source'])}{' · ' + html.escape(e['meta']) if e.get('meta') else ''}</div></td>"
            f"<td class=\"score\">{e['score']:.3f}</td>"
            f"<td class=\"note\">{html.escape(e.get('note', ''))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _checks_section(checks: list[dict]) -> str:
    if not checks:
        return '<div class="empty">No ideas checked yet. Run <b>whitespace check "your idea"</b>.</div>'
    parts = []
    for c in checks:
        v = c["verdict"]
        parts.append(
            "<div class=\"check\">"
            f"<span class=\"verdict v-{v}\">{v}</span>"
            f"<div class=\"idea\">{html.escape(c['idea'])}</div>"
            f"<div class=\"q\">checked {html.escape(c['ts'])} · top similarity "
            f"{c['top_score']:.3f} · {c['candidates_examined']} candidates examined</div>"
            "<table class=\"ev\"><tr><th>Candidate</th><th>Score</th><th>Read</th></tr>"
            + _ev_rows(c.get("evidence_full") or c.get("top_evidence", []))
            + "</table></div>"
        )
    return "\n".join(parts)


def _radar_section(scan: dict | None) -> tuple[str, str]:
    if not scan:
        return "", '<div class="empty">No scan yet. Run <b>whitespace scan</b> first.</div>'
    theme_html = []
    max_c = max((t["count"] for t in scan["themes"]), default=1)
    for t in scan["themes"]:
        pct = 100 * t["count"] / max_c
        theme_html.append(
            "<div class=\"theme\">"
            f"<div class=\"t-name\">{html.escape(t['theme'])}</div>"
            f"<div class=\"t-bar\"><div class=\"t-fill\" style=\"width:{pct:.0f}%\"></div></div>"
            f"<div class=\"t-n\">{t['count']}</div></div>"
        )
    src_html = []
    labels = {"github": "GitHub", "hackernews": "Hacker News", "producthunt": "Product Hunt"}
    for key, label in labels.items():
        s = scan["sources"].get(key, {})
        items = s.get("items", [])
        cards = []
        for it in items[:12]:
            pills = "".join(
                f"<span class=\"pill\">{html.escape(th)}</span>" for th in it.get("themes", [])[:3]
            )
            cards.append(
                "<div class=\"card\">"
                f"<div class=\"c-name\"><a href=\"{html.escape(it['url'])}\">{html.escape(it['name'])}</a></div>"
                + (f"<div class=\"c-blurb\">{html.escape(it['blurb'])}</div>" if it.get("blurb") else "")
                + f"<div class=\"c-foot\"><span class=\"pill src\">{html.escape(it.get('meta', ''))}</span>{pills}</div>"
                + "</div>"
            )
        src_html.append(
            f"<div class=\"src-head\"><h3>{label}</h3>"
            f"<span class=\"st\">{len(items)} items · {html.escape(s.get('status', ''))}</span></div>"
            + ("\n".join(cards) if cards else "<div class=\"empty\">source unavailable this run</div>")
        )
    return "\n".join(theme_html), "\n".join(src_html)


def build(scan: dict | None, checks: list[dict], out: str | Path) -> Path:
    """Render the dossier. Checks carry full evidence when passed through."""
    themes_html, radar_html = _radar_section(scan)
    when = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    window = scan.get("window_days", "—") if scan else "—"

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>whitespace — AI tool opportunity radar</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<header class="top">
  <div class="kicker">whitespace · opportunity radar</div>
  <h1>Where is the whitespace?</h1>
  <div class="sub">A scan of this week's AI-tool landscape, fused with novelty
  checks on your own ideas — every verdict backed by named evidence you can audit.</div>
  <div class="meta-row"><span>generated <b>{when}</b></span>
  <span>window <b>{window} days</b></span>
  <span>verdicts <b>{len(checks)}</b></span></div>
</header>

<h2 class="sec">Theme map</h2>
{themes_html if themes_html else '<div class="empty">No scan data.</div>'}

<h2 class="sec">Radar — what launched lately</h2>
{radar_html}

<h2 class="sec">Novelty ledger</h2>
{_checks_section(checks)}

<footer>
<b>How to read this.</b> Similarity is lexical (TF-IDF over names and descriptions),
not semantic — the evidence table is the real output; the verdict is a headline.
<b>GREENFIELD</b> means nothing close surfaced in the searched sources, not that
nothing exists. <b>OCCUPIED</b> means a direct equivalent was found — read the top
rows before building. Sources: GitHub search API, Hacker News Algolia API,
Product Hunt launches via the awesome-product-hunt ledger, web via DuckDuckGo.
All keyless; any source can degrade without breaking the report.
</footer>

</div>
</body>
</html>"""

    out_path = Path(out)
    out_path.write_text(doc)
    return out_path
