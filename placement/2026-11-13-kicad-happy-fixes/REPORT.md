# kicad-happy fixes, 2026-11-13

Asked by the user: address every finding of the kicad-happy review of the routed board
(`reviews/2026-11-12-kicad-happy/REPORT.md`), U501's pad vias as the manufacturer recommends, the low-priority
notes and the interior stitching included. Decisions taken on the way, each with its undo: `decisions/log.md`
(F01 to F08). The analyzers run again on the result: `reviews/2026-11-13-kicad-happy-after/`.

## Where it ended

Board: main's of 2026-11-12 (`264352a`) with the steps below. No part moved. `node60.kicad_dru` and
`node60.kicad_pro` are unchanged.

- KiCad DRC with the board's own project and rules, zones refilled: **0 errors, 0 unconnected items**, 19
  warnings (380 before: 377 silk, 2 dangling tracks, 1 double via).
  Schematic parity: the 19 known `ki_fp_filters` lines, nothing else.
- `prove_rules.py` 39 of 39. `t1s_stubs.py`: every length as before. `trunk_check.py --all`: 0 crossings, 0
  vias in the corridor, 0 top-side pads. `block_poses.py check`: every block on its table. RMII windows as
  before (TX setup 0.601 ns).
- Supply paths (`measure_paths.sh`, 85 °C): every line of the table as on main. Battery pours on the outer
  layers: same pieces (`pour_crossings.py`). Inner planes: same piece counts (`plane_pieces.py`).

| Finding | Status | What was done | What remains |
|---|---|---|---|
| N1 U501 pad vias | fixed | 9 GND vias in pad 33, 3 × 3 at 1.20 mm, 0.33 mm holes, per Microchip C04-2500 Rev B (F01) | nothing |
| N2 0.075 mm via ring | partly | 213 -> 131 vias of 0.35/0.20: 59 to 0.45/0.25, 22 to 0.40/0.20 (F03) | 83 under U401 (D23), 24 with no room, 24 in the power band left small to keep VBAT_D (option file); the question to JLCPCB |
| N3 double via, stubs | fixed | deleted, with 29 more exact duplicates found board-wide (F02) | nothing |
| N4 silkscreen | partly | 377 -> 19 warnings; every reference clear of pads, silk and parts (F05) | 19 from footprint graphics (edge connectors' outlines, three pin 1 markers): library or part moves |
| N5 L302 at the edge | no change needed | checked against edge rule, ring vias, enclosure (F06) | nothing |
| N6 stitching, return vias | fixed where there is room | 130 return vias, 233 stitching vias (F04) | 41 fast-net vias without a site (20 under U401, 7 in the power band, 14 hemmed in); no stitching in the power band by design |
| Other sections | see below | datasheets fetched, two statements checked, pad spacing measured, lifecycle audit run | structured datasheet extraction, SPICE, thermal, Gerber checks |

## N1: U501's exposed pad

Microchip's data sheet DS60001573K calls the pad "the primary ground connection of the device", to be joined
to the ground plane "through an array of vias as specified in the Packaging Information section" (§6.4,
p. 230). §8.1's recommended land pattern (drawing C04-2500 Rev B, p. 267) draws nine vias, 3 × 3, with Thermal
Via Diameter V 0.33 mm and Thermal Via Pitch EV 1.20 mm, "filled or tented". The board has exactly that:
0.33 mm holes on 0.60 mm pads, filled and capped like every via.

Two things had to give. The array stands 0.10 mm north of the pad's centre, because a centred south row would
stand 0.71 mm from the T1S trunk on F.Cu (the rule asks 0.75). And three locked tracks crossed the pad on other
layers: TXD1 and MDC on F.Cu, TX_EN on In2. They now run in the 0.6 mm gaps between the via rows, 0.4 to
0.6 mm longer each (4 ps on the RMII lines). In3's 3V3 plane under the PHY
loses 5.8 mm² to the nine antipads and stays one piece.

## N2: via sizes

| Via | Before | After |
|---|---:|---:|
| 0.35/0.20 mm (0.075 mm ring) | 213 | 131 |
| 0.40/0.20 mm (0.10 mm ring) | 60 | 90 |
| 0.45/0.25 mm (0.10 mm ring) | 2,287 | 2,701 |
| 0.60/0.33 mm (U501's pad) | 0 | 9 |
| All vias | 2,560 | 2,931 |

The 131: 83 under U401 (D23, unchanged), 24 that DRC refuses at both larger sizes, and 24 in the middle of the
power band that fit but cost VBAT_D 0.3 % (F03). `n2_vias.json` lists all 129 candidates with the size each
fits and why any stayed small.

**To ask JLCPCB** (not asked; the user's to send): whether a 0.35 mm via pad on a 0.20 mm hole (0.075 mm
ring) is accepted on the 2 oz inner layers of JLC062012-1080 with filled and capped vias, for 131 vias; and if
not, the smallest via pad they accept there on 0.20 and 0.25 mm holes, since the other 2,791 small vias have a
0.10 mm ring, which is also under the 0.254 mm their page gives for plated holes on 2 oz.

## N6: return vias and stitching

`stitch.py` proposes, KiCad's DRC judges (0 errors). A first proposal put vias 0.6 mm from T1S copper: a
board copy has no project beside it, so its nets have no classes; the script now takes them from the
project's patterns.

- Return vias (a GND via within 1.0 mm of a signal via): RMII, REF_CLK, oscillator, MDIO and SPI nets 65 of
  106 vias covered (5 before), buses and reset 15 of 28, other signals 65 of 152. 21 of the 130 are 1.0 to
  1.5 mm away, where nothing nearer was legal.
- Stitching: 233 vias on a 5 mm grid north of the power band and in the board's margins. Nothing in the power
  band, where every layer but In1 and In4 is battery copper.
- The analyzer's EMC score went from 76 to 82; its RP-001 lines fell from warning to info for all 21 nets it
  lists (for example RESET_L 11 uncovered transitions to 4, RMII RXD1 6 to 1, SPI5 MISO 11 to 4).

## N4: silkscreen

`silk_place.py` rasterises, per side, what a reference may not touch (mask openings, silk graphics, every
courtyard, the edge) and gives each reference the nearest free spot. All 282 found one; 16 are 3 to 6 mm
from their part (F05). The remaining 19 warnings are footprint graphics.

## The review's other sections

- **Already covered by a decision:** nothing there needed a change. Checked from the data sheet: the
  LM74910H's exposed pad (RTN) is to float (F07), so TV-001 on U201 stays a false positive.
- **Analyzer's new RT-001 on GND** ("3 copper islands hold its 190 pads") is false, like its VBAT_IN line:
  KiCad reports 0 unconnected items, and `net_islands.py`, which joins pours, tracks, pads and vias by their
  shapes, finds one island for GND (190 pads) and one for VBAT_IN (20 pads). The analyzer's line appears with
  the stitching vias.
- **JLCPCB, pad to pad:** no two pads of different nets closer than 0.15 mm (F08).
- **Datasheets:** 59 PDFs fetched through DigiKey's API into `datasheets/` (git-ignored). Analyzer DS-002 (no
  datasheets) is gone. The structured extraction the IC-aware checks and the thermal analyzer need was not
  run (F07); `analyze_thermal.py` still skips for lack of it.
- **Lifecycle audit** (the review had not run it): 72 part numbers at DigiKey, 69 active, 3 unknown (the two
  busbars and LAN8670D0-E/LMXVAO, not resolved under that number); 69 temperature checks against −40 to
  +125 °C, none failing.
- **Not done:** SPICE (no simulator installed: `ngspice`, `ltspice`, `xyce` all missing; installing one is the
  user's call), Gerber analysis (no fabrication outputs yet).

## Left for the user

1. The JLCPCB question above. The 24 power-band vias stay 0.35/0.20 mm (user, 2026-11-13: "Leave them
   small"); `specs/n2_band_option.json` remains as the fallback if JLCPCB refuses the 0.075 mm ring.
2. The 19 silk warnings need footprint or part changes: the AT13/ATM13 footprints' body outline beyond the
   board edge (library), and R605/R705/R805 0.15 mm further from their switch's pin 1 marker (or the marker
   moved in the library footprint).
3. Handbook chapter 05 asks for the board name, revision and "DropOut" on the top side's silkscreen. The board
   has no such text. Not added: the PCB revision's name is the user's to give.
4. CK-002: no series resistor on any SPI clock (DEC-018's buses, 122 and 224 mm long). A schematic change,
   so not made here.
5. The docs hero renderings were not re-rendered (`npm run hero`): the copper changed, the placement did not.
6. Structured datasheet extraction, a SPICE simulator, and the thermal analysis that depends on both.

## How to repeat

```
cd placement/2026-11-13-kicad-happy-fixes
git show 264352a:node60.kicad_pcb > work/base.kicad_pcb && ./drc.sh work/base.kicad_pcb   # main's board, zones filled
./build.sh work/base.kicad_pcb work/final.kicad_pcb     # the steps, from specs/, then DRC
./land.sh work/final.kicad_pcb work/base.kicad_pcb      # onto node60.kicad_pcb, power_shapes.json in step, locked
./checks.sh $PWD/work/base.kicad_pcb                    # every check, with before/after pairs in checks/
```

The specs were proposed in this order, each from the board as the steps before left it: `n1_u501.json` (by
hand), `n2_resize.json` (`n2_enlarge.py`, `n2_retry.py`), `n6_stitch.json` (`stitch.py` on
`export_copper.py`'s dump), `silk_place.json` (`silk_export.py`, `silk_place.py`).

## Tools in this folder

- `drc.sh`: KiCad DRC on any board copy under the board's own project. KiCad finds `.kicad_pro` and
  `.kicad_dru` by the board's file name, so a copy named anything but `node60.kicad_pcb` is judged with
  KiCad's defaults (the first via pass here was, and was thrown away).
- `apply_fix.py` (delete, tracks, vias, resize from a spec), `dedupe_tracks.py`, `near.py`.
- `n2_enlarge.py`, `n2_retry.py`: KiCad reports one violation per track, so a clean run is the only proof;
  the retry confirms every round with one.
- `stitch.py`, `plane_pieces.py`, `net_islands.py`, `sync_spec_sizes.py`.
- `silk_export.py`, `silk_place.py`, `silk_apply.py`.
- `build.sh`, `land.sh`, `checks.sh`. `work/` (boards, dumps, logs) is not committed.
