# Decision pages

The user decided (2026-11-02) that every decision the placement process asks of them comes as
an HTML page with pictures and the information laid out to decide from, published as a
private Artifact (readable on a phone; the source stays in the run folder). The terminal
message only says that a decision is waiting and gives the link.

## When a page is needed

- The plan (stage 1), and every later version of it.
- A stackup or layer-plan change the escape budget or capacity forces.
- Each hand-reviewed block (stage 3), and each new version of one.
- A conflict between the plan and an architecture decision, a KRT prior or a datasheet.
- Close seeds (stage 5), and any seed choice that trades one blocker for another.
- Each gate FAIL the run cannot fix and the user may accept (stage 6).
- The final placement, before it replaces the repo's board.

Several small questions at one stage go on one page as separate decisions only when they
are independent; otherwise one page per decision.

## What a page holds

`scripts/decision_page.py` builds it from a JSON (its `--help` gives the format):

1. **The question**, in one line, and **why now**: what forces it and what waits on it.
2. **Facts it rests on**, each with its source (a file, a decision record, a datasheet page,
   a measurement and the script that made it).
3. **Options**, two or three, each with:
   - pictures: the board region rendered for that option (see below), at a zoom where pads and
     net names read; the same view for every option so they compare;
   - measures: the numbers that differ between options, each with its limit and status
     (`pass`, `warn`, `fail`, `info`); measures with the same label line up across options in
     one table;
   - gains and costs, short, in the board's terms (mm, A, layers, dollars from a quote).
4. **The recommendation**, with its reason. Say so when there is no clear winner.
5. **How to answer**: reply in the session with the option's letter, or a change to it; a
   comment on the page reaches Claude too.
6. **Sources**.

An option is only on the page if it was measured. Placeholder numbers never go on a page.

## Pictures

- Placement regions: KRT `render_placement.py BOARD --view X0,Y0,X1,Y1 [--side B]
  [--ratsnest-nets NET ...] -o img/<opt>.png` (it writes `<stem>_F.png` and `_B.png` without
  `--side`). Bottom-side views are drawn as seen through the board from above, so both sides
  line up.
- Fast routes: `kicad-cli pcb export svg --mode-single --layers B.Cu,Edge.Cuts
  --exclude-drawing-sheet --fit-page-to-board -o img/<opt>_B.svg BOARD` (SVG keeps tracks sharp
  at any zoom; add `--mirror` for a bottom view as seen from below).
- 3D (heights, the lid, busbars): `kicad-cli pcb render --side bottom --zoom 2 -o img/3d.png BOARD`.
- Datasheet figures: KRT `py_tools/pdf_text.py <pdf> --render N --out img/fig.png --dpi 200`.
  They stay in the run folder's ignored `decisions/img/`, never in a commit.
- Plans and lanes: an SVG drawn over the render (rectangles and lines in board mm).

Keep a page under 15 MB (the builder refuses more): crop with `--view`, prefer SVG for
copper, and JPEG for 3D renders.

## Publishing

1. Write `decisions/<id>-<slug>.json` and its pictures in `decisions/img/`.
2. `python3 scripts/decision_page.py decisions/<id>-<slug>.json` writes the `.html` beside it.
3. Load the `artifact-design` skill once per session before the first publish (the builder's
   page already follows its contract: title, theme tokens, phone width, no external scripts).
4. Publish with the Artifact tool: `file_path` the HTML, `icon` "circuit", a one-sentence
   `description` naming the board and the question. A new version of the same decision is
   republished from the same file path, so its link stays.
5. Tell the user in one line: the decision, the link, and that the run waits for it.
6. On the answer, add a line to `decisions/log.md`: id, date, question, link, answer in the
   user's words, and what changed because of it.
