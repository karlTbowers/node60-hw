# Passive placement study, 2026-11-12

Asked by the user: review where the pull-ups, pull-downs, bypass capacitors and setting
resistors stand, and move any that would save vias or plane cuts; later, remove the thin
3V3_MAIN track to R607/R707 and tidy the power shapes. Every attempt is a copy of main's board
(commit 7530cf0); main was untouched until D32 was answered: **I and H** (user, 2026-11-12), landed the same day (see Landing).

## Attempts

Each: spec `attempts/NN-*.json`, board `boards/NN-*.kicad_pcb` (not committed; rebuild with
`./build.sh NAME SPEC...`), pictures `img/NN-*/*_1_before.png` and `*_2_after.png`. All pass
KiCad DRC with the board's own rules, 0 errors.

| Page | Attempt | What moves | 3V3 track, board / band (mm) | 3V3 vias | Blocks touched |
|---|---|---|---|---|---|
| | main | | 246 / 201 | 69 | |
| A | 01 tmp175-home | C215, R211 to U203; 43 mm feed and 3 vias deleted | band 153 | 67 | none |
| B | 02 east-feed | east cell fed from the In3 margin (5 mm, was 36 mm); 3 vias that joined nothing deleted | band 193 | 66 | none |
| C | 03b i2c-pullups-stair (needs 01) | R406, R407 to U203, the bus's end, on R211's via | band 153 | 65 | none |
| | 03a i2c-pullups-row | first arrangement, superseded by 03b | | | none |
| D | 04 irq-pullup | R508 to U401 ball B3 | unchanged | 69 | none |
| E | 05 ntc-to-mcu | R607/C607, R707/C707, R807/C807 to the plane south of U401 | track stays (feeds R601, R701) | 72 | out_6x, out_34, out_8x |
| F | 06 phy-strap | R513 to U501's pin 23 side | unchanged | 69 | none |
| | 07b combined | 01+02+03b+04+05+06 | 171 / 138 | 65 | as 05 |
| G | 08 no-3v3-into-cells | 01+02+05, and R601, R801 to the In3 margins' vias, R701 to the MCU | 38 / 8 | 68 | out_6x, out_34, out_8x |
| I | 09 everything | 01+02+03b+04+05+06+08 | 42 / 8 (F.Cu 33 to 1.5) | 66 | as 08 |
| H | 10 tvs-pour | VBAT_IN pour on F.Cu extended over D201's tab (it had no copper) | unchanged | 69 | none |

Numbers: `copper_table.py` to `data/copper_table.json`.

## Fast routes

`judge/v024`: 22 runs (main four times as base and base3, each of a01 to a09 twice),
KiCadRoutingTools v0.24.0 (a27fdf2e), graded by KiCad with the board's own rules;
`route_metrics.py judge/v024 --json data/routes.json`. Earlier batches (`judge/base`,
`attempts`, `attempts2`, `attempts3`) were stopped when KRT was upgraded mid-run and are not used.

| Run | Blocking | Unconnected | Clearance | Signal vias | Signal mm |
|---|---|---|---|---|---|
| main | 108 to 113 | 75 | 29 to 33 | 216 | 4181 |
| a01 | 107, 111 | 74 | 29 | 214 | 4285 |
| a02 | 121, 123 | 70 | 47 | 243 | 4466 |
| a03b | 122, 118 | 72 | 46 | 228 | 4081 |
| a04 | 136, 134 | 71 | 61 | 230 | 3992 |
| a05 | 117, 114 | 69 | 44 | 245 | 4327 |
| a06 | 101, 101 | 73 | 24 | 218 | 4263 |
| a07b | 116, 118 | 72 | 40 | 223 | 4006 |
| a08 | 134, 137 | 70 | 60 | 221 | 4262 |
| a09 | 129, 131 | 69 | 56 | 227 | 4487 |

Reading: v0.24.0 lays the same copper on the same board every time (repeats differ only in
KiCad's count, by up to 5), but moving one resistor reshuffles the route (a06 101, a04 136), nearly
all in the router's own clearance errors. The blocking count cannot rank the attempts. Unconnected
items are lower than main on every attempt. No routing gain is claimed; the case for the moves is
the hand copper removed.

## Findings not trialled

- R604/R704/R804 (FLT pull-ups) at the MCU on 3V3_MAIN: a schematic change against the sheet's
  note after TI's Table 9-1; the user's call.
- C420 (V11, 100 nF) 6.9 mm from the nearest ball, in no block table.
- U203 13.7 mm from Q201; the intent asks 5 mm.
- R306/R307 could stand 6 mm closer to U303 pin 2 (no via saved). R512 needs a via wherever it stands.
- A 3V3 strip on In3 to the middle cell was rejected: it cuts VBAT_PROT across the path to all three switches.

## Landing (D32: I and H, 2026-11-12)

`land_d32.sh`, from the repo root: the attempts 01, 02, 03b, 04, 05, 06, 08 and 10 on a copy of main's board
(`build.sh d32-land`), `land_spec.py` brings `placement/2026-11-02-bars/power/power_shapes.json` in step with it
(52 stubs and points out; 8 vias, 13 stubs and the zone `PWR_VBAT_IN_D201_F` in; the moved 3V3 parts excepted
from the automatic pad vias), `lock_supply.py` and `scripts/draw_power.py` redraw the supply copper from the
spec (the redrawn copper equals the reviewed board's, track for track and via for via), and the board is
written back. Block tables: `out_6x`, `out_34`, `out_8x` and `t1s` edited, `mcu_pullups` and `u203_parts` new.

Checks on the landed board: KiCad DRC 0 errors, schematic parity 0, 211 unconnected (main 216),
`block_poses.py check` 0 parts off their table, `prove_rules.py` 32 of 32. Six new silk-overlap warnings
(reference texts of the moved parts) are left for the silk pass.

`scripts/draw_power.py` fix found on the way: a locked stub longer than 2 mm survived a redraw and stacked
(1V5_CORE_REG had the same track seven times); the sweep now looks at both ends.

## Tools

`dump_board.py`, `plane_at.py`, `passives.py` (the survey of all 175 two-pad parts),
`apply_attempt.py`, `build.sh`, `drc_counts.py`, `study_picture.py`, `pictures.sh`,
`copper_table.py`, `route_metrics.py`, `review_page.py`.
