# Placement run 2026-11-02-bars: report

Node60 on the v15 board (230 × 110 × 2.0 mm, 1/8" × 3/4" busbars, DEC-025), placed with the
`pcb-placement` skill. The placement is on `node60.kicad_pcb` in this run's PR (decision D09, A).

## Gate

- Date: 2026-11-02; KiCad 10.0.7; board sha256 0670a4fe0a962bf1…
- Verdict: **NOT PASSED**

| Check | How it is measured | Status | Result |
|---|---|---|---|
| Buildable | KRT check_assembly --baseline (parts on the board, courtyards, bodies, pads) | FAIL |   VERDICT: NOT BUILDABLE / EXIT=4 |
| Floorplan intent | KRT check_floorplan --intent (edges, groups, templates, keep-outs, decaps) | PASS | 0 error(s) |
| Schematic parity | kicad-cli pcb drc --schematic-parity (field mismatches warn) | FAIL | footprint_symbol_field_mismatch 199, missing_footprint 2, footprint_symbol_mismatch 56 |
| Heights, B side, whole board | part_heights.py: model body, limit 6.17 mm (CLAUDE.md: board 6.17 mm off the floor (K501 5.2 mm accepted at 0.97 mm, user 2026-11-01)) | PASS | none over |
| Heights, F side, under the low lid | part_heights.py: model body, limit 9.0 mm (CLAUDE.md: 9.0 mm under the low lid above the board; the output and T1S headers stand under the raised front band and T1S hood (1 mm above the tallest header), not the low lid) | PASS | none over |
| Heights, F side, lid bosses, Ø8 mm at each SurLok M4 hole | part_heights.py: model body, limit 5.03 mm (scripts/enclosure_geometry.py v15: boss ends 16.2 mm, board top 11.17 mm) | PASS | none over |
| BGA escape U401 | escape_budget.py: layers needed vs planned, nothing over the ball field | PASS | diagonal gap 0.791 mm -> a 0.45 mm via between four balls: fits / deepest signal ring 8, 2 ring(s) per layer -> 4 signal layer(s) needed; 4 available (F.Cu, In2.Cu, In3.Cu, B.Cu) |
| Layer capacity | layer_capacity.py: MST demand vs tracks per 10 mm window | PASS | 0 window(s) over 100 % (ERROR), 0 over 60 % (WARN) |
| Switcher hot loops | hot_loop.py against each datasheet's layout limits | PASS | 0 FAIL |
| Critical blocks | block_poses.py check: core parts exact, flex within allowance, approved | PASS | power: 13 parts, 0 off their table pose; approved 2026-11-02 (D04); t1s: 19 parts, 0 off their table pose; approved 2026-11-02 (D05); buck_1v5: 12 parts, 0 off their table pose; approved 2026-11-02 (D06); buck_3v3: 9 parts, 0 off their table pose; approved 2026-11-02 (D06); crystal: 5 parts, 0 off their table pose; approved 2026-11-02 (D07); u701: 22 parts, 0 off their table pose; approved 2026-11 |
| Fiducials | FID parts per assembled side; 2 or 4, not symmetric under a half turn | PASS | F: 3; B: 3 |
| Net classes | each planned class assigned to its nets, track width at least its minimum | PASS | 4 planned class row(s) on the board |
| Vias at high-current layer changes | free via sites within reach of each pad vs ceil(I / I per via) | PASS | 9 pad(s) have room |
| Fast route, KRT score | quick_score: blocking (open nets, floorplan, assembly) | FAIL | blocking 2, joins_needed 1 |
| Fast route, board's own rules | grade_route.py: KiCad DRC with the board's .kicad_pro and .kicad_dru | FAIL |   unconnected items : 1  nets: 3V3_MAIN /   not blocking (silk, dangling, library, mask): 616 /   NOTE: lib_footprint_issues, silk_overlap, silk_over_copper reached KiCad's 199-entry report cap; the count is a floor / BLOCKING=1 |

The fast-route rows are judge_composed3's route, of the composed board before C803's last 0.05 mm and TP402's 0.2 mm moves.

The four failing rows were accepted in D09 (user, 2026-11-02):

| Row | Why it fails | Accepted because | Follow-up |
|---|---|---|---|
| Buildable | BB901/BB902's tie pads sit inside the REDCUBE terminals' pads (4 overlaps, 2.56 mm² each); KRT can't waive pads on locked parts | By design (D02): the net-tie bar is how the board shows the busbar joining its terminals. KiCad's DRC accepts it | none |
| Schematic parity | 199 field mismatches, 2 missing footprints (C207, L201), 56 footprint/symbol mismatches | The same counts on main's board before this run; none come from placement. CI (errors only) passes | a schematic and library pass before routing sign-off |
| Fast route, board's own rules | 1 open: U501 pin 29 (3V3_MAIN) | Router churn on the PHY's 0.5 mm south edge, not a placement defect (below) | hand-route the PHY's south edge first |
| Fast route, KRT score | 2 blocking: U501 pin 29, and VBAT_IN's J901–J910 join | The join is made only by the busbar | none |

The skill's DONE rule (KRT blocking 0 and board-rule BLOCKING 0) is **not met**; D09 accepted
the run without it.

## Plan

Plan v2 (`plan.md`, `plan.json`): v1 approved with D01 B (tented vias of any net allowed under
the bars; `node60.kicad_dru` and DEC-025 updated); v2 moved the busbar join and fiducials to
their own decisions (D02, D03) and dropped the U401 scoped rule (the BGA escapes at the board's
0.1 mm track and 0.15 mm clearance).

## Blocks

| Block | Anchor | Parts | Approved | Notes |
|---|---|---|---|---|
| Power entry | R201 | 35 | D15, 2026-11-03 (replaces D04) | Re-ordered to flow east; BVR4026 Kelvin shunt, INA228 beside it |
| T1S line interface and PHY | K501 | 20 | D16, 2026-11-03 (replaces D05) | PHY chain north of the trunk midpoint, K501 on it; stub 12.5/12.5 mm |
| Buck 1V5_CORE | U303 | 11 | D06, 2026-11-02 | divider on the SW side, 2.55 mm from the switch node |
| Buck 3V3_MAIN | U302 | 8 | D06, 2026-11-02 | |
| MCU crystal | Y401 | 5 | D07, 2026-11-02 | C424, C425 to their pins; TP407 7 mm away; no-via rule on the crystal nets |
| Output cell 3-4 | U701 | 21 | D13, 2026-11-03 (D08 turned to 0°) | the reviewed cell, centred between J906/J907 pin 1 |
| Output cell 1-2 | U601 | 21 | D13, 2026-11-03 | copy at 0°, centred between its headers |
| Output cell 5-6 | U801 | 21 | D13, 2026-11-03 | copy at 0°, centred between its headers |

Every block is on its table pose on `node60.kicad_pcb` (`block_poses.py check`).

## Seeds

The annealer (stage 4) was **not re-run**: the rest of the board keeps main's placement (the
KRT runs behind PRs #34–#38), and the blocks were composed on top of it (`candidate.kicad_pcb`
= main + power block, `composed.kicad_pcb` = candidate + crystal and output cells). No seeds
were screened out.

## Moves after the blocks were composed

All by `pose_search.py` (one process, KRT's checks once on the result):

| Part | Move | Why |
|---|---|---|
| TP806 | (220.6, 121.2) → (231.0, 107.75), turned 270° → 0° | the copied cell put it on J908 |
| R605, R705, R805 | 0.1 mm south | courtyards touched their switch's by 0.07 mm |
| C803 | 0.3 mm, then 0.05 mm north (after D08; recorded in `out_8x.poses.json`) | courtyard on J908's; the second move so KRT's measure reads no overlap |
| TP402 | 0.2 mm west | courtyard touched TP407's (0.06 mm²) after D07 moved TP407 |

62 parts differ from main in all.

## Fast routes

| Run | Chain | KRT open | Board rules BLOCKING |
|---|---|---|---|
| judge_cand_a | main + power block | 1 (0 after a targeted pass) | 1 (0 after) |
| judge_composed | composed, U801 at the annealer's pose | 3 (SW3_FLT_L, REFCLK, IRQ_L) | 3 |
| judge_composed2 | U801 moved | 2 (RBIAS, 3V3_MAIN pin 29) | 2 |
| judge_composed3 | REFCLK, RBIAS routed first | 1 (3V3_MAIN pin 29) | 1 |
| judge_composed4 | 3V3_MAIN, then REFCLK, RBIAS first | 3 (REFCLK, 3V3_MAIN, MODE0; the T1S pair lost on the way) | 3 |
| judge_composed5 | REFCLK, RBIAS after the T1S pair (the chain now) | 2 (REFCLK, CRS_DV) | 2 |

Every open pin reads PASSABLE (`check_reachability`). U501's south edge (pins 26–31: RBIAS,
REFCLK, an unused pin, 3V3_MAIN, the T1S pair) is 0.5 mm pitch; each order closes some nets
and loses others. Pin 29: the QFN fan-out gives it a stub; the bulk pass rips all of 3V3_MAIN
to make room and restores 67 of its 68 connections. The crystal nets had 0 vias in every
composed run; every output, sense and fault net routed.

## Decisions

See `decisions/log.md` (D01–D09, each with its page and answer).

## Assumptions

- Heights come from the parts' 3D model bodies; the limits from `scripts/enclosure_geometry.py`
  v15 and CLAUDE.md.
- The fast route is evidence for the placement, not the routing.
- The judging chain strips BB901/BB902 and closes the bar areas to tracks (KRT does not read
  `node60.kicad_dru`), and routes the crystal nets first on B.Cu, outside the BGA fan-out.

## What routing inherits

- **T1S pair first**, as the chain does (DEC-012 rev. B order; 0.165 mm / 0.15 mm in the
  T1S_100R class).
- **Crystal nets** on B.Cu with no via (`node60.kicad_dru` rule; NXP S32K3 HDG §3.2); route
  MDC (U401 ball N3, 2.3 mm from the oscillator) away from it.
- **U501's south edge by hand**: pin 29 straight out to a via, then REFCLK and RBIAS; also IRQ_L,
  and U401's 3V3_MAIN balls H6, H7, L8 and K11 (the final fast route left these open, all PASSABLE).
- **BGA escape**: 4 signal layers (F.Cu, In2, In3, B.Cu), 0.1 mm track, 0.15 mm clearance,
  0.45/0.25 mm vias between balls.
- **Via room** at all 9 high-current pads (`gate.md`).
- **Rule areas**: `BUSBAR_VBAT_IN` and `BUSBAR_GND` (only the bar's nets in F.Cu tracks and
  pours, tented vias of any net).
- **Before routing sign-off**: set `unconnected_items` back to `error` (PR #21).

## After D09 (2026-11-02/03)

- **DEC-026**: the 1V5_CORE ripple check found U303 (LMQ66430 on the battery) folding back into
  the AM band; U303 became a TPS628502-Q1 on 3V3_MAIN (node60-hw #48) and its cell was
  recomposed to TI's Figure 9-61 and approved in D10. The ripple check is closed.
- **C207, C217, L201** (node60-hw #49): added from the netlist with `scripts/add_missing_footprints.py`
  and placed with `pose_search.py`: L201 on B.Cu by U302's input, C207/C217 (8.01 mm) on F.Cu
  beside J912 under the 9.0 mm low lid, at least 8.5 mm from every lid boss. Every part on the
  schematic is now on the board (280).
- **Final gate** (`gate.md`, `judge_final`): 12 pass, 1 warning (parity: the 19 `ki_fp_filters`
  fields), 3 fail (busbar tie pads, accepted in D09; the two fast-route rows: 3 nets, 10 items at
  U501/U401, all PASSABLE). D11 puts full routing to the user.
- The hero renders were re-run after the placement: no visible change (the moved parts are on the
  bottom).
