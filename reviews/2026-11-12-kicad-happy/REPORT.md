# Node60: kicad-happy review of the routed board (2026-11-12)

Board: `node60.kicad_pcb` as on `main` at `264352a` (6 layers, 2.0 mm, fully routed), with `node60.kicad_sch`, `node60.kicad_dru` and the working copy's `node60.kicad_pro`. Tools: kicad-happy 3.0.1, KiCad 10.0.7 (`kicad-cli`). Read-only: no design file was changed, nothing committed. No KiCad lock file was present.

## Verdict

No analyzer finding contradicts the routing result: KiCad DRC has 0 errors and 0 unconnected items (also with zones refilled), and parity shows only the 19 known `ki_fp_filters` warnings. The analyzers' 10 "errors" are all either false positives or already-recorded decisions.

Three new points need your attention:

1. **U501 (LAN8670) has no via in its exposed pad**, and that pad is the PHY's only ground.
2. **The 0.35/0.20 mm via (0.075 mm ring) is used well beyond U401**: 124 of the 213 are elsewhere on the board, so the recorded "assumed OK with JLCPCB" covers more than CLAUDE.md says.
3. **Small clean-ups near U501**: two vias on top of each other and two 0.475 mm dangling track ends.

Everything in this review is a consistency check, not a datasheet check: the repo has no `datasheets/` folder, so no finding is datasheet-backed (analyzer DS-002).

## What ran

| Check | Tool | Output | Result |
|---|---|---|---|
| Schematic analysis | `analyze_schematic.py` | `schematic.json` | 115 findings: 0 error, 3 warning, 112 info |
| PCB analysis (`--full --proximity --schematic`) | `analyze_pcb.py` | `pcb.json` | 371 findings: 10 error, 211 warning, 150 info |
| Schematic-to-PCB cross-check | `cross_analysis.py` | `cross_analysis.json` | 2 warnings |
| EMC, CISPR 25 Class 5, market automotive | `analyze_emc.py` | `emc.json` | 56 findings: 0 error, 32 warning, 24 info; score 76/100 |
| Thermal | `analyze_thermal.py` (85 °C ambient) | `thermal.json` | skipped by the tool, see below |
| KiCad DRC with parity, all severities | `kicad-cli pcb drc` | `kicad_drc.json` | 0 errors, 380 warnings, 0 unconnected, 19 parity warnings |
| Same, zones refilled in memory | `kicad-cli pcb drc --refill-zones` | `kicad_drc_refilled.json` | identical counts |
| KiCad ERC, all severities | `kicad-cli sch erc` | `kicad_erc.json` | 0 errors, 2 warnings |
| JLCPCB design rules | manual, against JLCPCB's capabilities page fetched today | this report | see the JLCPCB section |

Component counts agree: 282 schematic components, 282 footprints, 314 nets on both sides. All 212 BOM parts carry an MPN.

## New findings, by severity

### N1. High: U501 exposed pad (VSS) has no vias

- **Evidence:** `pcb.json` TV-001, warning, deterministic: "Thermal vias: U501 none (0/9 min)". U501 at (156.0, 43.55) on B.Cu, pad 33 is 3.5 × 3.5 mm on GND. I checked the via list myself: no via of any net inside the pad, and the nearest GND vias are 4.7 to 6.0 mm from the pad centre, at (158.34, 39.45), (151.10, 42.59), (158.50, 48.15), (159.01, 47.95) and (156.60, 49.47).
- **Why it matters:** in the schematic, pad 33 (VSS) is U501's only ground pin; pins 11 and 32 are strap and wake pins tied to GND, not supply returns. The PHY's whole return current therefore goes sideways through the B.Cu ground pour, which the 0.1 mm escape tracks cut up, before it reaches a via to the In4 and In1 ground planes. That is a ground-inductance and emissions concern for the 10BASE-T1S transceiver, more than a thermal one. KiCad DRC can't see it: the pad is connected.
- **Not covered by a decision.** D25 A leaves "interior stitching" for after routing, but nothing records vias in this pad. The rule file has an `ESCAPE_U501` area and no pad-via requirement.
- **Suggested fix:** a 3 × 3 array of 0.45/0.25 mm GND vias in pad 33 (they are filled and capped already). The analyzer's "9 minimum" is its generic figure for the pad size, not Microchip's; check the LAN8670 data sheet's land pattern.

### N2. Medium: the 0.075 mm via ring is used across the board, not only under U401

- **Evidence:** `pcb.json` DFM-001 (error, deterministic) and DFM-002 (warning, deterministic): annular ring 0.075 mm. Via sizes: 2,287 × 0.45/0.25, 213 × 0.35/0.20, 60 × 0.40/0.20. Of the 213, only 89 are inside U401's body; 124 lie between x 74.75 and 230.75, y 34.7 and 112.0. Nets include SPI5_SWITCH2 (19), SW_LHI (7), SW2_FLT_L (6), T1S_TERM_CT (6), SW_VDD of outputs 3-4 (5), T1S_TERM_DROP (5), GND (4), HGATE_G (4), T1S_P and T1S_N (3 each), VBAT_PROT (2), LM_SW (2), RMII and MDIO.
- **Against the record:** CLAUDE.md records the 0.075 mm ring on the 2 oz inner layers as "assumed OK for now, checked before ordering", and says that if JLCPCB refuses, "the vias under U401 and the In3 planes there are redone". The exposure is now wider than that sentence: a refusal would also reopen the power-band channels, the T1S taps and the switch 2 SPI bus.
- **JLCPCB's page today:** via diameter at least 0.1 mm over the hole, 0.15 mm preferred, so 0.35/0.20 meets the via rule. The 0.254 mm figure for 2 oz is in the PTH annular ring row; the page has no separate via row for 2 oz. The question to JLCPCB is the same as before, only for 213 vias on five layers instead of the ones under U401.
- **Suggested action:** ask JLCPCB before more work depends on it, and update the CLAUDE.md sentence. Vias outside the BGA that have room could go to 0.45/0.25.

### N3. Low: duplicate via and two dangling track ends at U501

- **Evidence:** `kicad_drc.json`, warnings. `holes_co_located`: two T1S_REFCLK vias at the same spot (157.0, 47.35). `track_dangling`: a 0.475 mm B.Cu track of MDIO0_T1S_MDC ending at (156.25, 41.10) and one of MDIO0_T1S_MDIO ending at (156.75, 41.10).
- **Why it matters:** the double via gives a double drill hit in the drill file; the stubs are harmless electrically but are leftovers from routing. Both are simple deletions.

### N4. Low: 377 silkscreen warnings

- **Evidence:** `kicad_drc.json`: 199 `silk_overlap` (reference text over other silk, for example C203 on C204, C415 on C404), 162 `silk_over_copper` (reference text over pads, clipped by the fab), 16 `silk_edge_clearance` against the outline.
- Reference text hasn't been arranged since placement. Not a routing defect; a job before fabrication outputs.

### N5. Low: L302 is 1.0 mm from the north board edge

- **Evidence:** `pcb.json` PM-002, warning, deterministic. L302 at (217.4, 33.3) on B.Cu. It is at the analyzer's limit, not under it. Worth a look against the removable north panel and the GND ring that runs 1 mm in from the edge (D25 A). DRC is clean.

### N6. Info: return vias at signal layer changes

- **Evidence:** `emc.json` RP-001, 20 warnings and 2 info, deterministic, and "21+ nets (truncated)": layer changes with no GND via within 1.0 mm, for example RESET_L (11 of 11), SPI5_SWITCH2_MISO (11), RMII0_T1S_RXD1 (6), RMII0_T1S_RX_ER (5), T1S_TERM_DROP (9).
- **Partly covered:** D25 A puts interior stitching after routing, so this is the worklist for that step, not a defect of the route. Most of the nets are slow (NTC, fault lines, gate drives). The ones that deserve a return via are the RMII lines; the board has 446 GND vias in all. Note that F.Cu to B.Cu and to In2 all have a GND plane next to them (In1, In4), so a return via matters where a signal moves between the In1 and In4 references.

## Findings already covered by a recorded decision

| Analyzer finding | Evidence | Covered by |
|---|---|---|
| PM-002 × 8, error, deterministic: J903 to J909 and J912 courtyards overhang the edge by 13.9 to 15.6 mm | `pcb.json` | The AT13/ATM13 headers sit on the board edge by design (DEC-024/025, `place_connectors.py`) |
| DFM-001, error: annular ring 0.075 mm | `pcb.json` | Recorded assumption (CLAUDE.md, D23 A), but see N2 for its scope |
| DFM-001, warning: 0.1 mm tracks | `pcb.json`: 241 segments, all on F.Cu and B.Cu, all within x 152.5 to 210.1, y 39.5 to 60.4 | D12 escape areas ESCAPE_U401 and ESCAPE_U501; none on an inner layer |
| VP-001 × 185, warning, heuristic: via in SMD pad | `pcb.json` | Vias are filled and capped (set 2026-11-04 for the in-pad vias); JLCPCB lists fill and cap for 0.15 to 0.55 mm vias, and all vias here are 0.35 to 0.45 mm |
| CC-002 × 20, warning: narrow signal tracks 0.1 mm | `pcb.json` | Same escape areas |
| Parity: 19 × missing `ki_fp_filters` | `kicad_drc.json` | CLAUDE.md "Schematic parity": KiCad always reports them. The C207, C217 and L201 warnings recorded there are gone |
| CK-003, warning: T1S_OSC_OUT and T1S_REFCLK within 6.9 and 7.8 mm of J903 | `emc.json`, deterministic | D27 A placed Y501 between J903 and U401 for RMII timing. The 50 MHz clock beside the T1S connector is worth a near-field probe at the emissions test |
| CK-002, warning, heuristic: SPI4_SWITCH1_SCK 224 mm, SPI5_SWITCH2_SCK 122 mm | `emc.json` | DEC-018 (one LPSPI bus per switch). No series resistor on any SCK net (U401, test point, switch only): slow pad slew in firmware is the only edge control |
| SW-001/EE-002: buck harmonics | `emc.json`, heuristic | DEC-026. The analyzer assumed 500 kHz for both bucks ("topology_default"); U303 runs at 2.25 MHz, so its numbers are wrong for U303 |
| TE-001: test points on 48 of 313 nets | `pcb.json` | The 62 test points are the chosen set |
| CP-002 × 32, info: no copper opposite connectors and bars | `pcb.json` | Busbar rule areas |

## False positives

| Analyzer finding | Why it is wrong |
|---|---|
| RT-001, error, deterministic: "/VBAT_IN incompletely routed, 3 copper islands" (D201 pad 2 and U201 pin 2 apart from the rest) | Both join through small pours that touch a larger pour of the same net: `PWR_VBAT_IN_D201_F` on F.Cu (D32) and `PWR_VBAT_IN_U201_In2` on In2 (D36 A). The analyzer doesn't merge touching zones. KiCad reports 0 unconnected items, also after a refill. |
| TV-001, warning: U201 pad 25 (RTN) has no vias and is unconnected | The schematic leaves RTN unconnected on purpose. From memory, TI asks for the LM749x0 exposed pad to float; not checked against the data sheet here. |
| PU-001, warning, heuristic: U201 TMR needs a pull-up | TMR is a timer-capacitor pin, not open-drain. |
| RS-001, warning, heuristic: VBAT_Q2D has no source | It is the node between the shunt and the load-disconnect FETs. |
| CC-001 and TW-001, warning, heuristic: 3V3_MAIN 0.20 mm track "for 0.7 A" at J401 | The current is guessed from output capacitance. J401 takes only the debug probe's reference; 3V3 is carried by the In3 plane. |
| EP-AUD, info: J903 and J912 have no ESD protection | D501 to D504 (VETH100A1DD1HG3-08) are on T1S_P and T1S_N; the analyzer didn't recognise the part. |
| IO-001 × 15, info: no EMC filtering near connectors | Includes the busbars and the SurLok terminals; the outputs are switched battery lines. |
| TF-001, info: U203 "isolated SMPS controller" | U203 is the TMP175 temperature sensor. |
| ERC `pin_to_pin` × 2: U501 pins 11 and 32 against a PWR_FLAG | Both pins are tied to GND, which carries the flag. |

## JLCPCB rules (6 layers, 2.0 mm, JLC062012-1080)

Compared with JLCPCB's capabilities page as fetched on 2026-11-12.

| Item | Board | JLCPCB | Status |
|---|---|---|---|
| Thickness, layers | 2.0 mm, 6 | 2.0 mm listed | OK |
| Size | 230 × 110 mm | within limits | OK |
| Track and space, 1 oz outer | 0.10 mm min (escape areas), 0.15 elsewhere | 0.09/0.09 multilayer | OK |
| Track and space, 2 oz inner | 0.15/0.15 (rule), In2 tracks all 0.15 mm or wider | 0.15/0.15 | OK, at the limit |
| Via hole and diameter | 0.20 and 0.25 mm holes, 0.35 to 0.45 mm | 0.15 / 0.25 min; holes of 0.2 to 0.25 with diameter under 0.45 "cost more" | OK; 273 vias in the dearer class |
| Via ring on 2 oz inner layers | 0.075 mm on 213 vias, 0.10 mm on 2,347 | PTH row: 0.254 mm for 2 oz; no via row | Open, see N2 |
| Via hole to hole | rule 0.25 mm | 0.2 mm | OK, except the duplicate via (N3) |
| Via hole to track | rule 0.2 mm (0.225 at the UART pinch) | 0.2 mm | OK |
| PTH to copper | rule 0.35 mm | 0.28 min, 0.35 recommended | OK |
| Copper to edge | 0.3 mm | 0.2 mm routed edge | OK |
| Filled and capped vias | all vias, 0.35 to 0.45 mm | 0.15 to 0.55 mm, default on 6 layers | OK |
| Silk text | rule 1.0 mm / 0.15 mm | 1.0 mm / 0.15 mm | OK, at the limit |

Not checked against JLCPCB: SMD pad-to-pad spacing between nets (page: 0.15 mm; the board's global clearance is 0.10 mm), same-net track spacing (0.25 mm), and anything about assembly (LCSC numbers, two-sided assembly, rotations).

## Checks that could not run

- **Datasheet verification:** no `datasheets/` folder. Distributor API keys are set on this workstation, but a sync downloads files, which I didn't do without your say-so. Every pin-level and value statement here is consistency only.
- **SPICE:** the schematic analyzer found simulatable subcircuits (10 RC filters, 8 dividers), but no simulator is installed (`ngspice`, `ltspice`, `xyce` all missing).
- **Thermal:** `analyze_thermal.py` ran and skipped all four candidates: "no components had quantifiable power dissipation data". It needs datasheet extractions. The 10 A thermal question stays with the release blocker.
- **Lifecycle audit:** not run (analyzer LC-007); it calls distributor APIs.
- **Gerber analysis:** no fabrication outputs in the repo.
- **EMC coverage:** findings came from 5 of the tool's 18 categories (I/O filtering, clock routing, return path, switching, emission estimate); the others raised nothing. The tool rates its own CISPR 25 radiated coverage "minimal" and says ISO 7637-2 is lab only. No ground-plane, decoupling-distance or differential-pair finding was raised.
- **Deep review pass and prior-review delta:** not done; no datasheets, and this is the first kicad-happy run.

## Analyzer facts worth keeping

- Y401: 2 × 10 pF gives about 8 pF load with 3 pF stray, matching the "-8-" crystal. The analyzer's "-60 % error" compares against a default 20 pF target.
- U303 feedback: 76.8 kΩ / 51 kΩ with an assumed 0.6 V reference gives 1.504 V (reference is the analyzer's guess, not from the data sheet).
- T1S_P 62.97 mm, T1S_N 64.36 mm over the whole net including taps and stubs; the board's own skew rules pass.
- Decoupling: U401's nearest caps are 0.52 mm away (25 caps within 7.1 mm), U501 has 10 within 3.3 mm.
- Thermal vias: Q201 to Q204 104 to 127 each, U601/U701/U801 31 each.

## Summary for the user

1. **Add GND vias in U501's exposed pad** (N1). It is the PHY's only ground and has none; the nearest GND via is 4.7 mm from the pad centre.
2. **Ask JLCPCB about the 0.075 mm ring now** (N2): 124 of those vias are outside U401, on SPI, T1S, RMII, gate and two VBAT_PROT connections, so a refusal costs more than CLAUDE.md records.
3. **Delete the duplicate T1S_REFCLK via and the two MDC/MDIO stubs** (N3).
4. Before fabrication outputs: silkscreen (N4), return vias on the RMII lines during stitching (N6), L302's edge distance (N5).
5. To make this a datasheet-backed review: sync datasheets and install ngspice, then re-run.
