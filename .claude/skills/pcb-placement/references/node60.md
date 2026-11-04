# Node60: where the plan's answers are

Node60's plan is mostly already written in the repo. This page says where, as of 2026-11-02;
re-read the sources on every run (they change), and treat anything here that disagrees with
them as stale.

| Plan item | Node60 | Source |
|---|---|---|
| Outline | 230 × 110 mm, 2.0 mm, drawn by `place_connectors.py` | `CLAUDE.md` (DEC-024, DEC-025) |
| Stackup | 6 layers, 2.0 mm, JLCPCB stackup JLC062012-1080 (1 oz outer, 2 oz inner; DEC-027, 2026-11-03); JLCPCB's rules apply (0.15 mm track and space on the 2 oz inner layers); 2 oz outer copper for high current and the 0.20 mm via option still open | `CLAUDE.md`, DEC-027, site page "PCB stackup & fab quotes" |
| Fixed parts | J901–J912 and the busbar footprints BB901/BB902, from `scripts/place_connectors.py` (version `CURRENT`, v15); J401 debug header and D201 on F.Cu | `CLAUDE.md`, memory "debug header on top" |
| Sides | nearly every part on B.Cu; on F.Cu only 0402/0603 decoupling, D201 and J401 | `CLAUDE.md` (DEC-024) |
| Busbars | 1/8" × 3/4" C110 bars resting on the REDCUBE spigots 0.6 mm above the top face; rule areas `BUSBAR_VBAT_IN`, `BUSBAR_GND`: F.Cu under each takes only the bar's own net | `node60.kicad_dru`, `CLAUDE.md` (DEC-023, DEC-025) |
| Parts under a busbar | top: none (BB901/BB902 courtyards); bottom: a plan decision, by whether each part's nets can leave without a through via | `references/fast-route.md` |
| Lid bosses | Ø8 mm bosses under each SurLok receptacle, 3.5 mm past the bar and 5.0 mm above the board: J401 and D201 stay out from under them | `CLAUDE.md` (DEC-025), `scripts/enclosure_geometry.py` |
| Height above the board | 9.0 mm under the low lid (not yet checked against the parts); raised band and hood 1 mm above the tallest header | `CLAUDE.md` |
| Height below the board | board 6.17 mm off the floor; K501 (5.2 mm) leaves 0.97 mm | `CLAUDE.md` |
| Critical link | 10BASE-T1S: J912–J903 trunk in the middle of the north edge (39 mm apart), line interface (K501, termination legs and centre tap, ESD diodes, DC-block caps, FL501) on B.Cu under the trunk's midpoint in an exclusive zone between the connectors' inner pins; the bucks' switch nodes kept at least 10 mm from the T1S line nets (closest 11.8 mm; LM_SW is the LM74910's OV/UV ladder switch, not a switching node) | `CLAUDE.md` (user, 2026-11-01), DEC-012 rev. B, DEC-017 |
| Critical nets | T1S trunk and stub (`/T1S_P`, `/T1S_N`, `/T1S/T1S_*`, class `T1S_100R`); RMII U401–U501 (`/RMII0_T1S_*`, with `REF_CLK`); MCU crystal Y401 on `FXOSC_EXTAL`/`FXOSC_XTAL` (10 pF C0G loads, 0 Ω RsEXT); INA228 (U202) and LM74910H (U201) sense pairs from the 4-terminal 0.3 mΩ shunt R201's sense pads (`RS_SENSE_P` pad 2, `RS_SENSE_N` pad 3; force pads `VBAT_D` 1 and `VBAT_Q2D` 4; D14-1, 2026-11-03); LM74910 (U201) current sense through R209, C212, C213 | the netlist; `CLAUDE.md` schematic review answers |
| Heat | three TPS2HCS08A-Q1 (U601, U701, U801), up to 10 A per channel (8 A rated with both channels on at 85 °C: unproven); LM74910 FETs Q201–Q204 and R201 on the 40 A pass-through; bucks U302 (3V3_MAIN) and U303 (1V5_CORE) | `CLAUDE.md` release blockers, DEC-016 |
| Switchers | U302, U303 (LMQ66430-Q1, VQFN-14): VIN pin 3, PGND 6/13/15, SW 7, FB 11 (U302's FB is its output rail) | footprint pads; the datasheet's layout section for the limits |
| BGA | U401 S32K344, LFBGA-257, 0.8 mm: 8 signal rings, 1 track per channel at 0.1/0.1, 4 signal layers needed | `escape_budget.py` |
| MCU and PHY | U401 and U501 north of both busbars (U401 in the north-east corner, U501 between it and the T1S zone): no other-net via may sit under a bar | `CLAUDE.md`, `references/fast-route.md` |
| Output channels | U601 + parts composed once; U701, U801 copies (same sheet file placed three times) | sheet plan in `CLAUDE.md` |
| SPI | one LPSPI per switch: U601 LPSPI4, U701 LPSPI5, U801 LPSPI3 | DEC-018 |
| Net classes | only `T1S_100R` exists; every rail sits in Default: power classes are a plan item | `node60.kicad_pro` |
| Fiducials | none on the board yet | `gate.py` |
| Schematic parity | 257 items on 2026-11-02 (199+ field mismatches, 56 footprint/symbol mismatches, 2 missing footprints): look before the gate | `gate.py` |

## Known open items a Node60 run will meet

- The stackup is chosen (DEC-027: 6 layers, 2.0 mm, JLC062012-1080), but the layer roles are
  not: the escape budget's 4 signal layers fit it with two planes (GND, VBAT_PROT), so the
  layer plan can be proposed, but the choice is the user's.
- Whether any bottom-side part may stand under a busbar.
- Fiducials, and how heavy bottom parts are held in reflow.
- Power net classes and widths for the 10 A outputs and the 40 A path (handbook chapter 05:
  every path above about 3 A gets its width, copper and via count calculated).
