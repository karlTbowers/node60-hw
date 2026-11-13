# Node60: kicad-happy analyzers after the fixes (2026-11-13)

The same analyzers as `reviews/2026-11-12-kicad-happy/` (kicad-happy 3.0.1, KiCad 10.0.7), run on the board
after `placement/2026-11-13-kicad-happy-fixes/`. KiCad's own DRC result is in that folder's
`checks/kicad_drc.json`. What was done and why: that folder's `REPORT.md`.

| Check | Before | After |
|---|---|---|
| KiCad DRC | 0 errors, 380 warnings, 0 unconnected | 0 errors, 19 warnings, 0 unconnected |
| Schematic parity | 19 (`ki_fp_filters`) | 19 (the same) |
| `analyze_schematic.py` | 115 findings | 114 (DS-002, no datasheets, gone) |
| `analyze_pcb.py --full --proximity --schematic` | 371: 10 error, 211 warning, 150 info | 374: 11 error, 210 warning, 153 info |
| `cross_analysis.py` | 2 warnings | 2 warnings (the same) |
| `analyze_emc.py`, CISPR 25, automotive | 56: 32 warning, 24 info; score 76 | 56: 13 warning, 43 info; score 82 |
| `analyze_thermal.py`, 85 °C | skipped | skipped (needs structured datasheet extractions) |
| `lifecycle_audit.py`, DigiKey, −40 to +125 °C | not run | 72 parts: 69 active, 3 unknown; 69 temperature checks, 0 failing |

## The review's findings

| Finding | Analyzer line before | After |
|---|---|---|
| N1 | TV-001 warning: "Thermal vias: U501 none (0/9 min)" | TV-001 info: "U501 adequate (10/9 min)": the nine pad vias, and the analyzer counts one more beside the pad |
| N2 | DFM-001 error, DFM-002 warning: annular ring 0.075 mm | the same two lines: they report the smallest ring on the board, and 131 vias still have it (213 before) |
| N3 | DRC `holes_co_located` 1, `track_dangling` 2 | 0 and 0 |
| N4 | DRC `silk_overlap` 199, `silk_over_copper` 162, `silk_edge_clearance` 16 | 0, 3 and 16 (footprint graphics) |
| N5 | PM-002 warning: L302 1.0 mm from the edge | the same (no part moved; nothing is violated) |
| N6 | RP-001: 20 warnings, 2 info | 1 warning (the summary line), 21 info, fewer uncovered transitions on every net |

## New in the analyzer's output

- **RT-001 error, "Incompletely routed net GND (3 copper islands hold its 190 pads)": false.** It appears with
  the stitching vias. KiCad's DRC reports 0 unconnected items with zones refilled, and
  `placement/2026-11-13-kicad-happy-fixes/net_islands.py` (pours, tracks, pads and vias joined by their real
  shapes) finds one GND island holding all 190 pads, and one VBAT_IN island holding all 20 (the analyzer's
  other RT-001 line, already a false positive in the first review).
- TB-001 (0402 tombstoning risk, info) 75 to 77: R408 and R503 are new. Each has a new GND via 0.7 to 0.9 mm
  from one pad (another net's via, not in the pad); the heuristic reads a nearby via as thermal asymmetry.

## Lifecycle audit

DigiKey lists 69 of 72 part numbers as active and rated for the range. Unknown: the two busbars (made to
drawing, no distributor part) and LAN8670D0-E/LMXVAO, which DigiKey's search did not resolve under that
number. The PHY's stock is already a release blocker in `CLAUDE.md`.

## Still not run

Structured datasheet extraction (the PDFs are fetched; `datasheets/` is git-ignored), so the IC-aware
detectors and the thermal analyzer stay at heuristics; SPICE (no simulator installed); Gerber analysis (no
fabrication outputs).
