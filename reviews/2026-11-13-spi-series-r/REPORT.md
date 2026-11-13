# Node60: kicad-happy analyzers after the SPI series resistors (2026-11-13)

The same analyzers as `reviews/2026-11-13-kicad-happy-after/` (kicad-happy 3.0.1), run on the board after
`placement/2026-11-13-spi-series-r/`. What was done and why: that folder's `REPORT.md`.

| Check | Before | After |
|---|---|---|
| KiCad DRC | 0 errors, 19 warnings, 0 unconnected | the same |
| Schematic parity | 19 (`ki_fp_filters`) | 19 (the same) |
| `analyze_schematic.py` | 114 findings | 115 (DS-002 back: `datasheets/` is git-ignored and absent from this worktree) |
| `analyze_pcb.py --full --proximity --schematic` | 374: 11 error, 210 warning, 153 info | 388: 11 error, 220 warning, 157 info |
| `cross_analysis.py` | 2 warnings | 2 warnings (the same) |
| `analyze_emc.py`, CISPR 25, automotive | 56: 13 warning, 43 info; score 82 | 56: 13 warning, 43 info; score 82 |

- **CK-002 still prints**, for `/SPI4_SWITCH1_SCK` (212 mm, was 224) and `/SPI5_SWITCH2_SCK` (106 mm, was 122).
  It is a heuristic on a clock net's length; it has no check for a series resistor. Both lines now have one at
  U401 (R409, R412).
- New in `pcb.json`: ten VP-001 warnings (a via in a pad of R410 to R414 and R416; all vias are filled and
  capped), four TB-001 info lines (R410, R411, R415, R416), and three CC-002 lines carrying the new `_MCU` net
  names in place of the old ones (0.1 mm escape tracks under U401, unchanged).

Not run again: thermal (skips, as before), lifecycle audit (no new part number).
