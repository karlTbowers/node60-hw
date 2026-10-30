---
id: DEC-021
title: Board component side up, busbars under the SurLok receptacles, lid with a raised T, T1S on the north wall
status: accepted
date: 2026-10-30
revision: B
page: subsystems/enclosure
supersedes: [DEC-020]
requirements: [REQ-NET-001, REQ-PWR-002, REQ-QUAL-001]
parts: [74660016R, SLPRATPSR, SLPRATPSB, AT13-2P-BM04, ATM13-2P-BM04]
gates: [GATE-HAR-01, GATE-HAR-02, GATE-THM-02]
rejected:
  - option: Board component side down under the lid (DEC-020)
    reason: The user changed the mechanical design on 2026-10-30 to put busbars under the SurLok receptacles. With the board up, the busbars sit on its top face and the receptacles land on them.
  - option: 5 mm busbars
    reason: Every millimetre of busbar comes out of the SurLok stud's reach into the REDCUBE thread (5.6 mm long). With the library's estimated 7.7 mm stud, 5 mm would leave about 2.7 mm of engagement. The user asked for a thickness that works and can be bought.
  - option: Plugs pointing inward (toward the board's centre line)
    reason: The raised T's stem sits between the two low sections, so an inward plug would run into it. Plugs point outward or north.
---

## Context

DEC-020 mounted the board component side down so the SurLok receptacles in the lid could reach the REDCUBE terminals. On 2026-10-30 the user changed the mechanical design: board component side up again, a busbar on top of the board for each power pair, the T1S connectors in the middle of the north wall, and a lid stepped down so the receptacles sit on the busbars. The user suggested a lid shaped as a raised T with low sections beside it, reviewed the design in the 3D mockup and the dimensioned drawing, and accepted it the same day.

## Decision

- **Board component side up**, 2.6 mm thick (kept from DEC-020: the REDCUBE's 2.6 mm spigot ends flush with the top face). KiCad's top view is again the view from above.
- **Power terminals:** the four REDCUBE 74660016R move to the bottom side (B.Cu), their M6 threads opening up through the board.
- **Busbars:** one per power pair, on top of the board, cut to length and drilled in house from **1/8" × 1" C110 copper flat bar** (3.175 × 25.4 mm). That's 80.6 mm², about 1.2 A/mm² at the 100 A upstream total.
  - **Where they go:** VBAT_IN joins J910 and J901; GND joins J911 and J902. Each bar is 165.4 mm long with two Ø6.5 holes 140 mm apart.
  - **The joint:** each SurLok receptacle's contact face lands on its busbar, and its stud passes through the busbar into the REDCUBE below, clamping the bar onto the terminal's flush spigot.
  - **On the PCB:** components stay out from under the bars (outlines on User.Drawings).
  - **Metric alternative:** 25 × 3 mm bar.
- **Terminal positions:** one battery/return pair in each low section of the lid, 70 mm either side of the centre line. Battery J910/J901 are 45 mm from the front edge, return J911/J902 115 mm.
- **T1S:** J903 and J912 in the middle of the north wall, 45 mm apart, J903 on the left as seen from outside.
- **Lid: a raised T.** The low sections, where the receptacles' panel faces sit, are 22.4 mm above the board's top face (busbar plus the SurLok's 19.2 mm). The headers are up to 28.5 mm tall, so they sit under a raised T about 12 mm higher:
  - **Crossbar:** across the front, over the six AT13 outputs.
  - **Stem:** up the middle to the north wall, over the T1S pair.
- **SurLok plugs** point outward (west or east) or north. `scripts/check_surlok_clearance.py` checks all 16 combinations against each other, the flanges, the T and the board edge (east/west plugs stay inside the walls). All pass; the tightest is 8.9 mm.

## Consequences

- **SurLok stud length decides the busbar.** With the estimated 7.7 mm stud, about 4.5 mm reaches the REDCUBE's 5.6 mm thread. Amphenol publishes no stud length. Get it, or a sample, before release. Amphenol's own instructions bolt the stud through a busbar with a washer and an M6 nut instead.
- **Clamped laminate:** the busbar bears on the spigot face and on the board around it, so the joint clamps some FR-4. GATE-HAR-02 measures the joint's temperature rise and checks for loosening.
- **The pass-through limit (DEC-016) is unchanged**, at 40 A provisional. The busbars carry the pass-through between each pair.
- **Board area:** the two bars cover about 2 × 165 × 25 mm across the middle of the board, so no components can go under them.
- **Header pin tails on 2.6 mm** remain marginal (DEC-020).
- **Drawing and mockup:** the [Enclosure & mechanical](../../subsystems/enclosure/) page and the [3D mockup](../../mockups/node60-enclosure.html) are generated from the same geometry as the PCB placement.
