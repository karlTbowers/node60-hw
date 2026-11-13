# Routing run, 2026-11-12

Asked by the user: finish routing everything on Node60's board, then put the test points back, then
commit and push to main. Decisions taken on the way are in `decisions/log.md`.

## Where it ended

- **On main:** the board prepared for routing (decisions D34-1 to D34-6). KiCad DRC 0 errors, schematic
  parity 0, 205 unconnected items (211 before), every block on its table, `prove_rules.py` 32 of 32. The supply
  paths measure as before but VBAT_PROT, 1.4 % up from the In2 window being back. The test points are still parked.
- **On branch `layout/route-attempt-6layer`:** the full routed attempt. KiCad DRC 0 errors, 30 unconnected
  items, all 62 test points back on the board (55 joined). **Not landed on main**: it cuts the outer-layer
  power pours (below), and 30 joins are still open.
- **Open decision D33** (the user's; page https://claude.ai/artifact/1mJPM6ByyyzovSkJMTTtqk): signal tracks on F.Cu under the GND busbar. Without it the board's own
  rules leave no way to the middle output cell or round U201 that does not cut a power pour.

## The finding behind it

The board lost its inner-layer keep-outs on 2026-11-05 (commit `111fb0e`): the In2 signal window north of
y 70 and the power-only areas of decision D17 A. `scripts/draw_rule_areas.py` redraws them only when given
`--window` and `--power-only`, and was run without. Every router run since, including the fast routes that
judged D29, D31 and D32 and this run's first full route, laid signals on In2 through the power band, and
KiCad had no rule area to object with. The In2 VBAT_PROT pour also spread over the whole layer.

With the keep-outs back (D34-1), signals in the band have:

- B.Cu only under the GND busbar (y 61 to 80) and under the VBAT_IN busbar (y 90 to 109): the top layer there
  is closed to other nets by `node60.kicad_dru`;
- F.Cu in the strip between the bars (y 80 to 90) and south of y 109;
- no inner layer south of y 70.

Every line from the MCU to the middle output cell (nine of them) and every small signal of U201 and U202
has to cross y 72.5 to 86 on B.Cu, and B.Cu there is VBAT_IN (west and east), VBAT_D and VBAT_Q2D pour
from x 93.5 to 216.5. So each such line cuts a power pour, or does not get through.

## What the route cost the power paths

`copper_r.py`, 85 C, all six layers unless noted.

| Path | Before | Routed attempt | Change |
|---|---|---|---|
| VBAT_IN, J901 to Q202 | 0.614 mOhm | 0.788 mOhm | +28 % |
| VBAT_Q2D, R201 to Q203 and Q204 | 0.135 mOhm | 0.246 mOhm | +82 % |
| VBAT_D, Q201 and Q202 to R201 (outer layers only) | 0.522 mOhm | 0.655 mOhm | +25 % |
| VBAT_IN, J910 to Q201 (outer layers only) | 1.310 mOhm | 1.319 mOhm | +1 % |
| OUT1 / OUT2 (outer layers) | 1.551 / 1.504 mOhm | 1.597 / 1.553 mOhm | +3 % |
| OUT3 / OUT4 (outer layers) | 1.553 / 1.487 mOhm | 1.688 / 1.933 mOhm | +9 % / +30 % |
| OUT5 / OUT6 (outer layers) | 1.533 / 1.509 mOhm | 1.604 / 1.812 mOhm | +5 % / +20 % |
| VBAT_PROT to U601 / U701 / U801, 20 A each | 14.27 / 10.56 / 14.44 mV | 14.91 / 10.67 / 14.86 mV | +4 % / +1 % / +3 % |
| VBAT_PROT loss at 3 x 20 A | 0.785 W | 0.809 W | +3 % |

Pour copper on B.Cu: VBAT_IN east 1,144 to 722 mm2 in two pieces; VBAT_Q2D 440 to 334 mm2 in three pieces;
VBAT_D 309 to 292 mm2 in two pieces. On F.Cu: VBAT_IN west band 219 to 152 mm2, VBAT_Q2D 104 to 67 mm2.
The inner-layer pours are whole. Pictures: `img/band_east_B_1_before.png`, `img/band_east_B_2_attempt.png`.

On the prepared board (main) every path but VBAT_PROT measures as before, to the last digit. VBAT_PROT is
14.70 / 10.48 / 14.63 mV and 0.796 W (+1.4 %): the In2 pour is back to the part south of y 70 that D17 A
gave it (20,360 to 11,782 mm2); the rest had spread over the signal window while the rule areas were gone.

## What ran

1. `prep.sh`: main's board, the termination drive lines ripped, `hand/h0.json` applied (part nudges, supply
   joins, the feedback net), the D17 A rule areas drawn, five nets pre-routed (`hand/h1.jobs.json`).
2. The bulk route: `placement/2026-11-02-bars/judge_route.sh` with `KEEP_DECAPS=1`, `S0_HOOK=route_hook.py`
   (keep-outs along the T1S line, which KRT's reading of the rules does not keep) and the plane nets left
   out (`ROUTE_NETS`), KiCadRoutingTools v0.24.0. `transplant_new.py` puts its copper on the real board.
3. Repair rounds (`round.sh`): `gen_jobs.py` turns KiCad's unconnected items into jobs, `mini_route.py`
   routes them to the board's own rules, KiCad's DRC grades each round.
4. Supply joins: a via into its plane for each supply pad left hanging (`gen_jobs.py --supply`), and for each
   piece of GND pour the signal tracks cut off (`gen_island_jobs.py`).
5. Test points: `place_test_points.py` puts each on its own net's copper nearest its old pose, or on the
   nearest free spot with a stub; `apply_test_points.py`.

| Stage | DRC errors | Signal joins open | Supply joins open | At test points |
|---|---|---|---|---|
| main before | 0 | 129 | 14 | 68 (parked) |
| prepared board (on main now) | 0 | 124 | 13 | 68 (parked) |
| bulk route, transplanted | 5 | 21 | 19 | 63 |
| after the repair rounds | 0 | 10 | 27 | 63 |
| after the supply joins | 0 | 10 | 11 | 63 |
| test points back (the attempt) | 0 | 10 | 13 | 7 |

Earlier in the run a first full route (before the keep-outs were found missing) came to 3 open signal joins.
It is discarded: it used In2 through the band.

## Still open on the attempt (30)

- **U201 (7 joins):** LM_OV, LM_CSP (2), LM_TMR, RS_SENSE_P, HGATE_G, DGATE. One layer only there. The divider
  resistors R204 to R207 stand in the opposite order to pins 3 to 5, so the three nets must cross, and only
  one track fits between their pads and Q201's tab. Picture: `img/u201_attempt.png`.
- **Middle cell (3 joins):** SW2_SNS, SW_LHI at the MCU, SPI4_SWITCH1_CS_L at the MCU: stubs walled in by
  their neighbours' routes. Picture: `img/mid_cell_attempt.png`.
- **Supply pads (13):** U202 pin 8 (VBAT_PROT), U201 pin 2 (VBAT_IN sense), U301 pins 1 and 2's pour, U501 pin
  18, C506, C701, C801, Q501, and four pieces of GND pour. Most were open on main before the run.
- **Test points (7):** TP207, TP301, TP403, TP414, TP701, TP703 (2): placed, not joined.

## Checks on main's board

KiCad DRC with `node60.kicad_pro` and `node60.kicad_dru`: 0 errors, 205 unconnected. Schematic parity: 0. `block_poses.py check --parked`: 0 parts off their table (t1s table re-posed for R501 and C509). `prove_rules.py`: 32 of 32. `t1s_stubs.py`: trunk 38.9 mm, PHY stub 24.6/25.6, relay leg 23.9/24.9, as before. `copper_r.py`: every supply path as before but VBAT_PROT (0.785 to 0.796 W at 3 x 20 A, the In2 window).

## Limits of the tools, as found

- `scripts/draw_power.py` must not be run on a routed board: its via fields are chosen against the copper
  that is there, so a redraw moves field vias (55 differed in a trial). `power_shapes.json` is kept in step
  by `land_spec.py`, and a redraw is only for an unrouted board.
- KiCadRoutingTools: its fan-out uses the 0.45 mm via under U401 where the board's preset is 0.35 mm; it
  moves U401's caps on its copy unless told not to (`KEEP_DECAPS`); it does not keep the T1S 0.75 mm rule
  without keep-outs; it leaves the same handful of short nets open in every run; its pour guard will not
  cross a supply pour even where nothing else is possible.
- `mini_route.py` is a single-net router: it has no way to share a narrow corridor between several nets in
  the right order, which is what the middle cell needs. Its rip-up mode moved the problem rather than
  solving it and was not used for the result.

## Files

`prep.sh`, `route_hook.py`, `repair.sh`, `round.sh`, `apply_jobs.sh`, `measure_r.sh`; `mini_route.py`,
`gen_jobs.py`, `gen_island_jobs.py`, `place_test_points.py`, `apply_test_points.py`, `transplant_new.py`,
`rip_nets.py`, `rip_box.py`, `land_spec.py`, `sync_tables.py`, `export_courtyards.py`, `drc_pairs.py`,
`count_open.py`; `hand/` (every hand spec and job list); `img/`; `decisions/`. `work/` (boards, logs) is
not committed.

## The hand specs, in the order they were applied

`hand/h0.json` and `hand/h1.json` (before the bulk route; both are on main's board). Then, on the routed
attempt only: `q3`, `q4`, `q5` (repair rounds), `m2` (the middle cell's corner cleared with `rip_box.py`
and routed again), `u1` (U201's joins), `v2`, `v3`, `v4` (supply joins), `test_points.json`, `t3`, `t4`, `t5`
(test point stubs and the pour pieces they cut off). Each `NAME.jobs.json` is the job list, `NAME.json` what
`mini_route.py` made of it.
