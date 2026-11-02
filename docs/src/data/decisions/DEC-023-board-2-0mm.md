---
id: DEC-023
title: Board 2.0 mm thick, the busbars resting on the REDCUBE spigots (enclosure version 10)
status: superseded
date: 2026-11-01
revision: B
page: subsystems/enclosure
supersedes: [DEC-022]
requirements: [REQ-NET-001, REQ-PWR-002, REQ-QUAL-001]
parts: [74660016R, SLPRATPSR, SLPRATPSB, AT13-2P-BM04, ATM13-2P-BM04]
gates: [GATE-HAR-01, GATE-HAR-02, GATE-THM-02]
rejected:
  - option: Keep the 2.6 mm board of DEC-020 to DEC-022 (enclosure version 7)
    reason: JLCPCB builds 6 and 8 layers only up to 2.0 mm, so 2.6 mm leaves PCBWay alone; its prototype price was about 2.5 times JLCPCB's for the same stackup (instant quotes, 2026-11-01). The header pin tails were also marginal on 2.6 mm.
---

## Context

DEC-020 made the board 2.6 mm thick so the SMT REDCUBE 74660016R's 2.6 mm spigot ends flush with the face the busbar sits on, and DEC-021 and DEC-022 kept it. Two things count against 2.6 mm:

- **Fab houses.** On 2026-11-01 the user priced five 250 × 160 mm prototypes, 6 layers, 1 oz outer and 2 oz inner copper, S1000-2M (Tg 170), ENIG, with filled vias for the BGA:
  - **JLCPCB, 2.0 mm:** about $290. JLCPCB builds 6 and 8 layers only up to 2.0 mm (2.5 mm and up is for 12 layers or more).
  - **PCBWay, 2.6 mm:** about $745.
- **Header pin tails.** The AT13 and ATM13 tails (3.1 ± 0.4 mm and 3.05 mm) came through only 0.1 to 0.5 mm on 2.6 mm (DEC-020).

Enclosure version 10 is version 7 on a 2.0 mm board. The user chose it on 2026-11-01.

## Decision

- **The PCB is 2.0 mm thick.** Everything else is DEC-022's (enclosure version 7): outline 250 × 160 mm, component side up, 5 mm off the floor, the connector positions, the busbars, the lid, the removable north panel and the plug directions.
- **The busbars rest on the REDCUBE spigots.** The 74660016R's Ø9.0 spigot is 2.6 mm long, so it stands 0.6 mm proud of the top face. Each busbar bears on its two spigots, 0.6 mm above the board, and the SurLok stud clamps it there. The busbar top, the receptacles, the low lid and the stud engagement stay where version 7 has them.
- **The raised sections drop 0.6 mm.** The headers stand on a board 0.6 mm thinner, so the front band and the T1S hood are a 10.5 mm step above the low lid, 43.5 mm overall (version 7: 11.1 mm and 44.1 mm). They stay 1 mm above the tallest header.
- `scripts/place_connectors.py` sets `CURRENT = "v10"`, and the PCB is placed from it at 2.0 mm. `scripts/check_surlok_clearance.py` passes all 16 plug combinations (tightest 0.9 mm, as version 7), and `scripts/check_assembly.py` fits the board with the removable north panel.

## Consequences

- **No laminate in the joint.** The receptacle clamps the busbar onto the spigot, and the load stays in the REDCUBE. DEC-021's clamped-laminate concern goes away. Keep other nets' copper and solder mask from under the busbars, since the bars no longer rest on the board.
- **Header pin tails** come through 0.7 to 1.5 mm, which settles DEC-020's marginal solder joints. Check the longest tail against the workmanship class's protrusion limit on the first assembled sample (GATE-HAR-01). The #4-20 header screws are 0.6 mm shorter.
- **Current capacity is unchanged:** it comes from the copper, not the core. Vias are 23 % shorter, so heat moves between layers slightly better.
- **Open: Würth's approval.** The 74660016R data sheet (rev. 001.001) gives the Ø9.3 hole and the 2.6 mm spigot but no board thickness. Confirm with Würth that the spigot may stand 0.6 mm proud of a 2.0 mm board, with the busbar clamped on it. Blocks board release, not the layout. GATE-HAR-02 measures the joint.
- **Stackup and fab house** are still open; 2.0 mm keeps both JLCPCB and PCBWay available.
- **SurLok stud length** still decides the engagement (DEC-022).
- **Drawings and mockup:** version 10 on the [Enclosure options](../../subsystems/enclosure/) pages and in the [3D mockup](../../mockups/node60-enclosure.html). The other versions stay there as the record of the options.

## Correction (2026-11-02): SurLok receptacle geometry

The heights above came from the SurLok figures in use on 2026-11-01: the DropOut library's estimated 7.7 mm stud, and the catalogue's B − A − C (19.2 mm) taken as the receptacle's seat-to-panel depth. Amphenol's SLPRATPSB customer drawing C10-730187 rev. F and its STEP, found on 2026-11-02, show the stud is 9.95 mm beyond the seat and the panel face is 9.25 mm above it; 19.2 mm is the panel face to the stud tip. With the corrected figures, version 10 (this decision's design) changes as follows; the plan, the plug, cable and assembly checks, and the decision itself don't:

- **Stud engagement:** the stud takes the REDCUBE's whole 5.6 mm thread (was about 4.5 mm), which settles the open stud-length point above. It comes out 1.2 mm below the REDCUBE, so the board sits 6.17 mm off the floor instead of 5.
- **Low lid:** 8.8 mm lower, 24.2 mm high outside. Parts under it get 9.0 mm above the board instead of 19.0; the tallest parts there haven't been checked against this yet. The lid's M4 bosses end 1.25 mm above the busbar.
- **Raised sections:** they stand 1.17 mm higher with the board, 44.66 mm overall, 20.5 mm above the low lid.

See [Power receptacles: RADLOK vs SurLok Plus](../../subsystems/enclosure/receptacles/).
