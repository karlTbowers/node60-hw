---
id: DEC-017
title: Second T1S connector for a bus pass-through, and a relay-switched OPEN Alliance termination
status: accepted
date: 2026-10-28
revision: A
page: subsystems/network
requirements: [REQ-NET-001, REQ-NET-004, REQ-QUAL-001]
parts: [ATM13-2P-BM04, G6KU-2F-Y-T1-TRS_DC3, G6KU-2F-Y-T1_DC3, G6KU-2F-Y-T1-TRS_DC5, G6KU-2F-Y-T1-TRS_DC12, DMC2710UVQ-7, DMC2400UVQ-7, CRCW120649R9FKEAHP, CRCW12061K50FKEA, AC0805FR-07100KL, CGA4J2X7R2A104K125AA]
gates: [GATE-NET-01, GATE-NET-02, GATE-HAR-01, GATE-MCU-01, GATE-BOM-01]
rejected:
  - option: Single 100 Ω resistor across the pair, fitted or not at assembly (R502 in the first schematic)
    reason: Not the OPEN Alliance end termination (split legs to a centre tap with 100 nF and 100 kΩ to ground), and it cannot be changed once the case is sealed.
  - option: Photorelays (for example Toward AB45S-Q at 5 Ω, AB47S-Q at 0.16 Ω)
    reason: The switch sits in series with a 50 Ω leg that must hold ±1 %. Low-capacitance photorelays add 5 Ω or more that drifts with temperature; low-resistance ones bring large off-state capacitance against the ~4 pF left in the node's capacitance budget. They also drop to their unpowered state when the node sleeps.
  - option: Automotive analog switches (74LVC1G66-Q100, 74HC4066-Q100, TS5A3166-Q1, TMUX6612-Q1)
    reason: Same resistance-versus-capacitance trade-off (10–95 Ω at 3.5–6.5 pF, or 0.9–1.4 Ω at 19–27 pF off), the ±1 V bus swing around ground forward-biases single-supply switches, and only the 36 V TMUX6612 comes near surviving a bus wire shorted to battery.
  - option: Non-latching relay or any switch that needs power to hold its state
    reason: Node60 powers down when parked. The termination must keep its state while asleep, or the wake-up pulse arrives at an unterminated end (or at extra mid-bus terminations).
  - option: Terminator plug in the second connector
    reason: No board parts and no added capacitance, but a custom harness part, and a missing plug leaves the bus unterminated. The user chose a switch the controller can set.
  - option: G6KU-2F-Y (standard −40 to +85 °C model) and other small latching signal relays
    reason: Rated to +85 °C only; Node60 is Grade 1 (+125 °C).
  - option: G6KU-2F-Y-T1 with 5 V or 12 V coil
    reason: Node60 has no 5 V rail (the 5 V coil needs 3.75 V to operate); the 12 V coil would need its own regulator to ride through cold crank and jump start.
    outcome: alternative
---

## Context

The user wants Node60 to pass the 10BASE-T1S bus through to a downstream node, as DEC-016 does for power, and to work either in the middle of the bus or at its end. A 10BASE-T1S mixing segment is terminated at its two ends only. Rev A planned a termination that is "populated or enabled only at a physical segment endpoint" (REQ-NET-004); the first schematic had a single 100 Ω resistor, not fitted (R502).

OPEN Alliance's 10BASE-T1S Implementation Specification (V1.0, §5.3 and §6.4.1) and Microchip's LAN86xx bus interface network application note (AN1718 rev. D, April 2026) specify the termination as two legs from the lines to a centre tap, with 100 nF and 100 kΩ from the centre tap to ground:

| Node | Legs (R1, R2) | Source |
|---|---|---|
| End node (bus end) | 50 Ω ±1 %, ≥ 0.4 W each (Microchip: 49.9 Ω 1 %, 1 W, 1206) | OA §6.4.1, AN1718 Table 1-2 |
| Drop node (mid-bus) | 1.5 kΩ ±1 % (common-mode termination, optional) | OA §5.3, AN1718 Table 1-2 |
| Centre tap | 100 nF ≥ 50 V ‖ 100 kΩ to ground (Microchip: 100 nF 100 V 0805, 100 kΩ 0805) | OA, AN1718 |

## Decision

1. **Second T1S connector J912**, another Amphenol Sine ATM13-2P-BM04, wired in parallel with J903 on T1S_P/T1S_N. J903 faces upstream, J912 downstream; the bus runs through the node.
2. **OPEN Alliance split termination, switched by a latching relay.** A DPDT latching relay (K501) selects, per line, either the 49.9 Ω leg (end node) or the 1.5 kΩ leg (drop node) to the centre tap. The centre tap has 100 nF ‖ 100 kΩ to ground. With the relay's 100 mΩ max contact resistance, an end-node leg is 49.9–50.0 Ω, inside 50 Ω ±1 %. One leg value is always connected, so the line is never left without the common-mode termination.
3. **Relay: Omron G6KU-2F-Y-T1-TRS DC3** (user's choice, 2026-10-28): single-winding latching, DPDT, surface mount, high-temperature model rated −40 to +125 °C, 100 mΩ max contact resistance, rated for low-level loads (failure rate 10 µA at 10 mV), 10 ms minimum set/reset pulse, 3 V coil (46.6 mA, 64 Ω) run from 3V3_MAIN (must operate ≤ 75 % of rated, max 150 %). Datasheet: Omron G6K, revised 2026-03.
4. **Legs and centre tap:** R517/R519 Vishay CRCW120649R9FKEAHP (49.9 Ω 1 %, 0.75 W, 1206), R516/R518 CRCW12061K50FKEA (1.5 kΩ 1 %, 1206), C514 TDK CGA4J2X7R2A104K125AA (100 nF 100 V X7R 0805), R520 Yageo AC0805FR-07100KL (100 kΩ 0805). Schematic: SET (coil pin 1 +, pin 8 −) closes the 49.9 Ω legs (end node); RESET, the factory state, closes the 1.5 kΩ legs (drop node).
5. **Coil driver:** two Diodes DMC2710UVQ-7 complementary MOSFET pairs (20 V, AEC-Q101, SOT-563), each wired as a half-bridge from 3V3_MAIN with both gates on one MCU pin (Q501 on T1S_TERM_END, Q502 on T1S_TERM_DROP). 100 kΩ pull-downs hold both gates low through reset, so both coil ends sit at 3V3_MAIN and no current flows. Driving one pin high for ≥ 10 ms pulls its coil end to ground and switches the relay; the H-bridge body diodes clamp the coil when the pulse ends.
6. **MCU pins:** PTD0 (ball F3) and PTD1 (ball E3), plain GPIOs that were unused.

## Firmware

- The termination state (end or drop) is commissioned by the controller over T1S and stored in flash, alongside the PLCA node ID.
- At every cold boot, after the PHY is up, firmware drives the relay to the stored state with one 10 ms pulse: the relay may arrive from the factory in either position, and a hard shock could flip it.
- Firmware reports the stored termination state to the controller. The relay has no position feedback (both poles carry the bus), so the controller verifies the bus-wide configuration (exactly two ends terminated) during commissioning.

## Consequences

- **Wake-up keeps working while parked.** The relay holds its state without power, so the termination stays as commissioned while the node sleeps and the controller's wake-up pulse (OA Sleep/Wake-up v1.1 §8.3.1) sees a correctly terminated bus. A switch that needs power would not.
- **Capacitance budget:** the second connector, the trunk trace between J903 and J912, the relay's open contacts and the extra pads all count against the ~4 pF left after the PHY, choke and ESD (DEC-012). Omron publishes no open-contact capacitance; GATE-NET-02 measures the node's capacitance in both states.
- **Layout (Microchip AN1718 §2.0):** J903 and J912 side by side with the shortest possible trunk between them; ESD and termination in line on the pair at the connectors; stub to the PHY well under 10 cm; no ground pour around the line interface; no copper in any layer under the choke. The DC block sits on the connector side of the choke (DEC-012 rev. B).
- **Bus faults at an end node:**
  - One wire shorted to battery: DC flows only through a leg and the 100 kΩ (about 0.24 mA at 24 V); the 100 nF sees a charging transient.
  - Battery on one wire and ground on the other: the two 49.9 Ω legs are in series across the fault, about 0.24 A at 24 V and 2.9 W per leg, sustained. That is beyond any 1206 resistor's rating; a leg may fail open and leave the bus end unterminated. This applies to any end-terminated 10BASE-T1S node. Check the harness short-circuit requirement (as DEC-012 notes for the ESD diodes) and whether the termination must survive it.
- **GATE-MCU-01:** PTD0/PTD1 are new pin uses; both are plain GPIOs (checked against NXP's IOMUX table). The ball map is unchanged.
- **Supply:** G6KU-2F-Y-T1-TRS DC3 had no stock at DigiKey or Mouser on 2026-10-28 (the DC5 and DC12 versions are stocked). GATE-BOM-01.
- **Qualification:** the relay lists no AEC-Q200 qualification; the MOSFETs are AEC-Q101.
