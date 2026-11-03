# Node60 placement plan, v1 (2026-11-02)

Status: v2 (2026-11-02). v1 approved with D01 option B (tented vias allowed under the bars). v2 changes: the busbar net tie (D02) and the fiducials (D03) can't be done as v1 wrote them and wait on their decisions; the U401 scoped rule is dropped (at 0.1 mm track, the board minimum, and 0.15 mm clearance, the Default class, the BGA escapes, so no rule is needed).

Run: `placement/2026-11-02-bars/`. Starting board: `main` at 63ff75e (PR #38's placement, busbar
3D models from PR #37). Measurements below were taken on that board with this skill's scripts
(`escape_U401_*.json`, `capacity.json`, `heights_*.json`, `baseline_rules.json`).

## Stackup and layers

6 layers, 2.0 mm, JLCPCB 1/2 oz assumed by every quote (CLAUDE.md, PCB stackup & fab quotes page);
stackup and fab house still **open**.

| Layer | Job | Source |
|---|---|---|
| F.Cu | signal; decoupling caps, J401, D201; under each busbar only the bar's net | DEC-024, `node60.kicad_dru` |
| In1.Cu | GND plane | autoplan's plane map, accepted here |
| In2.Cu | signal | escape budget |
| In3.Cu | signal | escape budget |
| In4.Cu | VBAT_PROT plane | autoplan's plane map, accepted here |
| B.Cu | signal; nearly every part | DEC-024 |

U401's escape needs 4 signal layers (deepest signal ring 8, 2 rings per layer) and has 4; a 0.45 mm
via fits between four balls, so the board's own via (0.45/0.25) escapes it: no finer via is needed
(`escape_budget.py`). Layer capacity: busiest 10 mm window 7 % full (`layer_capacity.py`).

## Fixed parts

| Ref | What | Pose | Source |
|---|---|---|---|
| J901, J910 | VBAT_IN REDCUBE terminals, B.Cu | (208.0, 99.6), (102.0, 99.6) | `place_connectors.py` v15 |
| J902, J911 | GND REDCUBE terminals, B.Cu | (233.5, 70.6), (76.5, 70.6) | same |
| J903, J912 | T1S headers, north edge, 39 mm apart | (176.6, 46.0), (137.6, 46.0) | same |
| J904–J909 | output headers, front edge, 37.3 mm pitch | y 125.0 | same |
| BB901, BB902 | busbar footprints (courtyard = bar outline) and rule areas `BUSBAR_<net>` | over each terminal pair | same, PR #33/#37 |
| J401 | debug header, always on F.Cu | annealer places | user, 2026-11-01 |

Placed by `scripts/place_connectors.py` and locked.

## Enclosure keep-outs and height limits

| Area | Side | What may stand there | Height limit | Source |
|---|---|---|---|---|
| Under each busbar | F | nothing (BB901/BB902 courtyards) | 0.6 mm (bar on the spigots) | DEC-023 |
| Under each busbar | B | any part; its vias under a bar tented | — | `node60.kicad_dru`, D01 (B) |
| Under each busbar | copper | F.Cu: only the bar's own net in tracks and pours; tented vias of any net | — | `node60.kicad_dru`, D01 (B) |
| Lid bosses, Ø8 mm at each SurLok M4 hole (16) | F | parts under 5.0 mm | 5.03 mm | `enclosure_geometry.py` v15 |
| Low lid | F | everything | 9.0 mm | CLAUDE.md |
| Floor | B | everything | 6.17 mm (K501 5.2 mm at 0.97 mm, accepted) | CLAUDE.md, user 2026-11-01 |

## Heat and quiet zones

| Zone | Parts | Why | Keep away from |
|---|---|---|---|
| Power entry | Q201–Q204, R201 | 60 A node load through the FET bank and the 0.25 mΩ shunt | the INA228's Kelvin lines' routing, the crystal |
| Output switches | U601, U701, U801 | 2 × 10 A each; exposed pad 17 (VBAT_PROT) needs a via field to In4 | their pad's via field kept clear of the busbar rule areas |
| Switchers (noisy) | U302 + L301 (3V3_MAIN), U303 + L302 (1V5_CORE) | switch nodes | T1S line nets 10 mm (11.8 now), crystals and the 50 MHz clock 3 mm |
| Quiet | T1S line, Y401, Y501, INA228 sense | — | switch nodes |

## Critical nets

| Id | Nets | Parts | Layers | Lane | Budget | Rule |
|---|---|---|---|---|---|---|
| T1S | `/T1S_P`, `/T1S_N`, `/T1S/T1S_*` | J912, J903, K501, FL501, C511, C512, D501, D502, U501 | B.Cu, In2/In3 | J912 to J903 trunk; trunk midpoint to FL501 to U501 | trunk ≤ 45 mm, stub ≤ 25 mm | class T1S_100R, AN1718 §2: no pour round the line interface, no copper under FL501 |
| RMII | `/RMII0_T1S_*` | U501, U401 | B.Cu, In2/In3 | U501 to U401 | ≤ 40 mm | Default |
| REFCLK | `T1S_OSC_OUT`, `T1S_REFCLK`, `RMII0_T1S_REF_CLK` | Y501, R503, R504, U501, U401 | B.Cu | Y501 beside U501 | R503 ≤ 6 mm from U501.27 | intent rows |
| FXOSC | `FXOSC_EXTAL`, `FXOSC_XTAL` | Y401, C424, C425, R408, U401 | B.Cu | at U401's K1/L1 balls | ≤ 3.5 mm | intent rows |
| Kelvin | VBAT_D, VBAT_Q2D sense taps | R201, U202 (INA228) | B.Cu | R201's Kelvin pads to U202 | **≤ 10 mm (71 mm now)** | assumed: TI INA228 layout guidance, short and coupled |

## Blocks and ports (stage 3, one decision page each)

| Block | Anchor | Reviewed by hand? |
|---|---|---|
| T1S line interface | K501 | yes (held under the trunk's midpoint) |
| Buck 3V3_MAIN, buck 1V5_CORE | U302, U303 | yes (KRT templates, `hot_loop.py`) |
| Power entry: FET bank, shunt, INA228, LM74910 | U201 | yes |
| MCU crystal | Y401 | yes |
| Output channel | U701 (U601, U801 copies; D08) | yes, once |
| Everything else | — | annealer |

## Net classes and high-current pads

| Nets | Class | Track | Clearance | Source |
|---|---|---|---|---|
| everything else | Default | 0.2 | 0.15 | `node60.kicad_pro` |
| T1S line | T1S_100R | 0.165 | 0.15 | DEC-012 |
| U401 ball field | none needed: 0.1 mm track (board minimum, as KiCad's DRC measures tracks) at 0.15 mm clearance fits one track per channel | | | `escape_budget.py --space 0.15`, v2 |
| VBAT_PROT, VBAT_D, VBAT_Q2D, outputs | power widths per path, from IPC-2152 at the routing stage | | | handbook ch. 05 |

High-current pads (1 A per 0.45/0.25 via, **assumed**): Q201.9–Q204.9 30 A, R201.1/.2 60 A,
U601/U701/U801.17 20 A. Via sites measured on the current board: see D01.

## Assembly

Both sides reflowed. Top (decaps, J401, D201) first, bottom second, so the heavy parts (REDCUBEs, FETs,
TPS2HCS08s, K501) see one reflow and never hang; D201 (DO-218AC) and J401 then hang during the bottom
reflow: assembler to confirm or glue. Fiducials: 3 per side, asymmetric, near three corners, clear of
the busbars and bosses. Proposed; none on the board today.

## Busbar net tie

J901 reaches J910 (and J902 reaches J911) only through the bar, so KiCad reports J901 unconnected
whatever the placement. Proposed: BB901/BB902 carry a pad on each spigot, tied as a net tie, so the
bar joins its terminals on the board. Needed before the PR #21 override comes off.

## Switchers

`switchers.json`: U302 and U303, LMQ66430-Q1, from TI's datasheet layout section (stage 2).

## Assumed

- 1 A per via: to be checked against the stackup's plating and the 10 A thermal test.
- The Kelvin lane budget (10 mm): to be confirmed against the INA228 datasheet's layout section in stage 3.
- In1 GND / In4 VBAT_PROT as the plane layers: the stackup is open.
