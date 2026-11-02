# Stage 5: DONE is a fast route with no blocking net, under the board's own rules

KRT's rule stands: a placement is judged by routing it, not by its cost, crossings or
wirelength. Its `judge_seeds.py` fast-routes the seeds the annealer rates best and ranks them
by `quick_score` (floorplan errors and assembly first, then open nets, then joins needed, vias,
copper). This skill keeps that and adds one condition: the fast route is graded again by
KiCad's own DRC with the board's real `.kicad_pro` and `.kicad_dru`, and a placement is DONE
only when both say nothing blocks.

## Why both

On Node60 (V15 run, 2026-11-01) the kept seed's fast route scored 9 open nets in KRT, and
`grade_route.py` against `node60.kicad_pro` and `node60.kicad_dru` found more:

| Found | Count | Why KRT's score missed it |
|---|---|---|
| Vias under a busbar, against `F.Cu under the ... busbar` rules | 53 | `route.py` reads net-filtered `disallow` rules from the sibling `.kicad_dru`, but the fanout and plane steps lay copper with their own search and do not |
| Vias below the board's via floor (`via_diameter`) | 40 | `autoplan.py` routes at the fab's floors (0.25 mm fine via, 0.09 mm clearance) and wrote them into the judging copy's `.kicad_pro`; the board's own are 0.35 mm and 0.10 mm |

Each one is a placement fact: the BGA was under the bar, and its escape only fit with vias the
board does not allow. A seed ranked first on such a route can be the worst one.

## Keep-outs the annealer must see

A `.kicad_dru` rule that forbids other nets' copper in an area also limits parts: a part
whose pads sit in it can only reach out on the layers the rule leaves, and a through via
crosses every layer. On Node60, F.Cu under each busbar takes only the bar's own net, so a
bottom-side part under the bar has no via for any other net. The V15 intent kept parts out of
the busbars on the top side only, and the annealer put U401 (257 balls) under one.

For every such rule area, the plan says which parts may stand under it (on each side), and
the intent gets a keep-out for each side the rule reaches, whose `allow` names exactly those
parts:

```json
{"name": "busbar_vbat_B", "rect": [92.475, 90.075, 217.525, 109.125], "sides": ["B"],
 "allow": ["R201", "Q201", "Q202", "Q203", "Q204", "C2*"],
 "context": {"kind": "copper rule", "source": "node60.kicad_dru: F.Cu under the VBAT_IN busbar",
             "why": "no other-net via under the bar: only parts whose nets leave on B.Cu may sit here"}}
```

Check the result before routing anything: `escape_budget.py` names balls under a rule area;
`gate.py`'s rows do the rest.

## The judging chain

Write `judge_chain.txt` from KRT's `plan-pcb-placement` §3.7, with these changes:

1. **Floors.** The chain routes at the board's own floors: `route.py` and every fanout step
   get the `.kicad_pro` minimums (`--clearance`, track and via sizes as each tool names
   them), not the fab's. Where a BGA's escape needs a finer via or clearance, that is a
   stackup and fab decision for the user (with the price from the fab's quote), recorded in
   the plan and written as a `.kicad_dru` rule scoped to a rule area over the ball field,
   never a board-wide floor change.
2. **Rule areas as native keep-outs.** On the judging copy only, write each DRU-only area as a
   KiCad keep-out, so every step that honours native keep-outs sees it:
   `$KPY -X utf8 py_router/add_rule_area.py fixed.kicad_pcb fixed_judge.kicad_pcb --name
   JUDGE_BUSBAR_VBAT_IN --rect 92.475 90.075 217.525 109.125 --layers F.Cu --forbid tracks vias`.
   (A native keep-out also blocks the bar's own net; that costs the judging route nothing that
   matters.) Never write these into the repo's board: the `.kicad_dru` stays the one rule.
3. **The sibling rules.** Keep the board's `.kicad_dru` beside every board in the chain
   (`copy_board.py` does), so `route.py` reads its net-filtered rules too.

## Grading each fast route

```bash
python3 scripts/grade_route.py s3_fast.kicad_pcb --project <repo>/node60.kicad_pro \
    --rules <repo>/node60.kicad_dru --json s3_rules.json
```

It copies the fast route next to the real project and rules, refills the zones (a level-2
fast route leaves planes unfilled), runs `kicad-cli pcb drc`, and counts as blocking: every
unconnected item, every hit on a custom rule of the rules file, and every short, clearance,
hole, width or via-size error. Silk, dangling vias and library warnings are reported, not
blocking: the full route cleans them up. A type at KiCad's 199-entry cap is a floor, not a
count.

A seed is DONE when its `quick_score` blocking is 0 and `grade_route.py` prints `BLOCKING=0`.
Rank DONE seeds by KRT's key (vias, then copper, then segments). Seeds within KRT's "close"
margin are a decision page: show each one's fast route on both sides, its numbers from both
graders, and where they differ.

## When no seed is DONE

Read what blocks, by name. Hits clustered at one part (a BGA's escape, a connector's pins)
are placement: change the input (a keep-out, a block's pose, a group's side) and place again,
as KRT §3.6 describes. Hits spread thin across the board are routing parameters, and the
placement may be fine: say so with the measurement (KRT's `check_reachability.py` CAGED or
PASSABLE). After three different input changes that do not lower the blocking count, stop and
put the best seed and every remaining blocker on a decision page.
