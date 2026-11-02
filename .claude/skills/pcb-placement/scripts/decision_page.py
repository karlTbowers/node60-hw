#!/usr/bin/env python3
"""Build one decision page for the user (pcb-placement skill).

Every decision the skill puts to the user is a page, never a terminal question: what is
being decided and why now, the facts it rests on, each option with its pictures, its
measurements against their limits and what it gains and costs, a recommendation, and how
to answer. This script turns a decision JSON into one self-contained HTML file (images
embedded), ready to publish as a private Artifact. Standard library only.

    python3 decision_page.py RUN/decisions/D03-u401-position.json [-o RUN/decisions/D03-u401-position.html]

Decision JSON (paths are relative to the JSON file):
{
  "id": "D03",                       short id, also in the run's decisions/log.md
  "name": "U401 position",           page title: 2-4 words naming the thing decided
  "question": "Where should U401 sit?",
  "board": "node60", "stage": "1 Plan", "date": "2026-11-02",
  "why_now": "paragraphs: what forces the decision now, what depends on it",
  "facts": [{"label": "Busbar rule", "value": "only VBAT_IN on F.Cu under the bar", "source": "node60.kicad_dru"}],
  "options": [{
     "key": "A", "name": "Clear of the busbars", "summary": "one paragraph",
     "images": [{"path": "img/A_bottom.png", "caption": "B.Cu, U401 at (150, 60)"}],
     "measures": [{"label": "Balls under a busbar", "value": "0", "limit": "0", "status": "pass"}],
     "gains": ["..."], "costs": ["..."]}],
  "recommendation": {"option": "A", "why": "paragraphs"},
  "answer": "optional: how to answer, if not the default text",
  "sources": ["Omron G6K drawing, rev ...", "..."]
}
`status` is pass, warn, fail or info. Text fields take blank-line paragraphs, `code` and
**bold**. Measures with the same label line up across options in one comparison table.
"""
import argparse
import base64
import html
import json
import mimetypes
import os
import re
import sys

LIMIT_BYTES = 15 * 1024 * 1024

CSS = """
/* Layout: one column of sections; options side by side from 760px, stacked below. */
:root {
  --paper: #f4f6f6; --sheet: #ffffff; --ink: #1c2427; --muted: #5a676c; --rule: #d5dcdd;
  --copper: #a8562f; --copper-soft: #f5e6dd; --pass: #2f7a4b; --warn: #a06a00; --fail: #b3261e;
  --pass-bg: #e3f1e8; --warn-bg: #fbefd6; --fail-bg: #f9e1df; --info-bg: #e9eef0;
  --display: "Archivo Narrow", "Arial Narrow", "Helvetica Neue", Arial, sans-serif;
  --body: "Source Sans 3", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --paper: #121719; --sheet: #1a2124; --ink: #e3e8e9; --muted: #9aa7ab; --rule: #2e383b;
  --copper: #e08a5c; --copper-soft: #3a2519; --pass: #6cc58e; --warn: #e2ad45; --fail: #f08a80;
  --pass-bg: #17301f; --warn-bg: #36290c; --fail-bg: #3a1714; --info-bg: #222b2e; color-scheme: dark } }
:root[data-theme="dark"] {
  --paper: #121719; --sheet: #1a2124; --ink: #e3e8e9; --muted: #9aa7ab; --rule: #2e383b;
  --copper: #e08a5c; --copper-soft: #3a2519; --pass: #6cc58e; --warn: #e2ad45; --fail: #f08a80;
  --pass-bg: #17301f; --warn-bg: #36290c; --fail-bg: #3a1714; --info-bg: #222b2e; color-scheme: dark }
* { box-sizing: border-box }
body { background: var(--paper); color: var(--ink); font: 16px/1.5 var(--body); margin: 0 }
.wrap { max-width: 1180px; margin: 0 auto; padding-block: 28px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 28px }
header { display: grid; gap: 8px; border-bottom: 2px solid var(--copper); padding-bottom: 18px }
.eyebrow { font: 600 12px/1.2 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted);
  display: flex; flex-wrap: wrap; gap: 6px 14px }
.eyebrow b { color: var(--copper); font-weight: 600 }
h1 { font: 600 clamp(26px, 4vw, 38px)/1.15 var(--display); margin: 0; text-wrap: balance }
h2 { font: 600 20px/1.2 var(--display); margin: 0 0 10px; letter-spacing: .01em }
h3 { font: 600 18px/1.25 var(--display); margin: 0 }
p { margin: 0 0 10px; max-width: 68ch } p:last-child { margin-bottom: 0 }
code { font: 13px/1.4 var(--mono); background: var(--info-bg); padding: 1px 5px; border-radius: 3px; overflow-wrap: anywhere }
section { min-width: 0 }
.facts { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 1px; background: var(--rule);
  border: 1px solid var(--rule) }
.fact { background: var(--sheet); padding: 10px 12px; display: grid; gap: 2px; min-width: 0 }
.fact .k { font: 600 11px/1.3 var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--muted) }
.fact .v { font-weight: 600; overflow-wrap: anywhere }
.fact .s { font-size: 13px; color: var(--muted); overflow-wrap: anywhere }
.options { display: grid; gap: 18px; grid-template-columns: 1fr }
@media (min-width: 760px) { .options.n2 { grid-template-columns: 1fr 1fr } .options.n3 { grid-template-columns: repeat(3, 1fr) } }
.opt { background: var(--sheet); border: 1px solid var(--rule); padding: 16px; display: grid; gap: 12px; align-content: start; min-width: 0 }
.opt.rec { border-color: var(--copper); box-shadow: inset 0 3px 0 var(--copper) }
.opt-head { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap }
.key { font: 700 14px/1 var(--mono); color: var(--sheet); background: var(--ink); padding: 5px 8px }
.opt.rec .key { background: var(--copper) }
.tag { font: 600 11px/1 var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--copper) }
figure { margin: 0; display: grid; gap: 4px }
figure button { all: unset; cursor: zoom-in; display: block; border: 1px solid var(--rule); background: var(--paper) }
figure button:focus-visible { outline: 2px solid var(--copper); outline-offset: 2px }
figure img { display: block; width: 100%; height: auto; max-width: 100% }
figcaption { font-size: 13px; color: var(--muted) }
ul { margin: 0; padding-left: 18px } li { margin: 2px 0 }
.gc { display: grid; gap: 10px; grid-template-columns: 1fr 1fr } @media (max-width: 480px) { .gc { grid-template-columns: 1fr } }
.gc h4 { font: 600 11px/1.3 var(--mono); letter-spacing: .06em; text-transform: uppercase; margin: 0 0 4px; color: var(--muted) }
.table { overflow-x: auto; border: 1px solid var(--rule); background: var(--sheet) }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--rule); vertical-align: top }
th { font: 600 12px/1.3 var(--mono); letter-spacing: .04em; color: var(--muted); background: var(--paper) }
td.lim { font: 13px/1.4 var(--mono); color: var(--muted); white-space: nowrap }
.chip { display: inline-block; font: 600 13px/1.3 var(--mono); padding: 2px 7px; border-radius: 3px; background: var(--info-bg) }
.chip.pass { background: var(--pass-bg); color: var(--pass) } .chip.warn { background: var(--warn-bg); color: var(--warn) }
.chip.fail { background: var(--fail-bg); color: var(--fail) }
.callout { background: var(--copper-soft); border-left: 4px solid var(--copper); padding: 16px 18px }
.answer { background: var(--sheet); border: 1px dashed var(--copper); padding: 16px 18px; display: grid; gap: 8px }
.answer .opts { display: flex; flex-wrap: wrap; gap: 8px }
.answer .opts span { font: 600 14px/1 var(--mono); border: 1px solid var(--rule); padding: 8px 10px; background: var(--paper) }
.sources li { font-size: 14px; color: var(--muted); overflow-wrap: anywhere }
footer { font: 12px/1.5 var(--mono); color: var(--muted); border-top: 1px solid var(--rule); padding-top: 12px }
#zoom { position: fixed; inset: 0; background: rgba(10, 14, 15, .9); display: grid; place-items: center; z-index: 20;
  padding: max(16px, env(safe-area-inset-top, 0px)) max(16px, env(safe-area-inset-right, 0px)) max(16px, env(safe-area-inset-bottom, 0px)) max(16px, env(safe-area-inset-left, 0px)); cursor: zoom-out }
#zoom img { max-width: 100%; max-height: 100%; background: #fff }
@media (prefers-reduced-motion: no-preference) { .opt { transition: border-color .15s } }
"""

JS = """
const z = document.getElementById('zoom'), zi = z.querySelector('img');
document.querySelectorAll('figure button').forEach(b => b.addEventListener('click', () => {
  zi.src = b.querySelector('img').src; zi.alt = b.querySelector('img').alt; z.hidden = false; z.focus(); }));
z.addEventListener('click', () => { z.hidden = true; });
document.addEventListener('keydown', e => { if (e.key === 'Escape') z.hidden = true; });
"""


def inline(text):
    t = html.escape(str(text))
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    return t


def paras(text):
    if not text:
        return ""
    return "".join(f"<p>{inline(p.strip())}</p>" for p in re.split(r"\n\s*\n", str(text)) if p.strip())


def data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    if path.lower().endswith(".svg"):
        mime = "image/svg+xml"
    return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()


def chip(status, value):
    s = (status or "info").lower()
    s = s if s in ("pass", "warn", "fail") else "info"
    return f'<span class="chip {s}">{inline(value)}</span>'


def build(d, base):
    opts = d.get("options", [])
    rec = (d.get("recommendation") or {}).get("option")
    missing = []

    def fig(img):
        p = os.path.join(base, img["path"])
        if not os.path.exists(p):
            missing.append(img["path"])
            return f'<figure><figcaption>Missing picture: {inline(img["path"])}</figcaption></figure>'
        cap = inline(img.get("caption", ""))
        return (f'<figure><button type="button" aria-label="Enlarge: {cap}"><img src="{data_uri(p)}" '
                f'alt="{cap}" loading="lazy"></button><figcaption>{cap}</figcaption></figure>')

    cards = []
    for o in opts:
        is_rec = o.get("key") == rec
        gains = "".join(f"<li>{inline(g)}</li>" for g in o.get("gains", []))
        costs = "".join(f"<li>{inline(c)}</li>" for c in o.get("costs", []))
        cards.append(
            f'<article class="opt{" rec" if is_rec else ""}" id="option-{html.escape(str(o.get("key")))}">'
            f'<div class="opt-head"><span class="key">{inline(o.get("key", "?"))}</span>'
            f'<h3>{inline(o.get("name", ""))}</h3>{"<span class=tag>Recommended</span>" if is_rec else ""}</div>'
            f'{paras(o.get("summary"))}{"".join(fig(i) for i in o.get("images", []))}'
            f'<div class="gc"><div><h4>Gains</h4><ul>{gains or "<li>-</li>"}</ul></div>'
            f'<div><h4>Costs</h4><ul>{costs or "<li>-</li>"}</ul></div></div></article>')

    labels = []
    for o in opts:
        for m in o.get("measures", []):
            if m["label"] not in labels:
                labels.append(m["label"])
    table = ""
    if labels:
        head = "".join(f"<th>{inline(o.get('key'))} · {inline(o.get('name', ''))}</th>" for o in opts)
        body = []
        for lab in labels:
            cells, limit = [], ""
            for o in opts:
                m = next((m for m in o.get("measures", []) if m["label"] == lab), None)
                if m:
                    limit = limit or m.get("limit", "")
                    cells.append(f"<td>{chip(m.get('status'), m.get('value', ''))}</td>")
                else:
                    cells.append("<td>-</td>")
            body.append(f"<tr><td>{inline(lab)}</td><td class=lim>{inline(limit)}</td>{''.join(cells)}</tr>")
        table = (f'<section><h2>Measured</h2><div class="table"><table><thead><tr><th>Check</th><th>Limit</th>{head}'
                 f'</tr></thead><tbody>{"".join(body)}</tbody></table></div></section>')

    facts = "".join(
        f'<div class="fact"><span class="k">{inline(f["label"])}</span><span class="v">{inline(f["value"])}</span>'
        + (f'<span class="s">{inline(f["source"])}</span>' if f.get("source") else "") + "</div>"
        for f in d.get("facts", []))
    r = d.get("recommendation") or {}
    keys = "".join(f"<span>{inline(o.get('key'))}: {inline(o.get('name', ''))}</span>" for o in opts)
    answer = d.get("answer") or ("Reply in the Claude session with the option's letter, or with a change to one. "
                                 "A comment on this page reaches Claude too. Nothing goes ahead until you answer.")
    sources = "".join(f"<li>{inline(s)}</li>" for s in d.get("sources", []))
    n = min(len(opts), 3)
    page = f"""<title>{html.escape(d.get('name', d.get('id', 'Decision')))}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo+Narrow:wght@600;700&family=JetBrains+Mono:wght@400;600;700&family=Source+Sans+3:wght@400;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header>
  <div class="eyebrow"><b>{inline(d.get('id', ''))}</b><span>{inline(d.get('board', ''))}</span><span>Placement · {inline(d.get('stage', ''))}</span><span>{inline(d.get('date', ''))}</span></div>
  <h1>{inline(d.get('question', ''))}</h1>
</header>
<section><h2>Why this is decided now</h2>{paras(d.get('why_now'))}</section>
{f'<section><h2>Facts it rests on</h2><div class="facts">{facts}</div></section>' if facts else ''}
<section><h2>Options</h2><div class="options n{n}">{''.join(cards)}</div></section>
{table}
{f'<section class="callout"><h2>Recommendation: {inline(r.get("option", ""))}</h2>{paras(r.get("why"))}</section>' if r else ''}
<section class="answer"><h2>How to answer</h2><p>{inline(answer)}</p><div class="opts">{keys}</div></section>
{f'<section><h2>Sources</h2><ul class="sources">{sources}</ul></section>' if sources else ''}
<footer>Node60 pcb-placement skill · decision {inline(d.get('id', ''))} · built from {inline(os.path.basename(d.get('_src', '')))}</footer>
</div>
<div id="zoom" hidden tabindex="-1"><img alt=""></div>
<script>{JS}</script>
"""
    return page, missing


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("decision")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    d = json.load(open(a.decision))
    d["_src"] = a.decision
    for k in ("id", "name", "question", "options"):
        if not d.get(k):
            print(f"ERROR: the decision has no '{k}'", file=sys.stderr)
            return 2
    if len(d["name"].split()) > 5:
        print("WARN: 'name' is the page title: 2-4 words naming the thing decided", file=sys.stderr)
    page, missing = build(d, os.path.dirname(os.path.abspath(a.decision)))
    out = a.out or os.path.splitext(a.decision)[0] + ".html"
    open(out, "w", encoding="utf-8").write(page)
    size = os.path.getsize(out)
    for m in missing:
        print(f"WARN: picture not found: {m}", file=sys.stderr)
    print(f"wrote {out} ({size / 1024:.0f} KB)")
    if size > LIMIT_BYTES:
        print("ERROR: over 15 MB; use fewer or smaller pictures (crop with --view, or JPEG)", file=sys.stderr)
        return 1
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
