---
id: DEC-022
title: Press-fit REDCUBE terminals with the busbars on the blocks, and a flat lid with receptacle seats (enclosure version 4)
status: accepted
date: 2026-10-31
revision: B
page: subsystems/enclosure
supersedes: [DEC-021]
requirements: [REQ-NET-001, REQ-PWR-002, REQ-QUAL-001]
parts: ["786202106", 74660016R, SLPRATPSR, SLPRATPSB, AT13-2P-BM04, ATM13-2P-BM04]
gates: [GATE-HAR-01, GATE-HAR-02, GATE-THM-02, GATE-BOM-01]
rejected:
  - option: Enclosure version 2, SMT REDCUBE 74660016R under the board and a lid with a raised T (DEC-021)
    reason: The raised T puts an 11.1 mm step in the lid, so the lid gasket runs down and up the step's vertical faces. The user chose a flat lid to simplify the mechanical design and to seal on one level.
  - option: Enclosure version 7, a raised front band and a separate T1S hood
    reason: The same stepped lid seal as version 2, in two places.
  - option: A fully flat lid without seats, using a thicker busbar to lift the receptacles
    reason: The receptacles would need to rise 2.6 mm. A 3/16" bar leaves about 2.9 mm of the SurLok stud in the terminal's thread and a 1/4" bar about 1.4 mm (with the library's estimated 7.7 mm stud), too little for the 3 N·m joint.
  - option: Two boards, the T1S pair on a microcontroller board under the main board (enclosure version 8)
    reason: The user did not like its assembly (the main board slides in high and drops onto a mezzanine, and the output cutouts grow taller).
  - option: A horizontal parting line through the connector cutouts
    reason: Every header's panel seal would cross the joint, a likely leak path for IP67.
---

## Context

DEC-021 put the board component side up with SMT REDCUBE terminals underneath and the busbars on the board, under a lid with a raised T. The SurLok receptacles fix the height of the lid where they sit (their contact face is 19.2 mm below their panel face), and the output and T1S headers stand about 28 mm above the board. With the busbar on the board, the receptacles sit low, so the lid has to step up over the headers.

The enclosure options kept as candidates on 2026-10-30 included press-fit REDCUBE 786202106 terminals. Their 10.5 mm block lifts the busbar and so the receptacles nearly to the height the headers need. On 2026-10-31 the user had version 4 (version 2's layout with press-fit terminals) remodelled with a flat lid, decided the lid will be machined from solid aluminium, and chose it: a flat lid simplifies the mechanical design, and the lid seals on one level instead of on the vertical faces of a step.

## Decision

- **Power terminals: four Würth REDCUBE PRESS-FIT 786202106** (WP-PFIFUA, M6 blind thread 6.0 mm deep, 10 × 10 × 10.5 mm block, 16 press-fit pins, brass, tin-plated, 180 A max at 20 °C, 3.9 N·m max, for boards 1.6–2.7 mm thick, automotive approval, −55 to +150 °C; data sheet rev. 001.003). They replace the SMT 74660016R of DEC-016 on the same nets: J901 and J910 on VBAT_IN, J902 and J911 on GND. They sit on the top side (F.Cu). Library: `DropOut_Connector:786202106`.
- **Busbars on the blocks:** the 1/8" × 1" C110 copper bars of DEC-021 now rest on the terminal blocks, 10.5 mm above the board. Each SurLok receptacle's contact face lands on its bar, and its stud passes through the bar into the block's blind thread.
- **Board:** component side up, 2.6 mm thick (within the press-fit range), 250 × 160 mm, **5 mm off the floor**. Only the press-fit pins (3 mm) hang below it.
- **Positions:** as DEC-021 left them. Battery J910/J901 are 57.5 mm either side of the centre line, 50 mm from the front edge. Return J911/J902 are 78.7 mm either side, 115 mm from the front edge. T1S J903/J912 are in the middle of the north wall, 40 mm apart. The six outputs are on the front wall at a 40 mm pitch.
- **Lid: flat**, machined from solid aluminium, 4 mm thick, 3 mm above the tallest header (the T1S ATM13s) inside:
  - **Receptacle seats:** a 31 mm square pocket 2.6 mm deep at each receptacle, so its panel face sits where the receptacle needs it (19.2 mm above the bar). The lid is thickened 2.6 mm underneath each seat so it stays 4 mm thick there.
  - **Screw bosses:** an Ø8 × 4 mm boss under each of a receptacle's four M4 holes, for 8 mm of thread.
- **Walls and floor:** 3 mm, machined from solid aluminium. Outside, 257 × 167 × 46.1 mm.
- **Removable north panel:** the board has headers on the north and south walls, so it cannot go into one-piece walls. The base is the floor and the front, east and west walls; the north wall is a separate panel. Assembly:
  1. Lower the board 15.1 mm north of its place and slide it south, so the six output shrouds pass through the front wall.
  2. Slide the north panel 13.4 mm south onto the two T1S shrouds and bolt it to the floor and side walls with a gasket.
  3. Fit the lid, then screw the SurLok receptacles in through their seats.
- **SurLok plugs** point outward (west or east) or north. `scripts/check_surlok_clearance.py` checks all 16 combinations, including each plug's cable; all pass, the tightest at 0.2 mm (a return plug pointing west, to the board edge). `scripts/check_assembly.py` checks the fitting sequence.

## Consequences

- **Schematic:** J901, J902, J910 and J911 change from 74660016R to 786202106. The symbol is the same one-pin terminal, so no net changes. The PCB holds enclosure version 4 (`CURRENT = "v4"` in `scripts/place_connectors.py`).
- **Press-fit assembly:** the blocks are pressed in in one movement, with no soldering or rework after insertion, so after the board's other parts are soldered. Keep other components 4 mm away and each block 3 mm from the board edge; the holes need the plating and diameter Würth specifies.
- **The joint is metal to metal:** the busbar bears on the terminal block, not on the board, so no laminate is clamped in the joint (an open point of DEC-021).
- **Current:** at 180 A per terminal, the REDCUBE no longer limits the pass-through (the 74660016R was 85 A). The SurLok Plus 5.7 mm receptacle's 100–120 A class still does, so the 40 A provisional downstream limit of DEC-016 stands until GATE-HAR-02.
- **SurLok stud length** still decides the engagement: with the library's estimated 7.7 mm stud, 4.5 mm of the block's 6.0 mm thread. Amphenol publishes no stud length; get it, or a sample, before release.
- **Room under the busbars:** parts lower than about 9 mm can sit under the bars, at least 4 mm from the blocks.
- **Board-slide keep-out:** the board slides 15.1 mm over its standoffs, so a 15.1 mm strip on the south side of each mounting hole must stay free of parts on the underside.
- **Board thickness is free again:** 2.6 mm was chosen so the SMT terminal's spigot ended flush (DEC-020). The press-fit works from 1.6 to 2.7 mm, and a thinner board would leave the AT13 and ATM13 pin tails more protrusion. Open: choose with the stackup and fab house.
- **Seals:** the lid gasket runs on one level all round. The north panel adds one gasketed joint, against the floor and side walls, with two corners where the lid gasket crosses it.
- **Supply:** 786202106 was not found at DigiKey, Mouser or Newark on 2026-10-26 (bulk packaging only). GATE-BOM-01.
- **Drawings and mockup:** version 4 on the [Enclosure options](../../subsystems/enclosure/) pages and in the [3D mockup](../../mockups/node60-enclosure.html), generated from the same geometry as the PCB placement. The other versions stay there as the record of the options.
