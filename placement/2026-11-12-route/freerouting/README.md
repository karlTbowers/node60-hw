# Freerouting trial, 2026-11-12

A one-day trial of [Freerouting](https://github.com/freerouting/freerouting) as the bulk router for
Node60, beside the KiCadRoutingTools (KRT) routing run in this folder. **Result: not used.** This
branch (`trial/freerouting-2.5.0`, cut from main `b404f9c`) is the record, so a later Freerouting
release can be tried the same way and compared.

## Result

Board: the prepared board of the routing run (`work/b/p1.kicad_pcb`, the copper of main `b404f9c`),
133 signal joins open in 69 nets, test points parked. Graded with KiCad 10.0.7's DRC under the
board's own `node60.kicad_dru` and `node60.kicad_pro`. "Signal joins" leaves out joins at a test
point and joins of the plane nets (GND, 3V3_MAIN, 1V5_CORE, VBAT_*, VDDAU_AON, OUT1-6).

| Attempt | Signal joins open | DRC errors | Run time |
|---|---|---|---|
| Prepared board, nothing routed | 133 in 69 nets | 0 | |
| Freerouting run 1 (no via possible, see below) | 74 in 46 nets | 26 | 146 min |
| **Freerouting run 2, as routed (best attempt)** | 46 in 29 nets | 136 | 83 min |
| Freerouting run 2, only the nets with no error | 76 in 42 nets | 0 | |
| KRT, first bulk pass (`work/b/r1`) | 21 in 16 nets | 5 | minutes |
| KRT, after its repair rounds (`work/b/t5`) | 10 in 9 nets | 0 | |

- Run 2's 136 errors: 110 "items not allowed" (tracks on In2 south of y 70, in the power band
  that decision D17 A closes to signals, in 18 nets), 14 track width, 12 clearance (most on
  `T1S_P`: Freerouting added copper to the hand-routed T1S line and broke its 0.75 mm rule).
- Counting only what it routed within the rules, Freerouting closed 57 of 133 joins. KRT's first
  pass closed 112.
- Freerouting did not converge. In both runs the count of open connections swung from pass to
  pass (run 2: 121, 157, 128, 154, 120, 149, 115, 115, 146, 113 by its own count, plane nets
  included). Run 1's best pass was its first of 18.
- Each pass takes 6 to 10 minutes on this board (single-threaded; M1 Mac Studio, 20 cores).

## Why it does poorly here

1. **Node60's rules don't fit in a Specctra DSN.** The file carries widths, one clearance per
   class, and keep-outs. It cannot say "tracks no, vias yes" in a way Freerouting honours (see
   the next point), nor the T1S 0.75 mm rule, the busbar rules or the under-crystal rule. Each
   one has to be faked with keep-out areas, and what can't be faked comes back as DRC errors.
2. **Freerouting reads a tracks-not-allowed area as a full obstacle, vias included.** KiCad
   exports it as `wire_keepout`; Freerouting 2.5.0 treats that like `keepout`. The POWER_ONLY
   areas on In1, In3 and In4 cover the board, so in run 1 no via was legal anywhere: 0 new vias,
   and 12,740 "pre-existing violations" at load (the board's own vias against those areas).
   Run 2 removed them and marked In3 a power layer, which left In2 south of y 70 open, and
   Freerouting used it.
3. **KiCad exports a rule area that forbids nothing as a full keep-out.** ESCAPE_U401/U501 and
   the In2 signal window walled off the BGA and the PHY until `fr_export.py` deleted them from
   the scratch copy (the very first attempt fanned out 0 pins).
4. **The power band.** Under the rules, signals in the band have B.Cu only, and B.Cu there is
   power pour (see this run's `REPORT.md`). Freerouting found no way through either: every band
   net it closed, it closed on In2 south of y 70.

## What the KRT run can take from it

- **Three short joins at U201 that KRT left open do route**, each on B.Cu alone, when they are
  laid before their neighbours: `LM_CSP` (4.4 mm, x 153.75-156.6, y 77.4-79.5), `LM_TMR`
  (4.7 mm, x 149.1-152.75, y 71.6-73.6) and `RS_SENSE_P` (8.3 mm, x 156.15-159.0,
  y 77.35-82.47). On KRT's board `t5` the same paths are blocked by `RS_SENSE_N` and `INH`
  copper routed earlier (transplanting them gives 14 errors, all against those two nets). So:
  pre-route these three by hand or with `mini_route.py` before the bulk pass, then let
  `RS_SENSE_N` and `INH` go round them. Freerouting's copper for them is in
  `run2/freerouting-best.kicad_pcb`.
- **An independent router agrees the band does not route within the rules.** `DGATE`, `SW2_SNS`
  and `SPI4_SWITCH1_CS_L` (open in `t5`) were closed only through In2 south of y 70. `SW_LHI`,
  `HGATE_G` and `LM_OV` stayed open in both routers. That supports asking the user for room
  (decision D33) over spending more router time.
- **Nothing to copy from its method.** Its fan-out stage escaped 56 % of the pins and stalled;
  KRT's BGA escape and its repair rounds do better on this board.

## What a fairer retry would need

- A way to keep tracks off a layer region while letting vias through. Check whether a newer
  Freerouting honours `wire_keepout` as tracks-only; that alone would let In2 south of y 70 and
  the busbar areas be given as they are.
- The already-routed T1S line marked so Freerouting leaves it alone (it treated `T1S_P` as
  incomplete and added to it).
- Net exclusion for the plane nets (not tried; the command line has no option for it).
- The pass limit is `-mp N`. `--router.autorouter.max_passes` is not known to 2.5.0 and was
  ignored in run 1.

## How to repeat

Freerouting 2.5.0 (build 2026-10-05, the jar from the project's GitHub release) on OpenJDK 27
(Homebrew), KiCad 10.0.7. `$KPY` is KiCad's Python.

```
cd placement/2026-11-12-route
cp work/b/p1.kicad_pcb work/fr/in.kicad_pcb            # with its .kicad_pro and .kicad_dru
$KPY route_hook.py work/fr/in.kicad_pcb                 # T1S, crystal and switch-node keep-outs
$KPY fr_export.py work/fr/in.kicad_pcb work/fr/in.dsn --open-planes
java -jar freerouting-2.5.0.jar -de work/fr/in.dsn -do work/fr/out.ses -mp 10
$KPY freerouting/import_ses.py work/fr/in.kicad_pcb work/fr/out.ses work/fr/fr_routed.kicad_pcb
$KPY transplant_new.py work/fr/fr_routed.kicad_pcb work/b/p1.kicad_pcb work/fr/g.kicad_pcb --skip <plane nets>
kicad-cli pcb drc --refill-zones --save-board --severity-all --format json -o work/fr/g.drc.json work/fr/g.kicad_pcb
python3 freerouting/sum_drc.py -v work/fr/g.drc.json
```

The transplant puts only Freerouting's new signal copper onto the real prepared board (with its
test points and every rule area), so KiCad judges it under the real rules.

## Files

| File | What |
|---|---|
| `../fr_export.py` | scratch board to DSN: drops test points and the rule areas Freerouting misreads |
| `import_ses.py`, `sum_drc.py` | session import; DRC summary (errors by type, open joins by kind) |
| `run1/` | log, session file and DRC report of the run with no via possible |
| `run2/in.dsn`, `out.ses`, `fr.log` | the best run's input, output and log |
| `run2/freerouting-best.kicad_pcb` (+ `.kicad_pro`, `.kicad_dru`) | the best attempt on the prepared board, zones refilled; not a usable board |
| `run2/g2.drc.json`, `g2.badnets.json` | its DRC report and the 23 nets with an error |
| `run2/g2s.drc.json` | DRC report of the same with those 23 nets' new copper left out |

The `.kicad_dru` beside the board is the working copy of 2026-11-12 evening, which already held
the routing session's uncommitted D33 B edit (signal tracks allowed on F.Cu under the GND bar).
The export kept F.Cu under both bars closed to Freerouting, so that edit does not touch its
result; KRT's boards in the table were graded before it.

The Freerouting MCP server was not installed: its quick-start mode uploads the board to
Freerouting's public API, and its offline mode runs the same engine as the command line above.
