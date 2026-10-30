---
id: DEC-020
title: Board mounted component side down under the lid, 2.6 mm thick, connectors on fixed enclosure faces
status: accepted
date: 2026-10-30
revision: B
page: subsystems/harness
requirements: [REQ-NET-001, REQ-PWR-002, REQ-QUAL-001]
parts: [74660016R, SLPRATPSR, SLPRATPSB, AT13-2P-BM04, ATM13-2P-BM04]
gates: [GATE-HAR-01, GATE-HAR-02, GATE-THM-02]
rejected:
  - option: Component side up, REDCUBE 74660016R on the back face
    reason: The AT13 headers are 27.4 mm tall on the component side, so the lid sits at least about 30 mm above the board. The SurLok receptacle's contact face is a fixed 19.2 mm behind its panel face, so its stud cannot reach a terminal under the board without spacers or a busbar stack.
  - option: Würth REDCUBE PRESS-FIT 786202106 (180 A, M6 blind thread)
    reason: Compared in the enclosure mockup on 2026-10-30. It raises the current limit (180 A against 85 A), but none was found at DigiKey, Mouser or Newark (2026-10-26), and it needs a 4 mm component keep-out. The user kept the 74660016R.
    outcome: alternative
---

## Context

DEC-016 chose four REDCUBE 74660016R terminals with SurLok Plus receptacles screwed into them, and said the board outline, terminal positions and enclosure are set together. Connector placement on the PCB started on 2026-10-30 from the user's enclosure sketch: the six outputs on the front face, J903 on the right face, J912 on the left face, and the four power receptacles in the lid.

The 74660016R is a reverse-mount terminal: its body sits on one face and its M6 through thread opens through a Ø9.3 hole on the other face. The SurLok Plus 5.7 mm receptacle's contact face is 19.2 mm behind its panel face (catalog: B − A − C = 36.7 − 16.5 − 1.0 mm). With the component side facing the lid, the AT13 headers (27.4 mm tall) hold the lid too far from the board for the receptacles to reach the terminals.

## Decision

**The board mounts with its component side (F.Cu) facing the enclosure floor and its back face under the lid. The PCB is 2.6 mm thick.** User's decisions, 2026-10-30.

- **Power terminals:** the four REDCUBE 74660016R stay (DEC-016) and go on the component side. Their threads open through the board toward the lid, and each SurLok receptacle in the lid screws in from above. The receptacle's contact face lands on the board's back face, so the lid's outer face is about 19.2 mm above the board.
- **Connector faces (enclosure seen from outside):**
  - Front: J904–J909 (OUT1–OUT6), J904 on the left.
  - Right: J903, T1S upstream.
  - Left: J912, T1S downstream.
  - Lid: the four receptacles sit on a grid symmetric about the board's centre line. Battery J910 and J901 are 48 mm either side of it, 65 mm from the front edge. Return J911 and J902 are 75 mm either side, 125 mm from the front edge. The user's sketch set the idea (return pair wide, battery pair close); the numbers come from the plug clearance below.
- **Headers hang below the board.** The AT13 and ATM13 headers are on the component side, so their mating axes are below the board (13.8 mm for the AT13). The enclosure floor sits under them.
- **KiCad view is mirrored.** KiCad's top view looks at the component side, which faces the floor, so left and right swap against the outside view: J903 is on the board's left edge and J912 on its right, and J904 is the rightmost output. `scripts/place_connectors.py` holds the positions as seen from above the lid and mirrors them.
- **SurLok plugs can leave west, north or east.** The SLPRATPS receptacles have no keyway, so the right-angle plug can face any way. The catalog plug envelope is 18 mm wide and 55.1 mm long, with its round head on the mating axis, so it reaches 46.1 mm ahead of the axis. `scripts/check_surlok_clearance.py` tries all 81 west/north/east combinations of the four plugs against each other and against every receptacle's 27 mm flange, with 3 mm clearance. A plug pointing west or east must also end inside the board outline, so it stays within the enclosure walls; a plug pointing north may overhang the back (user, 2026-10-30). All 81 pass; the tightest is 3.8 mm (the battery plugs pointing at each other), and the outward return plugs end 3.9 mm inside the board edge. The battery pair can't move closer than about 95 mm apart, or those plugs collide. Rerun it when a terminal moves.
- **Board edges** sit 0.5 mm behind each connector's flange face, so the flanges, not the board, meet the walls.
- **Outputs** are on a 40 mm pitch: 4.8 mm between the 35.2 mm flanges (user, 2026-10-30).
- **Outline:** 250 × 160 mm, provisional until the enclosure is chosen.

## Consequences

- **2.6 mm suits the REDCUBE.** The 74660016R's Ø9.0 spigot is 2.6 mm long, so it ends flush with the back face, where the SurLok contact face seats.
- **Header pin tails are marginal on 2.6 mm.** The AT13's tails are 3.1 ± 0.4 mm and the ATM13's 3.05 mm, so they protrude only about 0.1 to 0.5 mm. Confirm with Amphenol, or on the first assembled sample, that the solder joints meet the board's workmanship class. The #4-20 screws that hold each header go in from the solder side, so their length follows the board thickness.
- **Stackup:** the copper count, layer thicknesses and fab house are still open. The handbook's 2 oz outer copper for the high-current paths and 4-layer minimum still apply.
- **Assembly:** all SMT parts, the REDCUBEs included, stay on one side. The headers are through-hole.
- **Power-entry placement:** DEC-016 put one battery/return pair on each side of the case. The user's sketch puts all four receptacles in the lid, and this decision follows the sketch.
- **3D mockup:** the [enclosure mockup](../../mockups/node60-enclosure.html) shows this arrangement. It is built from the connector positions on the PCB.
