# Routing run, 2026-11-12

Asked by the user: finish routing everything on Node60's board, then put the test points back, then
commit and push to main. Decisions taken on the way are in `decisions/log.md`.

## Where it ended (second run, after decision D33 B)

The user answered D33 on 2026-11-12: **B**, signal tracks on F.Cu under the GND busbar. With that rule
(`node60.kicad_dru`, proven by `prove_rules.py`, 39 of 39) the board is routed and on main:

- KiCad DRC with the board's own `.kicad_pro` and `.kicad_dru`: **0 errors**. Schematic parity: 0.
- **Every signal join is closed** (124 were open on the prepared board).
- **Two supply joins are open**, both open on main before the run too:
  - **U201 pin 2 (VBAT_IN, the LM74910's anode sense).** It is a battery net, so it may not use F.Cu under the
    GND bar, and on B.Cu the pocket west of U201 is closed by the divider lines LM_SW, LM_UVLO and LM_OV. It
    needs those three lines re-laid on F.Cu (they are resistor-limited, so the rule allows it) and an In2 hop
    over the west channel's lanes.
    Decision page D36: https://claude.ai/artifact/DWV3TCNBaJfFMNQ4Pdn2cW
  - **C510 pad 1 (VDDAU_AON, the PHY's second always-on decoupling cap).** Walled in by R301, R505 and the
    regulator's output; C509 on the same pin pair is connected.
- **All 62 test points are back on the board; 60 are joined.** TP301 (VDDAU_AON) and TP401 (UART0_DEBUG_TX)
  are placed but not joined.
- T1S line as before (`t1s_stubs.py`: trunk 38.9 mm, PHY stub 24.6/25.6, relay leg 23.9/24.9; trunk corridor
  clean). Every block on its table (test points re-posed).

## What the route cost the power paths

`copper_r.py`, 85 C (`measure_paths.sh`). "Before" is main's prepared board with nothing routed in the band.

| Path | Before | First attempt (pours cut) | Now |
|---|---|---|---|
| VBAT_IN, J901 to Q202 (all layers) | 0.614 mOhm | 0.788 mOhm | 0.620 mOhm (+1 %) |
| VBAT_IN, J910 to Q201 (all layers) | 0.611 mOhm | | 0.606 mOhm |
| VBAT_Q2D, R201 to Q203 and Q204 (all layers) | 0.135 mOhm | 0.246 mOhm | 0.145 mOhm (+7 %) |
| VBAT_D, Q201 and Q202 to R201 (all layers) | 0.268 mOhm | | 0.298 mOhm (+11 %) |
| VBAT_D, the same (outer layers only) | 0.522 mOhm | 0.655 mOhm | 0.717 mOhm (+37 %) |
| VBAT_IN, J910 to Q201 (outer layers only) | 1.310 mOhm | 1.319 mOhm | 1.303 mOhm |
| OUT1 / OUT2 (outer layers) | 1.551 / 1.504 mOhm | 1.597 / 1.553 | 1.552 / 1.510 mOhm |
| OUT3 / OUT4 (outer layers) | 1.553 / 1.487 mOhm | 1.688 / 1.933 | 1.579 / 1.519 mOhm (+2 %) |
| OUT5 / OUT6 (outer layers) | 1.533 / 1.509 mOhm | 1.604 / 1.812 | 1.535 / 1.489 mOhm |
| VBAT_PROT to U601 / U701 / U801, 20 A each | 14.70 / 10.48 / 14.63 mV | 14.91 / 10.67 / 14.86 | 14.79 / 10.54 / 14.71 mV |
| VBAT_PROT loss at 3 x 20 A | 0.796 W | 0.809 W | 0.801 W (+0.6 %) |

**VBAT_D is the one path that pays**: +11 % on all six layers (0.030 mOhm, 0.11 W at 60 A). The shunt's sense
pads sit between its F1 pad and Q202, so the two sense lines to U202 and U201 cut the B.Cu pour beside the pad
whichever way they run (the outer-layer figure shows it: the east half of the B.Cu pour now reaches F1 only
through the inner planes and F.Cu). Four plane vias beside the sense pad went for RS_SENSE_N. No signal runs
through a battery pour anywhere else: `pour_crossings.py` lists what stands inside each pour's outline.

## How the band is crossed

Between the GND busbar (south edge y 80.1) and the middle output cell (y 99.5) both outer layers are battery
pour, and F.Cu is closed again under the VBAT_IN bar (y 90.1 to 109.1). The first bulk route after D33 still
cut the pours (VBAT_Q2D 0.217 mOhm, the west VBAT_IN pour in two pieces). The ways through that touch no
current path are **two channels under the FET bodies**: 2.8 mm of B.Cu between each FET's source pads and its
drain tab, x 136.85 to 139.65 (Q201/Q203) and x 170.35 to 173.15 (Q202/Q204). The pour copper in them is a
dead-end strip beside the tab.

- West channel, six lanes at 0.3 mm pitch (x 137.6 to 139.1): MOSI, MISO, CS, SW2_FLT_L, SW_VDD, SCK.
- East channel, four lanes (x 170.9 to 171.8): NTC_SW2, SW_LHI, SW2_SNS, SW_VDD.
- The middle cell under the VBAT_IN bar is B.Cu only, so its lines arrive in pin order and nothing crosses:
  the lanes fan out along y 100.0 to 101.5 and drop onto the pins. SW_VDD comes down both channels (R704 on the
  west side, pin 3 and C703 on the east) because nothing can cross the cell. Three short F.Cu hops south of the
  bar's edge (y 109.1): SW2_FLT_L from R704 to pin 12, SW_SNS from pin 2 to R705, SW_VDD from its lane to C703.
- HGATE_G no longer runs under the shunt: Q203's gate is fed on F.Cu in the 1.2 mm gap between the top-layer
  pours, Q204's from the east. NTC_RSENSE runs on F.Cu in the gap between the top-layer VBAT_D and VBAT_Q2D pours.
- North of the band the lines use F.Cu under the GND bar, In2 north of y 70 and B.Cu.

Pictures: `img/d33_band_B.png`, `img/d33_band_F.png`, `img/d33_channel_W.png`, `img/d33_mid_cell.png`.

## Found on the way

- **Seven signal vias had cut the In3 VBAT_PROT finger to U301** (1.2 mm wide, x 163.2 to 164.4, y 47 to 71): the
  always-on regulator's only feed. The power-only keep-outs of D17 A let vias pass, and nothing told the
  routers the finger is narrow. Five vias moved, the finger is 2.4 mm wide beside Q501 and Q502 now, and
  `mini_route.py` (`NOVIA`) and `route_hook.py` keep vias off it. Q501, Q502 and R521 stand on the finger; their
  three in-pad vias are the reason for the widening.
- U301's VBAT_PROT pins were walled off from C301 by the regulator's own output (a pre-route of the first run).
- The VBAT_PROT sense node at U201 pins 15/16, U202 pin 8, C203 and C204 had no connection to VBAT_PROT at all
  (under it In2 and In3 are VBAT_D). It now has one via into the VBAT_PROT strip of In2 and In3 at (161.41, 71.7).
- KiCad reports one violation per track: on a routed board a rule proof planted on copper reports the short, not
  the rule. `prove_rules.py` now finds a copper-free spot for each planted item.
- `mini_route.py`'s rip-up mode again made things worse each time it was tried (three times); every result
  here is from plain routing in a planned order or from hand specs.

## What ran (second run)

1. The GND-busbar rule edit (D33 B) and its seven proofs; `judge_route.sh` closes only the VBAT_IN bar's area.
2. Bulk route of main's prepared board (KiCadRoutingTools v0.24.0, as the first run), copper transplanted:
   5 DRC errors, 13 signal joins open. One repair round (`hand/c1`): 2 errors, 6 open, pours cut.
3. Lines that cut pours ripped south of y 61 (`hand/c2.rips.json`, `c4.rips.json`); the two channels' lanes and
   the middle cell laid by hand (`hand/c4a.json`); lane tops staggered 0.5 mm; joins to the MCU side routed in a
   planned order, the east-most lane first (`hand/c4.jobs.json`, `c6.jobs.json`), pours priced out (`pour_cost`).
4. Hand specs for the sense lines (`c5h`), the SW2_SNS ball (`c6h`, `c6v`, `c7h`), the supply joins (`s3h`,
   `s3k`), the finger (`s5h`, `s5i`, `s5.jobs`), Q501 and R513 (`s7h`, `s7i`, `set_zone_poly.py`).
5. Supply pads and GND pour pieces to their planes (`s1`, `s2`, `s6`).
6. Test points: `TP_MAX_ON=200 place_test_points.py` puts each on its own net's B.Cu copper wherever a free spot
   is (median move 1.5 mm, six moved 30 to 99 mm along their lines); 12 needed a stub (`t2` to `t4`). The
   first try, with a 15 mm limit, gave 27 stubs up to 31 mm, one on the RMII reference clock, and was dropped.
7. `drop_dangling.py`, `dedupe_vias.py`, `land_spec.py`, `lock_supply.py`, `sync_tables.py`.

| Stage | DRC errors | Signal joins open | Supply joins open | At test points |
|---|---|---|---|---|
| prepared board (main before) | 0 | 124 | 13 | 68 (parked) |
| bulk route, transplanted | 5 | 13 | 23 | 62 |
| lanes and cell by hand, joins routed | 0 | 0 | 24 | 62 |
| supply joins | 0 | 0 | 2 | 62 |
| test points back (on main now) | 0 | 0 | 2 | 2 |

New tools in this folder: `rip_nets_box.py`, `prune_islands.py`, `missing_in_routed.py`, `pour_crossings.py`,
`measure_paths.sh` (with `r_jobs.json`), `drop_dangling.py`, `dedupe_vias.py`, `set_zone_poly.py`. The hero
renderings on the docs front page were not re-rendered.

## First run, before D33: the finding behind it

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

## First run: what the routed attempt cost the power paths

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

## First run: what ran

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

## First run: still open on the attempt (30)

- **U201 (7 joins):** LM_OV, LM_CSP (2), LM_TMR, RS_SENSE_P, HGATE_G, DGATE. One layer only there. The divider
  resistors R204 to R207 stand in the opposite order to pins 3 to 5, so the three nets must cross, and only
  one track fits between their pads and Q201's tab. Picture: `img/u201_attempt.png`.
- **Middle cell (3 joins):** SW2_SNS, SW_LHI at the MCU, SPI4_SWITCH1_CS_L at the MCU: stubs walled in by
  their neighbours' routes. Picture: `img/mid_cell_attempt.png`.
- **Supply pads (13):** U202 pin 8 (VBAT_PROT), U201 pin 2 (VBAT_IN sense), U301 pins 1 and 2's pour, U501 pin
  18, C506, C701, C801, Q501, and four pieces of GND pour. Most were open on main before the run.
- **Test points (7):** TP207, TP301, TP403, TP414, TP701, TP703 (2): placed, not joined.

## First run: checks on main's prepared board

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

## Files of the first run

`prep.sh`, `route_hook.py`, `repair.sh`, `round.sh`, `apply_jobs.sh`, `measure_r.sh`; `mini_route.py`,
`gen_jobs.py`, `gen_island_jobs.py`, `place_test_points.py`, `apply_test_points.py`, `transplant_new.py`,
`rip_nets.py`, `rip_box.py`, `land_spec.py`, `sync_tables.py`, `export_courtyards.py`, `drc_pairs.py`,
`count_open.py`; `hand/` (every hand spec and job list); `img/`; `decisions/`. `work/` (boards, logs) is
not committed.

## First run: the hand specs

`hand/h0.json` and `hand/h1.json` (before the bulk route; both are on main's board). Then, on the routed
attempt only (branch `layout/route-attempt-6layer`; the files are in `hand/first_run/` now): `q3`, `q4`, `q5` (repair rounds), `m2` (the middle cell's corner cleared with `rip_box.py`
and routed again), `u1` (U201's joins), `v2`, `v3`, `v4` (supply joins), `test_points.json`, `t3`, `t4`, `t5`
(test point stubs and the pour pieces they cut off). Each `NAME.jobs.json` is the job list, `NAME.json` what
`mini_route.py` made of it.
