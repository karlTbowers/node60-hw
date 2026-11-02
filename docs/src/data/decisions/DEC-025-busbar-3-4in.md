---
id: DEC-025
title: 1/8 × 3/4 in busbars (enclosure version 15)
status: accepted
date: 2026-11-01
revision: B
page: subsystems/enclosure
supersedes: [DEC-024]
requirements: [REQ-PWR-002, REQ-QUAL-001]
parts: [74660016R, SLPRATPSR, SLPRATPSB, Busbar_Cu_19.05x3.175mm_L125.05mm_2xD6.5mm_P106mm]
gates: [GATE-HAR-02, GATE-THM-02]
rejected:
  - option: Keep version 11's 1/8" × 1" busbars (DEC-024)
    reason: The 1" bars block 6.35 mm more of the top side along each bar, where the MCU and T1S decoupling caps have to sit, and the bars carry far more copper than the current needs.
  - option: 3/16" × 3/4" busbars (enclosure version 14)
    reason: The thicker bar lifts the receptacles 1.59 mm, so the SurLok stud engages only 5.19 of the REDCUBE's 5.6 mm thread, and Würth's minimum engagement is not known.
---

## Context

DEC-024 chose enclosure version 11: the compact 230 × 110 mm board on 2.0 mm, with DEC-021's 1/8" × 1" C110 busbars resting on the REDCUBE spigots 0.6 mm above the top face. Nothing fits under a bar, so each bar blocks a 25.4 mm strip of the top side, and the version 11 placement packed the MCU and T1S decoupling caps against the GND bar's edges and into the 3.6 mm gap between the two bars.

Version 14 tried 3/16" × 3/4" bars to free that area. It costs thread: the receptacles sit 1.59 mm higher on the thicker bar, and the SurLok's 9.95 mm stud then engages only 5.19 mm of the REDCUBE's 5.6 mm thread. On 2026-11-01 the user chose 1/8" × 3/4" instead, to get the board space back without leaving any of the REDCUBE's thread unused.

## Decision

- **The busbars are 1/8" × 3/4" C110 copper flat bar** (3.175 × 19.05 mm), cut to length and drilled in house: enclosure version 15, which is version 11 with the narrower bar.
- **Everything else is version 11's** (DEC-024): the 230 × 110 × 2.0 mm board and its connector plan, the receptacles, the lid, the removable north panel, and every height. The board sits 6.17 mm off the floor, and the enclosure is 237.7 × 117 mm outside, 24.2 mm tall at the low lid and 44.7 mm at the band and hood, with 9.0 mm under the low lid above the board.
- **Scripts:** `scripts/place_connectors.py` sets `CURRENT = "v15"`, and the PCB is placed from it. Its busbar footprints BB901 and BB902 and the `BUSBAR_<net>` rule areas follow the 19.05 mm bar. `scripts/check_surlok_clearance.py` passes all 16 plug combinations (tightest 2.0 mm, flange to flange), and `scripts/check_assembly.py` fits the board with the removable north panel, both as in version 11.

## Consequences

- **Top-side area:** each bar is 6.35 mm narrower, so each of its edges moves 3.2 mm in. The gap between the two bars grows from 3.6 to 9.95 mm, and the strip north of the GND bar grows by 3.2 mm. The parts are placed again for the narrower bars.
- **Whole thread engaged:** the SurLok stud passes through the REDCUBE's whole 5.6 mm thread, as in version 11. Version 14's question to Würth about minimum thread engagement falls away.
- **Less copper:** 60.5 mm² per bar against 80.6 mm² (−25 %). At 100 A that is about 1.7 A/mm², low for a bare bar, but check the bars' temperature rise when the current path is proved (GATE-HAR-02) and in the thermal test (GATE-THM-02).
- **Shorter bars:** each end still runs half a bar width past its hole, so each bar is 6.35 mm shorter. The cut list is on the version 15 page.
- **Lid bosses:** the receptacles and the Ø8 mm bosses under their M4 holes stay where they are, so on the narrower bar the bosses reach about 3.5 mm past each bar edge. They end 5.0 mm above the board there: clear of the decoupling caps, but the tallest top-side parts (J401, D201) must stay out from under them. In the placement D201 sits 2.4 mm clear of J910's boss. The relay K501, on top when this was decided, moved to the bottom the same day, under the T1S trunk.
- **Still open from DEC-024:** Würth's approval of the spigot standing 0.6 mm proud (blocks board release), the stackup and the fab house.
