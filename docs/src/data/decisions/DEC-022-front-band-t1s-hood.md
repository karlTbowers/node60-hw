---
id: DEC-022
title: Lid with a raised front band and a separate T1S hood, staggered receptacles and a removable north panel (enclosure version 7)
status: accepted
date: 2026-11-01
revision: B
page: subsystems/enclosure
supersedes: [DEC-021]
requirements: [REQ-NET-001, REQ-PWR-002, REQ-QUAL-001]
parts: [74660016R, SLPRATPSR, SLPRATPSB, AT13-2P-BM04, ATM13-2P-BM04]
gates: [GATE-HAR-01, GATE-HAR-02, GATE-THM-02]
rejected:
  - option: Enclosure version 2, a lid with a raised T (DEC-021)
    reason: The user chose version 7 on 2026-11-01. It drops the T's stem, so the lid between the front band and the T1S hood stays low.
  - option: Enclosure version 4, press-fit REDCUBE 786202106 terminals with the busbars on the blocks and a flat lid with receptacle seats
    reason: Chosen on 2026-10-31 as the first DEC-022 and reversed by the user on 2026-11-01 in favour of version 7.
  - option: Two boards, the T1S pair on a microcontroller board under the main board (enclosure version 8)
    reason: The user did not like its assembly (the main board slides in high and drops onto a mezzanine, and the output cutouts grow taller).
  - option: A horizontal parting line through the connector cutouts
    reason: Every header's panel seal would cross the joint, a likely leak path for IP67.
---

## Context

DEC-021 put the board component side up, with SMT REDCUBE terminals underneath, busbars on top and a lid with a raised T: a crossbar over the six outputs and a stem up the middle to the T1S pair on the north wall. Eight enclosure versions were kept as candidates from 2026-10-30. Version 7 is version 2 without the stem: the T1S pair gets its own hood, and the receptacles move to the positions first worked out for version 6.

On 2026-10-31 the user chose version 4 (press-fit terminals, flat lid) as DEC-022 (commit `db153a3`). On 2026-11-01 they reversed that before it reached `main` and chose version 7. This record takes the DEC-022 number in its place.

## Decision

- **Board, terminals and busbars: as DEC-021.** Component side up, 2.6 mm thick, 250 × 160 mm, **5 mm off the floor**. The four SMT REDCUBE 74660016R are on the bottom side (B.Cu), J901 and J910 on VBAT_IN, J902 and J911 on GND. A 1/8" × 1" C110 copper busbar on the top face joins each pair, and each SurLok receptacle's stud passes through its bar into the REDCUBE.
- **Positions:**
  - **Battery:** J910/J901, 52 mm either side of the centre line, 58 mm from the front edge.
  - **Return:** J911/J902, 78 mm either side, 105 mm from the front edge.
  - **T1S:** J903/J912 in the middle of the north wall, 40 mm apart.
  - **Outputs:** the six outputs on the front wall at a 40 mm pitch.

  The receptacles are staggered so a battery plug's cable pointing north passes beside the return receptacle and clear of the T1S hood.
- **Lid:** 4 mm thick, machined from solid aluminium.
  - **Low level:** across the middle of the case, where the receptacles' panel faces sit, 22.4 mm above the board (busbar plus the SurLok's 19.2 mm). An Ø8 × 4 mm boss under each of a receptacle's four M4 holes gives 8 mm of thread.
  - **Raised front band:** across the full width, 28.1 mm deep, over the six AT13 outputs.
  - **T1S hood:** a separate raised section over the T1S pair on the north wall, 82.8 × 33.4 mm.
  - **Height of the raised sections:** both are 1 mm above the tallest header inside, 11.1 mm above the low level.
- **Walls and floor:** 3 mm, machined from solid aluminium. Outside, 257 × 167 mm; 33.0 mm high at the low level, 44.1 mm at the band and the hood.
- **Removable north panel:** the board has headers on the north and south walls, so it can't go into one-piece walls. The base is the floor and the front, east and west walls. The north panel is a separate part and carries the T1S hood's step. Assembly:
  1. Lower the board 15.1 mm north of its place and slide it south, so the six output shrouds pass through the front wall.
  2. Slide the north panel 13.4 mm south onto the two T1S shrouds. Bolt it to the floor and side walls with a gasket.
  3. Fit the lid, then screw the SurLok receptacles in.
- **SurLok plugs** point outward (west or east) or north. `scripts/check_surlok_clearance.py` checks all 16 combinations, including each plug's cable; all pass. The tightest is 0.9 mm: a return plug pointing west, to the board edge. `scripts/check_assembly.py` checks the fitting sequence.

## Consequences

- **Schematic and parts:** unchanged from DEC-021. The PCB holds enclosure version 7 (`CURRENT = "v7"` in `scripts/place_connectors.py`).
- **SurLok stud length** still decides the engagement: with the library's estimated 7.7 mm stud, about 4.5 mm of the REDCUBE's 5.6 mm thread. Amphenol publishes no stud length; get it, or a sample, before release.
- **Clamped laminate** (DEC-021) stands: the busbar bears on the terminal's spigot and on the board around it. GATE-HAR-02 measures the joint.
- **The pass-through limit (DEC-016) is unchanged**, at 40 A provisional.
- **Board-slide keep-out:** the board slides 15.1 mm over its standoffs, so a 15.1 mm strip on the south side of each mounting hole must stay free of parts on the underside.
- **Seals:** the lid gasket steps up and down at the front band (on the east and west walls) and around the T1S hood. The north panel adds one gasketed joint, against the floor and side walls.
- **Header pin tails on 2.6 mm** remain marginal (DEC-020).
- **Drawings and mockup:** version 7 on the [Enclosure options](../../subsystems/enclosure/) pages and in the [3D mockup](../../mockups/node60-enclosure.html), generated from the same geometry as the PCB placement. The other versions stay there as the record of the options.
