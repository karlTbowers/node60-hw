---
name: pcb-placement
description: DropOut's PCB placement process for Node60 (and later boards). A short written plan first (stackup, layers, heat and quiet zones, critical nets with lanes, block ports, enclosure keep-outs and height limits), read-only checks (part heights from model bodies, BGA escape budget, layer capacity, each switcher's hot loop against its datasheet), the critical blocks composed by hand as pose tables with a reason per part, KiCadRoutingTools' annealer placing the rest, a placement gate table, and DONE only when a fast route has no blocking net under the board's own copper rules. Every decision put to the user is an HTML decision page with pictures. Use it to place, re-place or check the placement of a board, to plan a placement, to review a block, or when asked where parts should go.
---

# PCB placement

The annealer in KiCadRoutingTools (KRT) proposes; the plan, the hand-reviewed blocks and
the gate decide. KRT places a board well by function but cannot know what the board's
enclosure, copper rules and critical links demand: on Node60 its placement passed every KRT
check and still left 9 nets open, because it put the BGA under a busbar where the board's
rules allow no other net's via. So the process here adds what KRT cannot see, before and
after it runs, and asks the user at every decision with a page they can judge from.

Where each part of this comes from, and what was left out, is in `references/sources.md`.
The lessons that shaped it are in `references/lessons.md`; read it once before a run.

## Rules

1. **Decisions are the user's, on a decision page.** Whenever the run needs the user to
   choose, approve or accept something, build a decision page (`references/decision-pages.md`)
   and publish it as a private Artifact; never ask in the terminal alone. Stop until they
   answer, and log the answer in `decisions/log.md`.
2. **Never change an architecture decision** (Node60: the `DEC-*` records and the board facts
   in `CLAUDE.md`) on your own. A placement that needs one changed is a decision page that
   says so.
3. **Mechanical facts come from the repo or the user**, never from a guess: outline, connector
   poses, keep-outs, heights. Mark anything assumed as assumed, in the plan.
4. **The board's own rules judge copper.** `.kicad_pro` floors and `.kicad_dru` rules are the
   spec for every route that judges a placement. A judging route that lowers a floor or ignores
   a rule area is not evidence (`references/fast-route.md`).
5. **Read-only until the gate passes.** Work on copies in the run folder. The human's board is
   replaced only when the gate passes and the user accepts the placement on a decision page.
   Don't run anything while KiCad has the board open (`~node60.kicad_pcb.lck`).
6. **Nothing moves silently.** An approved block keeps its pose table. If the annealer or a
   repair moves a core part, the block goes back to the user as a new version.

## Tools

- `$KPY` is KiCad's bundled Python (it has `pcbnew`):
  `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`.
  Its stderr carries harmless wx "Debug:" and "assert" lines.
- KRT: `~/Dev/KiCadRoutingTools` (MIT). Run its tools from that folder with `$KPY -X utf8`.
  Its `plan-pcb-placement` skill (`.claude/skills/plan-pcb-placement/SKILL.md`) is the manual
  for the annealer steps below; read its §2–3.7 and `references/placement-lessons.md` before
  writing groups and intent.
- This skill's scripts, in `scripts/` (each prints its own `--help`):

| Script | Reads | Says |
|---|---|---|
| `part_heights.py` | board | each part's height from its 3D model body, against a limit |
| `escape_budget.py` | board, `.kicad_dru` | a BGA's rings, tracks per channel, layers needed, rule areas over its balls |
| `layer_capacity.py` | board, `.kicad_dru` | connection demand against tracks that fit, per window of each cut |
| `hot_loop.py` | board, switcher spec | each switcher's input cap, inductor and feedback parts against its datasheet |
| `block_poses.py` | board, pose tables | extract, apply, copy and check hand-reviewed blocks |
| `pose_search.py` | board, pose spec | legal poses for parts, searched in one process; KRT checks only the result |
| `grade_route.py` | fast-routed board, `.kicad_pro`, `.kicad_dru` | KiCad DRC with the board's own rules: open nets, custom-rule hits |
| `gate.py` | board, `plan.json` | the placement gate table (`gate.md`) |
| `decision_page.py` | decision JSON, pictures | one self-contained decision page |

## The run folder

`placement/<run>/` in the board repo (`<run>` = date and a word: `2026-11-02-v15`). Copy boards
into it with KRT's `py_router/copy_board.py` (it carries `.kicad_pro` and `.kicad_dru`), never a
bare `cp`. Copy `assets/run.gitignore` to `placement/<run>/.gitignore`: the records (plan, block
tables, decisions, gate, report) are committed with the placement; boards, renders and route
folders are not.

```
plan.md  plan.json  switchers.json           stage 1
heights.json  escape_<ref>.json              stage 2
blocks/<id>.poses.json  blocks/<id>.png      stage 3
groups.json  intent.json  s<S>.*  judge.json stage 4 (KRT's names)
s<S>_fast.*  s<S>_rules.json                 stage 5
gate.md  gate.json  REPORT.md                stage 6
decisions/<id>.json  decisions/img/  decisions/log.md
```

## Stages

### 1. Plan

Write `plan.md` (for the user) and `plan.json` (for the scripts) from `references/plan.md`.
On a board that has them, most answers are already in the repo: Node60's are in `CLAUDE.md`,
the architecture site and `scripts/place_connectors.py` (`references/node60.md` lists them).
The plan covers, each item with its source:

- **Stackup and layer plan**: layer count, thickness, which layers are planes and which carry
  signals, and whether the stackup is decided or open (an open stackup is a decision page
  once the escape budget is known).
- **Plane layers and signal windows**: for every plane layer, whether signals may use it and
  where. Each plane layer is power-only (no tracks; through vias still pass) or has a signal
  window: a rectangle where the plane is not poured and signal tracks may run, placed where the
  plane carries little current (away from the source-to-load paths), with its cost from the
  plane model (supply resistance to each load with and without the window) on the plan's
  decision page. Recorded as `plane_windows` in `plan.json` (`references/plan.md`), drawn on the
  board by `scripts/draw_rule_areas.py`, used by the fast route, and checked by the gate. Never
  leave it implicit: a router that may use a plane layer anywhere will cut the plane where the
  current flows (Node60, 2026-11-03: user, D17).
- **Fixed parts**: connectors, mounting parts, the debug header, with pose and source; how
  they get onto the board (Node60: `place_connectors.py`).
- **Enclosure keep-outs and height limits**: per side and area, with what may stand in each
  (busbars, lid bosses, the floor under bottom-side parts).
- **Heat zones and quiet zones**: what dissipates and where it goes; what is noisy (switch
  nodes) and what must stay away from it (clocks, sense lines, the critical link).
- **Critical nets**, each with its parts, the layer(s) it may use, its lane (from which
  block's port to which), its length or loop budget, and the rule it follows.
- **Blocks and ports**: which blocks are hand-reviewed (stage 3), and for each the edge its
  external nets leave from.
- **Net classes and high-current pads**: the class each rail and critical net needs, and
  each pad where a high current changes layer (current, current per via).
- **Assembly**: which sides are assembled, the fiducials, and anything about heavy parts on
  the second side.

**Decision:** the plan, on one decision page (the board drawn with its fixed parts, keep-outs,
zones and lanes; `references/plan.md` says how to draw it). Nothing is placed before the user
approves it. A later change to the plan is a new version and a new page.

### 2. Read-only checks before placing

On the board with only its fixed parts placed (`fixed.kicad_pcb`):

- `part_heights.py fixed.kicad_pcb --json heights.json`: every part's height from its model's
  body. Each part without a model gets a datasheet height in `plan.json`'s `declared_heights`
  (with its source), never a guess. These heights feed KRT's brief `heights[]` and the
  intent's height-limited keep-outs (`max_height_mm`), so the annealer respects them.
- `escape_budget.py` on every BGA: layers needed against the plan's signal layers. A shortfall
  is a stackup decision page now, not a routing surprise later.
- `hot_loop.py` spec for every switcher (`switchers.json`): pins and limits from the datasheet's
  layout section, with the document, revision and figure as `source` (`references/blocks.md`).
- Every rule area the enclosure or the `.kicad_dru` imposes becomes an intent keep-out the
  annealer reads (`references/fast-route.md`, "Keep-outs the annealer must see"): which parts
  may stand under a busbar is a plan item, decided by what their nets can still reach.

### 3. Critical blocks, by hand

For each block the plan names (on Node60: the T1S line interface, both bucks, the LM74910
power entry with its shunt and the INA228, the MCU crystal; one output switch channel, copied
twice), compose it on a copy and write its pose table with a reason for every part
(`references/blocks.md`): the datasheet's layout figure and text first, the reference design
next, the house rules last. Switching stages use KRT's `fit_template.py` to seat the datasheet
layout; check them with `hot_loop.py`. Identical channels are composed and reviewed once, then
copied (`block_poses.py copy`, KRT `place_pose.py replicate`), and their copies are checked, not
reviewed again. A copy that lands on a neighbour (a test point on a connector, a resistor a
hair inside a courtyard) gets its flex parts moved by `pose_search.py`.

**Decision:** one page per block (a zoomed render of each side with net names, the pose table's
reasons, the hot-loop rows, what the arrangement gives up). Approve sets `approved` in its table.

### 4. Place the rest with KRT

Follow KRT's `plan-pcb-placement` §3.1–3.6 on the run folder: lock the fixed parts, emit the
intent, write `groups.json`, declare edges, covers, keep-outs and templates, then
`place_simple.py` over its seeds. What this skill adds:

- Approved blocks are held: a block whose position the plan fixes is applied
  (`block_poses.py apply`) and locked; a switching stage may instead ride as its KRT template.
- After placing, screen each judged seed before routing it: `block_poses.py check` on every
  approved block, `escape_budget.py` on every BGA, `hot_loop.py`, `layer_capacity.py`. A seed
  that moves a core part, covers balls or breaks a hot-loop limit is repaired or dropped
  (KRT §3.6 "when no seed can be judged"), and every repair move is logged in REPORT.md.
- On each chip the placement crowds (every BGA and QFN), `check_reachability.py --part REF`
  (KRT v0.24.0) before the fast route: how many of its signal nets can leave at once.
- Repairs and nudges go through `pose_search.py`: one spec lists the parts, their search
  radius, rotations and any `require` (e.g. a GND test point within 12 mm of its pin); it loads
  the board once, screens every pose in memory and runs `check_floorplan` and
  `check_assembly` once, on the result (`--verify`). Never a shell loop that runs KRT's tools
  per pose: about a minute a pose, against seconds for the whole search.

### 5. Fast route, judged by the board's own rules

Fast-route the screened seeds with KRT's `judge_seeds.py`, from a judging chain that keeps the
board's floors and sees every rule area, then grade each fast route with `grade_route.py`
against the board's real `.kicad_pro` and `.kicad_dru` (`references/fast-route.md`). DONE needs
both: KRT's `quick_score` blocking 0 and `grade_route.py` BLOCKING 0. When seeds are close,
the choice between them is a decision page.

Before a large run, check for a KRT update and install it; then one KRT version and one batch at a time: `references/fast-route.md`, "One KRT version, one batch
at a time". The baseline is routed in the same batch as what it is compared with.

### 6. Placement gate

`$KPY scripts/gate.py <kept seed> --plan plan.json --fast-route <its fast route> --fast-score
<its score>` writes `gate.md` (`references/gate.md` explains every row). A FAIL goes back to the
stage that owns it. A FAIL the run cannot fix, and the user is willing to accept, is a decision
page; their acceptance goes into `plan.json`'s `accepted` with the decision id, and the row then
reads ACCEPTED.

**Decision:** the placement itself, with the gate table, renders of both sides and the fast
route. On approval, the kept seed (never a fast-routed board) replaces the board in the repo on a
branch, with the run's records, in a PR.

## Small moves of free parts

A review that only nudges passives (a pull-up to the pin or plane it belongs with, a decap back to
its chip, a supply stub shortened) doesn't re-run stages 1 to 6. Worked example:
`placement/2026-11-12-passives/` (Node60). It still keeps rules 1, 2, 5 and 6.

1. **Find candidates from the board, not by eye.** For every two-pad part: what each pad's net is,
   how far it stands from the pin it serves, and whether its supply pad stands over that supply's
   plane on some layer (the example's `passives.py` and `plane_at.py`). Measure the copper already
   drawn for it (track and vias per supply net, and where).
2. **One attempt, one spec, one copy.** Each move is a small JSON (parts with their new poses,
   copper to delete and add, the reason) applied to a copy made with `copy_board.py`; the repo's
   board is not touched. Number the attempts and keep the ones that were superseded or rejected,
   with why.
3. **Screen each copy**, in this order: `block_poses.py check` against every approved block table (a
   core part that moved makes the attempt a block change, which is the user's decision on a page);
   KiCad DRC with the board's own rules, refilled, compared with main's (0 new errors, and read the
   unconnected and dangling changes); `check_floorplan` and `check_assembly` with the intent, under
   `KRT_PY`; `check_reachability --part` on each chip a moved part now stands beside.
4. **Pictures, labelled.** The same region before and after for every attempt, moved parts ringed,
   the plane under them tinted, kept in the study folder for the user's review.
5. **Judge by a fast route** only what passed the screens: baseline and attempts in one batch, each
   repeated. Supply nets say nothing there (KRT routes them pad to pad across the planes); read the
   blocking count and the moved parts' own signal nets.
   Read each routed board with KRT's `py_tools/route_review.py` (it names the pad every open net
   is disconnected at, so a net open only at a parked test point is told from one open at a chip,
   and lists the nets with the most vias and the longest detours), and compare the moved nets
   across boards with `py_tools/render_nets.py -o OUT.png --nets ... main=BASE attempt=BOARD`
   (one panel per board, vias and length per panel). Both tried 2026-11-12: 2 to 20 s a board.
   Before drawing a supply stub or any other join by hand, `py_tools/check_join.py BOARD NET
   x,y,layer ... via:x,y` checks it against the board's tracks, vias and pads; it does not see
   pours, so a join that cuts a zone reads CLEAN and KiCad's refill and DRC still judge that.
6. **Decide on a page.** The attempts go to the user as one decision page. Landing an accepted move
   goes through the records that draw the board (`power_shapes.json`, the block tables), on a
   branch, with CI's DRC.

## Hand-back

- `REPORT.md`: the gate table first; the plan version; each block with its approval date;
  the seeds, which were screened out and why, and the kept one; every repair move; the fast
  route's numbers from both graders; each decision with its link and answer; what was assumed.
- The decision log, with every page's Artifact link.
- What routing inherits: the critical-net lanes, the via sites reserved at high-current pads,
  the BGA escape plan, and the rule areas the router must be given.
