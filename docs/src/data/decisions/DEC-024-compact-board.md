---
id: DEC-024
title: Compact 230 × 110 mm board (enclosure version 11)
status: superseded
date: 2026-11-01
revision: B
page: subsystems/enclosure
supersedes: [DEC-023]
requirements: [REQ-NET-001, REQ-PWR-002, REQ-QUAL-001]
parts: [74660016R, SLPRATPSR, SLPRATPSB, AT13-2P-BM04, ATM13-2P-BM04]
gates: [GATE-HAR-01, GATE-HAR-02, GATE-THM-02]
rejected:
  - option: Keep version 10's 250 × 160 mm board (DEC-023)
    reason: A placement trial on the 230 × 110 mm board fitted every part with nearly all of them on the bottom side, so the larger board buys nothing the layout needs and makes the enclosure bigger.
---

## Context

DEC-023 chose enclosure version 10: version 7 on a 2.0 mm board, 250 × 160 mm. Version 9 is version 7 with every connector as close to the next as the checks allow, giving a 230 × 110 mm board, and version 11 is version 9 on version 10's 2.0 mm board. When version 9 was drawn, it was not known whether the parts would fit on the smaller board.

On 2026-11-01 the user allowed parts on the bottom side, and a placement trial (KiCadRoutingTools `place_simple`, branch `layout/placement-v11`) placed every part on the version 11 board. Everything is on the bottom except the 0402/0603 decoupling caps and three parts taller than the 5 mm the board then stood off the floor (6.17 mm since the SurLok correction of 2026-11-02): the relay K501, the TVS D201 and the debug header J401, which stays on top so an installed board can be programmed. The placement passes its floorplan checks, assembles and passes DRC with schematic parity. The user chose version 11 the same day.

## Decision

- **The PCB is 230 × 110 mm, 2.0 mm thick: enclosure version 11.** Version 9's plan:
  - outputs J904–J909 at a 37.3 mm pitch on the front edge;
  - the T1S pair J903/J912 39 mm apart in the middle of the north edge;
  - battery receptacles 53 mm from the centre line, return receptacles 78.5 mm;
  - plugs pointing west or east may reach past the side walls.
- **Version 10's heights:** the busbars rest on the REDCUBE spigots 0.6 mm above the board, and the front band and T1S hood are 0.6 mm lower than version 9's. Outside, the enclosure is 237.7 × 117 mm, 24.2 mm tall at the low lid and 44.7 mm at the band and hood, with 9.0 mm under the low lid above the board.
- **Unchanged from DEC-022 and DEC-023:**
  - component side up, 6.17 mm off the floor (the SurLok stud tip 2 mm above it);
  - the busbars, the lid with a raised front band and a separate T1S hood;
  - the removable north panel;
  - plugs pointing outward or north.
- **Scripts:** `scripts/place_connectors.py` sets `CURRENT = "v11"`, and the PCB is placed from it. `scripts/check_surlok_clearance.py` passes all 16 plug combinations (tightest 2.0 mm, flange to flange), and `scripts/check_assembly.py` fits the board with the removable north panel.

## Consequences

- **Every dimension is at its limit** (version 9's derivation in `place_connectors.py`). Moving a connector, or changing a connector part, means re-running the plug check and the corner rule. The side walls assume an R5 inside corner in the machined base.
- **Room around the node:** a plug pointing west or east reaches up to 5.8 mm past the side wall's outside face, and its cable runs on from there. Leave that room where the node is mounted.
- **Parts on the bottom side.** The bottom faces the floor, 6.17 mm away. A part that leaves less than about 1 mm there goes on top, or the case floor moves down. On top, parts stay clear of the lid's M4 bosses under each receptacle (D201 was moved 1.5 mm for J901's). The input MOSFETs and the output switches face the floor, so a gap pad could take their heat into the case.
- **Heat and current:** the board has 37 % less area to spread the heat from the switches and MOSFETs and less copper to carry the outputs. The dual-channel thermal test (10 A is still unproven, GATE-THM-02) decides whether it is enough.
- **Busbars:** shorter, as the receptacles move in. The cut list is on the version 11 page.
- **Prototype price:** DEC-023's quotes were for the 250 × 160 mm board. Re-quote at 230 × 110 mm (37 % less area) before choosing the fab house.
- **Still open from DEC-023:** Würth's approval of the spigot standing 0.6 mm proud (blocks board release), the SurLok stud length, and the stackup and fab house.
- **Drawings and mockup:** version 11 on the [Enclosure options](../../subsystems/enclosure/) pages and in the [3D mockup](../../mockups/node60-enclosure.html). The other versions stay there as the record of the options.
