# SPI series resistors, 2026-11-13

Asked by the user: "kick off another session to add the series resistors on the SPI bus", the note the
kicad-happy review left under CK-002 (no series resistor on any SPI clock). Decisions taken on the way, each
with its source and its undo: `decisions/log.md` (S01 to S05). **S03 was the user's and is answered (2026-11-13): A, the SDO
resistor stays 33 Ω**, not TI's 768 Ω. Page: https://claude.ai/artifact/Lg5kELfNjbfz8ujCLtS6cZ
(private; source `decisions/S03-sdo-resistor.json`).

## Where it ended

Thirteen 33 Ω 0402 resistors (Yageo AC0402JR-0733RL, the part of R503/R504) on the schematic and on the routed
board. No other part moved. `node60.kicad_dru` and `node60.kicad_pro` are unchanged.

- KiCad DRC with the board's own project and rules, zones refilled: **0 errors, 0 unconnected items**, 19
  warnings (the same 19 as on main: 16 `silk_edge_clearance`, 3 `silk_over_copper`, all footprint graphics).
  Schematic parity: the 19 known `ki_fp_filters` lines. ERC: the two known warnings on U501.
- `prove_rules.py` 39 of 39. `t1s_stubs.py`: every length as before. `trunk_check.py --all`: 0 crossings, 0
  vias in the corridor, 0 top-side pads. `block_poses.py check`: all 12 blocks on their tables. RMII windows as
  before (TX setup 0.601 ns).
- Supply paths (`measure_paths.sh`, 85 °C): every line as on main (VBAT_PROT 0.807 W at 3 × 20 A). Battery
  pours on the outer layers: same areas and pieces (`pour_crossings.py`). Inner planes: In1 and In4 GND one
  piece each, In3 3V3 two, as before. **One difference:** the F.Cu ground pour south of U401, which the top-side
  tracks there already cut into small pieces, is in 21 pieces instead of 20; the new 6.3 mm² piece
  (x 200.5 to 206.5, y 59.7 to 61.1) has its own GND via at (202.94, 60.12).
- CI's other checks: `check_schematic.py` OK, `mcu_pinmap.py --check` up to date.

## The buses and what they got

Four SPI buses, each point to point from U401 (DEC-018, and the flash alone on LPSPI2).

| Bus | Device | SCK | MOSI | CS_L | MISO |
|---|---|---|---|---|---|
| LPSPI4 `SPI4_SWITCH1_*` | U601 | R409 at U401 | R410 at U401 | R411 at U401 | R608 at U601 pin 14 |
| LPSPI5 `SPI5_SWITCH2_*` | U701 | R412 at U401 | R413 at U401 | R414 at U401 | R708 at U701 pin 14 |
| LPSPI3 `SPI3_SWITCH3_*` | U801 | R415 at U401 | R416 at U401 | R417 at U401 | R808 at U801 pin 14 |
| LPSPI2 `SPI2_FLASH_*` | U402 | R418 at U401 | none | none | none |

Why these, in short (S01, S02): the handbook has no rule; TI's TPS2HCS08-Q1 data sheet draws a resistor `RSPI`
in all four lines (Figure 9-1; Table 9-1: 22 Ω typical, optional, "For EMI or other transient limits on the SPI
pins") and gives its SPI timing with 220 Ω; NXP and ISSI ask for nothing on these lines. 33 Ω is inside TI's
range and is the board's existing series part.

Measured on the board (`measure.py`; "stub" is the copper from the driver's pad to the resistor):

| Ref | Stub net (driver) | Line | At (mm) | Stub copper | Stub vias | Line copper | Line vias |
|---|---|---|---|---:|---:|---:|---:|
| R409 | `SPI4_SWITCH1_SCK_MCU` (U401.D15) | `SPI4_SWITCH1_SCK` | 209.80, 48.40, 90° | 11.8 mm (B.Cu 5.0 In2.Cu 6.8) | 2 | 212.0 mm | 2 |
| R410 | `SPI4_SWITCH1_MOSI_MCU` (U401.C15) | `SPI4_SWITCH1_MOSI` | 195.41, 66.69, 180° | 18.8 mm (B.Cu 2.4 In2.Cu 16.4) | 2 | 176.6 mm | 6 |
| R411 | `SPI4_SWITCH1_CS_L_MCU` (U401.A14) | `SPI4_SWITCH1_CS_L` | 202.08, 67.44, 180° | 10.8 mm (B.Cu 0.9 In2.Cu 9.9) | 2 | 167.3 mm | 4 |
| R412 | `SPI5_SWITCH2_SCK_MCU` (U401.A16) | `SPI5_SWITCH2_SCK` | 193.35, 61.72, 180° | 15.8 mm (B.Cu 3.9 F.Cu 11.9) | 4 | 106.2 mm | 2 |
| R413 | `SPI5_SWITCH2_MOSI_MCU` (U401.A15) | `SPI5_SWITCH2_MOSI` | 193.42, 60.78, 180° | 14.8 mm (B.Cu 0.2 In2.Cu 14.6) | 2 | 113.9 mm | 7 |
| R414 | `SPI5_SWITCH2_CS_L_MCU` (U401.G16) | `SPI5_SWITCH2_CS_L` | 212.95, 52.34, 270° | 11.2 mm (B.Cu 0.1 F.Cu 7.1 In2.Cu 4.1) | 3 | 145.5 mm | 7 |
| R415 | `SPI3_SWITCH3_SCK_MCU` (U401.E14) | `SPI3_SWITCH3_SCK` | 207.53, 61.03, 270° | 9.9 mm (B.Cu 9.9) | 0 | 59.6 mm | 2 |
| R416 | `SPI3_SWITCH3_MOSI_MCU` (U401.F14) | `SPI3_SWITCH3_MOSI` | 212.40, 54.70, 270° | 10.8 mm (B.Cu 5.4 In2.Cu 5.4) | 2 | 69.6 mm | 5 |
| R417 | `SPI3_SWITCH3_CS_L_MCU` (U401.G15) | `SPI3_SWITCH3_CS_L` | 213.49, 58.09, 270° | 10.2 mm (B.Cu 10.2) | 0 | 60.7 mm | 2 |
| R418 | `SPI2_FLASH_SCK_MCU` (U401.D2) | `SPI2_FLASH_SCK` | 209.97, 58.33, 0° | 20.5 mm (B.Cu 4.1 In2.Cu 16.5) | 2 | 40.5 mm | 3 |
| R608 | `SW_SDO` (U601.14) | `SPI4_SWITCH1_MISO` | 72.75, 110.60, 180° | 1.7 mm (B.Cu 1.7) | 0 | 212.0 mm | 5 |
| R708 | `SW_SDO` (U701.14) | `SPI5_SWITCH2_MISO` | 147.45, 110.62, 180° | 1.5 mm (B.Cu 1.5) | 0 | 137.4 mm | 11 |
| R808 | `SW_SDO` (U801.14) | `SPI3_SWITCH3_MISO` | 221.00, 108.65, 0° | 4.8 mm (B.Cu 4.8) | 0 | 66.7 mm | 3 |

The resistors at U401 stand 10 to 20 mm of copper from their balls, not at them: the balls are inside the BGA
and the bottom side under and beside it is taken, so each sits in the first free spot along its line (S05).
20.5 mm is 0.14 ns one way; NXP's fastest 3.3 V pad edge at the LPSPI timing condition (DSE = 1, SRC = 0) is
0.8 ns. Every line's test point is on the line side of its resistor, as on the schematic.

`img/u401_se_B.png` shows the ten at U401 on the bottom side.

## CK-002 itself does not go away

The analyzers were run again (`reviews/2026-11-13-spi-series-r/`, kicad-happy 3.0.1). `analyze_emc.py` still
prints CK-002 for both nets, now "SPI4_SWITCH1_SCK is 212mm long" and "SPI5_SWITCH2_SCK is 106mm long" (224 and
122 before: the stub is now its own net). CK-002 is a length rule ("Long clock trace", heuristic); it does not
look for a series resistor, and nothing short of moving U401 or the switches shortens those lines. What this
run closes is the review's own remark beside it ("No series resistor on any SCK net ... slow pad slew in
firmware is the only edge control"). EMC score 82, 56 findings, as before.

Other analyzer differences, all from the new parts: VP-001 (via in pad) 185 to 195, the ten pad vias of S05,
filled and capped like every via on the board; TB-001 (0402 tombstoning, info) on R410, R411, R415, R416;
three CC-002 lines renamed to the `_MCU` nets (the 0.1 mm escape tracks under U401, unchanged). DS-002 (no
datasheets directory) appears only because `datasheets/` is git-ignored and absent from this worktree.

## Timing note (found on the way, not changed by this run)

In mode 1 the switch shifts SDO on SCLK's rising edge and the MCU samples on the falling one. TI gives SDO valid
30 ns after the edge at most (§6.6); NXP's LPSPI controller wants 25 ns of setup (S32K3xx data sheet Rev. 14,
Table 47). At 8 MHz that leaves 62.5 − 55 = 7.5 ns for the flight out and back (2.9 ns on U601's bus) and the
SDO resistor's RC (about 1.2 ns at 33 Ω): about 3.5 ns to spare by the data sheets. 8 MHz is DEC-018's maximum,
not a requirement; GATE-OUT-02 is where the working clock gets set. With 768 Ω (S03 option B) the limit is about
5 MHz.

## Left for the user

1. **S03**: answered 2026-11-13, A: 33 Ω stays on SDO. TI's loss-of-ground condition (RSDO ≥ 768 Ω) is not met;
   the footprint is the same if that is wanted later.
2. `mcu-config.yaml` does not set the SPI pads' drive strength. It now notes NXP's timing condition (DSE = 1,
   SRC = 0); choosing the setting is firmware's.
3. 22 Ω (TI's typical RSPI) instead of 33 Ω would need AC0402JR-0722RL in the library (S02); not proposed.
4. The docs hero renderings were not re-rendered (`npm run hero`): 13 small parts were added on the bottom side.

## How to repeat

```
cd placement/2026-11-13-spi-series-r
python3 edit_sch.py            # on main's sheets only: adds R409-R418 and R?08 (refuses a second run)
./build.sh                     # main's board (85a8ca5) + plan.json -> node60.kicad_pcb, fields, silk, DRC
zsh ../2026-11-13-kicad-happy-fixes/checks.sh $PWD/work/base_filled.kicad_pcb   # writes into that run's checks/; copied to checks/ here
```

`plan.json` is the record of every part's pose, the track pieces taken out and the joins added. `plan.py`
proposed it on `export_copper.py`'s and `export_courtyards.py`'s dumps of main's board, in this order, each run
on the copper the one before left (`work/planned.copper.json`): the ten lines with a plain search; R808 again
with its real limit (4.6 mm, its test point is at 6.1); R417 (`DMAX=12`); R418 in its test point's branch; R414
last (`NO_TP=1 DMAX=12.2 REACH=4.5 PER_CUT=4`). A fresh single run may pick other, equally legal spots.

## Tools in this folder

- `edit_sch.py`, `sx.py`: the schematic edit, as text (no KiCad save, so nothing else on the sheets moves).
- `plan.py` (KRT's venv: shapely): cut, place, route with `../2026-11-12-route/mini_route.py` in plain mode.
- `apply_plan.py` (KiCad's Python): footprints from the library with their symbol links and nets, cuts, the
  driver's side re-netted, joins. `silk_new.py`: places only the named reference texts.
- `measure.py`, `view.sh` (a picture of any board window), `build.sh`. `work/` is not committed.
