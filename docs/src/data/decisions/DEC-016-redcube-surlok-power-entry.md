---
id: DEC-016
title: Würth REDCUBE 74660016R power terminals with Amphenol SurLok Plus receptacles and a pass-through feed
status: accepted
date: 2026-10-28
revision: B
page: subsystems/harness
requirements: [REQ-NET-001, REQ-PWR-002]
parts: [74660016R, "74660016", SLPRATPSR, SLPRATPSB, Busbar_Cu_19.05x3.175mm_L125.05mm_2xD6.5mm_P106mm]
gates: [GATE-PWR-01, GATE-THM-02, GATE-HAR-02, GATE-BOM-01]
rejected:
  - option: "Rev. A: J910 tied to J901 on the board, in parallel with the busbar, all four battery-side pads on one net VBAT_IN"
    reason: "From DEC-021 on the busbar rests on the REDCUBE spigots above the top face and the board has no copper between J910 and J901, so the bar is the only join; with one net, KiCad reported J901 unconnected, and a KiCad net tie between two pads of one net joins nothing. Changed in rev. B (user, 2026-11-02, placement decision D02): J901 gets its own net, and the bar is a schematic part joining the two nets."
  - option: Metri-Pack 480/630 class sealed connector or a dual feed (Rev A harness plan)
    reason: The user chose threaded power terminals with SurLok Plus receptacles on 2026-10-28, so the node can also pass battery power through to a downstream node.
  - option: Würth 74660016 (bulk)
    reason: The same terminal and footprint as 74660016R, in bulk packaging, and not listed at DigiKey, Mouser or Newark on 2026-10-28. 74660016R is the tape-and-reel version for machine assembly. Kept as the bulk alternate.
    outcome: alternative
---

## Context

Rev A planned the battery input as "Metri-Pack 480/630 class or dual feed" and the return as a matched 60 A conductor, without choosing parts. The schematic had two placeholders (J901 battery input, J902 power return). Every output's load current returns through the node (DEC-013), so both paths carry up to 60 A.

On 2026-10-28 the user decided the power entry, and added a pass-through: the node's power terminals also feed a second, lower-current power distribution node downstream.

## Decision

**Four Würth REDCUBE SMT 74660016R terminals on the board: two on the battery input, two on the power return** (J910 on VBAT_IN and J901 on VBAT_IN_DOWNSTREAM, joined by the busbar BB901; J902 and J911 on GND). Until rev. B (2026-11-02) J901 and J910 were both on VBAT_IN.

- **74660016R:** WP-SMRT REDCUBE SMT, reverse mounted, M6 internal through thread, brass, tin-plated, 85 A max at 20 °C ("operating current depends on PCB, cable lug and cross section of the cable"), 3.9 N·m max tightening torque, −55 to +150 °C, reflow with a Ø9.3 mm non-plated hole for the spigot (data sheet rev. 001.001). Tape and reel. Library: `DropOut_Connector:74660016R`.
- **Amphenol SurLok Plus receptacles screw into them:** **SLPRATPSR** (red) on the two battery terminals, **SLPRATPSB** (black) on the two return terminals. Decoded from Amphenol's SurLok Plus catalogue (IC-10): receptacle without keyway, 5.7 mm RADSOK contact (120 A class), threaded termination, flange panel mount, IP67 sealed, red or black. The 5.7 mm size is rated −40 to +125 °C and IP67/IP6K9K mated, and its threaded termination takes an M6 nut at 3 ± 0.1 N·m, inside the REDCUBE's 3.9 N·m limit.
- **Both sides of the case:** one battery/return pair of receptacles on each side of the enclosure. A busbar inside the case joins the two battery terminals, and another joins the two return terminals.
  - One pair feeds this node from the source: the receptacles on J910 and J911.
  - The other pair feeds a downstream power distribution node with lower current: the receptacles on J901 and J902.
- **The battery busbar is a board part (rev. B, user, 2026-11-02, placement decision D02):** BB901, `DropOut_Busbar:Busbar_Cu_19.05x3.175mm_L125.05mm_2xD6.5mm_P106mm`, is on the schematic (p9) as a two-pin net tie between J910's VBAT_IN and J901's VBAT_IN_DOWNSTREAM, with tie pads in the two terminals' pad 1 rings on the board. It is on the BOM: cut from 1/8" × 3/4" C110 flat bar (DEC-025) and drilled in house, fitted by hand at assembly. The return busbar (BB902) stays off the schematic and the BOM: the GND plane already joins J911 and J902, and the placement script draws the bar as a board-only footprint.

## Consequences

- **Pass-through current is not protected by this node.** The downstream feed leaves from the raw battery side, before the LM74910H ideal diode and breaker (DEC-001) and the INA228 shunt (DEC-002). Node60's reverse-battery protection, 75 A breaker and total-current telemetry cover only its own load. The downstream node needs its own protection, and the source fuse and cable must be sized for Node60 plus the downstream node.
- **Downstream current limit: 40 A, provisional** (user, 2026-10-28; the downstream node needs up to 60 A, and the user accepted a lower limit if needed).
  - At 60 A downstream, the upstream receptacle and terminal would carry 120 A: the top of the SurLok Plus 5.7 mm "100 to 120 A" class, with no derating curve for +125 °C in the catalogue, and above one REDCUBE's 85 A (max at 20 °C). The 8.0 mm SurLok size takes an M8 nut, not the REDCUBE's M6 thread.
  - At 40 A the upstream total is 100 A, about 83 % of the SurLok class rating.
  - **The busbars carry the pass-through.** On the battery side BB901 is the only join (rev. B): there is no board copper between J910 and J901, so the whole downstream current flows in the bar, and Node60's own load current leaves J910 through the board. On the return side the GND plane still joins J911 and J902 in parallel with the bar; GATE-HAR-02 measures that split. Until rev. B both pairs were meant to be tied on the board as well.
  - GATE-HAR-02 confirms 40 A from measured temperature rise at +125 °C ambient, or raises the limit toward 60 A.
- **REQ-NET-001 changes:** the node still connects with four conductors (T1S pair, battery, ground), and the power terminals may additionally pass battery and ground through to one downstream node.
- **Sealing is not decided yet** (user, 2026-10-28). The SurLok Plus receptacles are rated IP67 mated with a flange panel mount; the enclosure seal and the unmated state still need a decision.
- **Mechanical:** each receptacle's M6 stud screws into a board-mounted terminal, so the board is tied to the case wall at four points. The board outline, the terminal positions and the enclosure tolerances are set together; hold the terminal while tightening (Würth).
- **Qualification:** neither terminal family lists AEC-Q200 (Node60's grade rule applies to active parts; REQ-QUAL-001). Temperature rise and vibration are covered by GATE-HAR-02 and GATE-THM-02.
- **Supply:** 74660016R is listed only at Mouser (710-74660016R, no stock figure on 2026-10-28). SLPRATPSR and SLPRATPSB are stocked at DigiKey, Mouser and Newark. GATE-BOM-01.
- **Not board parts:** the SurLok receptacles, their mating plugs, the return busbar and the cables are enclosure and harness parts. The four REDCUBE terminals and, since rev. B, the battery busbar BB901 are on the schematic.
