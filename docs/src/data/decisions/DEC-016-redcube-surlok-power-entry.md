---
id: DEC-016
title: Würth REDCUBE 74660016R power terminals with Amphenol SurLok Plus receptacles and a pass-through feed
status: accepted
date: 2026-10-28
revision: C
page: subsystems/harness
requirements: [REQ-NET-001, REQ-PWR-002]
parts: [74660016R, "74660016", SLPRATPSR, SLPRATPSB, Busbar_Cu_19.05x3.175mm_L125.05mm_2xD6.5mm_P106mm, Busbar_Cu_19.05x3.175mm_L176.05mm_2xD6.5mm_P157mm]
gates: [GATE-PWR-01, GATE-THM-02, GATE-HAR-02, GATE-BOM-01]
rejected:
  - option: "Rev. B: J901 on its own net VBAT_IN_DOWNSTREAM, the busbar the only join between J910 and J901, J910 the source and J901 the downstream feed"
    reason: "The user cannot control which terminal pair a harness lands on, so either must work as the source (user, 2026-11-04). Changed in rev. C: both terminals on VBAT_IN, the power entry mirrored about the two terminals' midpoint and fed from both through board copper (placement decision D20 A), which also joins J901 to the net on the board."
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

**Four Würth REDCUBE SMT 74660016R terminals on the board: two on the battery input, two on the power return** (J910 and J901 on VBAT_IN, joined by the busbar BB901 and, since rev. C, by board copper through the mirrored power entry; J902 and J911 on GND). In rev. B (2026-11-02 to 2026-11-04) J901 had its own net, VBAT_IN_DOWNSTREAM.

- **74660016R:** WP-SMRT REDCUBE SMT, reverse mounted, M6 internal through thread, brass, tin-plated, 85 A max at 20 °C ("operating current depends on PCB, cable lug and cross section of the cable"), 3.9 N·m max tightening torque, −55 to +150 °C, reflow with a Ø9.3 mm non-plated hole for the spigot (data sheet rev. 001.001). Tape and reel. Library: `DropOut_Connector:74660016R`.
- **Amphenol SurLok Plus receptacles screw into them:** **SLPRATPSR** (red) on the two battery terminals, **SLPRATPSB** (black) on the two return terminals. Decoded from Amphenol's SurLok Plus catalogue (IC-10): receptacle without keyway, 5.7 mm RADSOK contact (120 A class), threaded termination, flange panel mount, IP67 sealed, red or black. The 5.7 mm size is rated −40 to +125 °C and IP67/IP6K9K mated, and its threaded termination takes an M6 nut at 3 ± 0.1 N·m, inside the REDCUBE's 3.9 N·m limit.
- **Both sides of the case:** one battery/return pair of receptacles on each side of the enclosure. A busbar inside the case joins the two battery terminals, and another joins the two return terminals.
  - **Either pair may take the source (rev. C, user, 2026-11-04):** the harness decides which, and the node works the same either way. The other pair feeds a downstream power distribution node with lower current.
  - The power entry (ideal-diode FETs, shunt, disconnect FETs) is mirrored about the midpoint between J910 and J901, so each battery terminal feeds its own ideal-diode FET through the same copper (placement decision D20 A).
- **Both busbars are board parts (rev. B, user, 2026-11-02, placement decision D02):** BB901, `DropOut_Busbar:Busbar_Cu_19.05x3.175mm_L125.05mm_2xD6.5mm_P106mm`, is on the schematic (p9) as a two-pin net tie with both pins on VBAT_IN since rev. C (J910's and J901's), with tie pads in the two terminals' pad 1 rings on the board. It is on the BOM: cut from 1/8" × 3/4" C110 flat bar (DEC-025) and drilled in house, fitted by hand at assembly. The return busbar BB902, `DropOut_Busbar:Busbar_Cu_19.05x3.175mm_L176.05mm_2xD6.5mm_P157mm`, is a schematic and BOM part the same way, for consistency (user, 2026-11-02), with both pins on GND: the GND plane joins J911 and J902 as well.

## Consequences

- **Pass-through current is not protected by this node.** The downstream feed leaves from the raw battery side, before the LM74910H ideal diode and breaker (DEC-001) and the INA228 shunt (DEC-002). Node60's reverse-battery protection, 75 A breaker and total-current telemetry cover only its own load. The downstream node needs its own protection, and the source fuse and cable must be sized for Node60 plus the downstream node.
- **Downstream current limit: 40 A, provisional** (user, 2026-10-28; the downstream node needs up to 60 A, and the user accepted a lower limit if needed).
  - At 60 A downstream, the upstream receptacle and terminal would carry 120 A: the top of the SurLok Plus 5.7 mm "100 to 120 A" class, with no derating curve for +125 °C in the catalogue, and above one REDCUBE's 85 A (max at 20 °C). The 8.0 mm SurLok size takes an M8 nut, not the REDCUBE's M6 thread.
  - At 40 A the upstream total is 100 A, about 83 % of the SurLok class rating.
  - **The busbars carry the pass-through.** On the battery side the board also joins J910 and J901 since rev. C, but only through the F.Cu pour under the bar: 4.7 mΩ terminal to terminal, measured from the copper (`copper_r.py`, 85 °C), against about 0.04 mΩ for the bar, so the bar carries about 99 % of the pass-through. Node60's own load current enters the board at both terminals and splits about evenly between the two ideal-diode FETs, so the bar carries the pass-through plus about half the node's current at most. The terminal on the source side still carries the node's current plus the pass-through, whichever terminal it is; the 40 A limit is unchanged. In rev. B the bar was the only join. On the return side the GND plane still joins J911 and J902 in parallel with the bar; GATE-HAR-02 measures that split. Until rev. B both pairs were meant to be tied on the board as well.
  - GATE-HAR-02 confirms 40 A from measured temperature rise at +125 °C ambient, or raises the limit toward 60 A.
- **REQ-NET-001 changes:** the node still connects with four conductors (T1S pair, battery, ground), and the power terminals may additionally pass battery and ground through to one downstream node.
- **Sealing is not decided yet** (user, 2026-10-28). The SurLok Plus receptacles are rated IP67 mated with a flange panel mount; the enclosure seal and the unmated state still need a decision.
- **Mechanical:** each receptacle's M6 stud screws into a board-mounted terminal, so the board is tied to the case wall at four points. The board outline, the terminal positions and the enclosure tolerances are set together; hold the terminal while tightening (Würth).
- **Qualification:** neither terminal family lists AEC-Q200 (Node60's grade rule applies to active parts; REQ-QUAL-001). Temperature rise and vibration are covered by GATE-HAR-02 and GATE-THM-02.
- **Supply:** 74660016R is listed only at Mouser (710-74660016R, no stock figure on 2026-10-28). SLPRATPSR and SLPRATPSB are stocked at DigiKey, Mouser and Newark. GATE-BOM-01.
- **Not board parts:** the SurLok receptacles, their mating plugs and the cables are enclosure and harness parts. The four REDCUBE terminals and, since rev. B, both busbars (BB901, BB902) are on the schematic.
