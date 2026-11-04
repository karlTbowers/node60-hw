---
id: DEC-012
title: ACT1210E-241 common mode choke and VETH100A1DD1 ESD diodes on the T1S line
status: accepted
date: 2026-11-03
revision: C
page: subsystems/network
requirements: [REQ-NET-001, REQ-NET-004, REQ-QUAL-001]
parts: [ACT1210E-241-2P-TL00, ACT1210E-131-2P-TL00, DLW32MH241MX2L, VETH100A1DD1HG3-08, PESD1ETH10LS-QYL, PESD1ETH10L-QYL]
gates: [GATE-THM-02, GATE-BOM-01]
rejected:
  - option: "Rev. A layout order: connector → ESD → choke → DC block → PHY"
    reason: Microchip AN1718 rev. D (the LAN8670 data sheet's line-interface reference), OPEN Alliance's 10BASE-T1S Implementation Specification (Figure 4) and both Microchip LAN8670 evaluation boards (EVB-LAN8670-RMII rev. 4, EVB-LAN8670D-USB rev. 1) put the DC block on the connector side of the choke. Changed in rev. B (user, 2026-10-29).
  - option: "Rev. B: one ESD pair, at J903 only"
    outcome: replaced
    reason: "Since DEC-017 the trunk runs J912 ↔ J903 through the board (39 mm) and either connector may face the harness, so a discharge into J912 crossed about 35 mm of trace before reaching a clamp. Rev. C adds D503/D504 at J912 (placement decision D16-2 A, user, 2026-11-03)."
  - option: Murata DLW32MH201XK2L
    reason: Murata rates it for 100BASE-T1, not 10BASE-T1S. It is in the library, but not as a Node60 option.
  - option: TDK ACT1210L-201-2P / Nexperia PESD2ETH1G-T (MR-CANHUBK344 parts)
    reason: Specified for 100BASE-T1 and 1000BASE-T1, not 10BASE-T1S.
  - option: Nexperia PESD2CANFD24L-TR (FRDM-A-S32K344 / MR-CANHUBK344 CAN ESD)
    reason: Specified for CAN, CAN FD, FlexRay and SENT, at 10 pF. That breaks the T1S capacitance budget.
  - option: Coilcraft 1210ETH-244
    reason: Rated for 10BASE-T1S, but not stocked at DigiKey or Mouser on 2026-10-22.
  - option: ESD diodes on the Nexperia PESD1ETH10L(S)-Q as first choice
    reason: Best capacitance (0.4 pF) and standoff (75 V), but no distributor stock and a 365-day Mouser lead time on 2026-10-22.
    outcome: alternative
---

## Context

The T1S pair is Node60's only network connection and its only wake path (DEC-007). Node60 is a multidrop follower on a mixing segment (REQ-NET-004). The OPEN Alliance 10BASE-T1S Implementation Specification V1.0 defines the line interface, called the bus interface network:
- **Choke:** a common mode choke that meets the 10BASE-T1S CMC test specification.
- **DC blocking:** two 100 nF caps rated at least 50 V.
- **ESD:** an optional ESD element. An ESD element placed between the connector and the choke must meet the OPEN Alliance T1S ESD specification.

That spec also limits the node's **combined capacitive load to CMDI ≤ 25 pF** for 8 nodes on 25 m. The budget is 10 pF for the transceiver, 10 pF for the choke, and 5 pF for everything else: connector, ESD and PCB traces.

The CMC test spec V1.1 (Annex A) classes chokes by their parasitic capacitance: Class III is 7 to 10 pF, and Class IV is 7 pF or less. The implementation spec's worked example uses a 200 µH Class III choke. Microchip's LAN8670 data sheet gives no line-interface circuit and names no choke or ESD part.

## Decision

- **Common mode choke: TDK ACT1210E-241-2P-TL00, quantity 1.** It is rated for 10BASE-T1S, with 240 µH (+50/−20 %) at 100 kHz, 80 V, 70 mA, and 4.1 Ω max DCR. It is AEC-Q200, −40 to +125 °C, in a 3.2 × 2.5 mm package.
  - It matches the spec's 200 µH Class III example and has deep distributor stock.
  - **Alternate:** ACT1210E-131-2P-TL00, 130 µH. TDK says it is Class IV, so it gives more capacitance margin for longer segments or more than 8 nodes. It uses the same footprint.
  - **Second source:** Murata DLW32MH241MX2L. It has the same rated values, and Murata states CMC Class 3. It uses the same land pattern, but its pad numbering and footprint differ.
- **ESD: Vishay VETH100A1DD1HG3-08, quantity 4: one per line at each T1S connector, D501/D502 at J903 and D503/D504 at J912 (rev. C), between the connector and the choke.**
  - **Rating:** OPEN Alliance compliant for 10BASE-T1S, 100BASE-T1 and 1000BASE-T1, and AEC-Q101.
  - **Electrical:** 24 V working voltage, trigger above 100 V, and at most 2.0 pF per line (1.0 pF across the pair). It survives ±15 kV for 1000 discharges (ISO 10605, 150 pF / 330 Ω).
  - **Package:** DFN1006-2B with wettable flanks.
  - **Alternates:** Nexperia PESD1ETH10LS-QYL (DFN1006BD-2, side-wettable) and PESD1ETH10L-QYL (DFN1006-2). Both have 0.4 pF max and 75 V standoff.

**Capacitance check (rev. C, two ESD pairs):** at most 2.0 pF from the two ESD pairs across the line, plus at most 10 pF from a Class III choke and at most 8.5 pF from the LAN8670, is 20.5 pF of the 25 pF CMDI, leaving about 4.5 pF for the two connectors and the traces (3 pF against the spec's 10 / 10 / 5 pF split). Rev. B, with one pair, left about 4 pF of the 15 pF non-transceiver budget. Sources and the item-by-item sum are under Rev. C below.

**Observed 2026-10-22, not quotes:**

| Part | DigiKey $ @1 / @1k | DigiKey stock | Mouser |
|---|---|---|---|
| ACT1210E-241 | 1.89 / 1.12 | 42,488 | 0 in stock, 70-day lead |
| ACT1210E-131 | 1.92 / – | 494 | 9,516 in stock |
| VETH100A1DD1HG3-08 | 0.48 / – | 15,582 | 30,510 in stock, $0.13 @1k |
| PESD1ETH10LS-QYL | – | 0 | 0, 365-day lead, $0.165 @1k |

## Consequences

- **Layout order (rev. B, 2026-10-29):** connector → ESD diodes → termination (DEC-017) → 100 nF DC-block caps → choke → LAN8670, the order of Microchip AN1718 rev. D (Figure 1-3), OPEN Alliance's implementation spec (Figure 4) and Microchip's LAN8670 evaluation boards. AN1718 §2.0: place the choke and DC-block caps as close as possible to the connector, ESD and termination in line on the pair, no ground pour around the line interface, no copper in any layer under the choke. Keep each ESD pair right at its own connector's pins (rev. C): D501/D502 at J903, D503/D504 at J912. Keep the pair symmetric through the choke so mode conversion stays low.
- **Footprints:** all three chokes share a land pattern but have different pad numbering. Use the library footprint for the fitted part, and don't swap MPNs without swapping footprints. The ESD diode footprints differ between Vishay and Nexperia.
- **Open risk on the choke:** TDK publishes no CMC class for ACT1210E-241. Get TDK's OPEN Alliance test report, and confirm it is Class III or better, before BOM lock (GATE-BOM-01).
- **Open risk on the ESD diode:** the VETH100A1DD1's 24 V working voltage leaves no headroom over 24 V jump-start if a bus wire shorts to battery. If the harness short-to-battery requirement is above 24 V, switch to the 75 V Nexperia parts.
- **EMC validation** of the full line interface belongs to GATE-THM-02.
- **Library:** all seven parts are in dropout-kicad-library PR #14, including the rejected DLW32MH201XK2L. Node60 picks them up with the next library submodule update.

## Rev. C: an ESD pair at J912 too (2026-11-03)

Placement decision D16-2 A (user, 2026-11-03) added **D503/D504**, a second VETH100A1DD1HG3-08 pair at J912's pins, wired as D501/D502: pad 1 (A1) to GND, pad 2 (A2) to `T1S_P` (D503) or `T1S_N` (D504). The T1S trunk runs J912 ↔ J903 through the board (DEC-017), and either connector may face the harness; with one pair at J903, a discharge into J912 travelled about 35 mm of trace before it reached a clamp. The user's condition was that the extra ≤ 2 pF per line fits the node's capacitance budget.

**The limit.** OPEN Alliance's 10BASE-T1S Implementation Specification V1.0 (S21), Table 1: a node's combined capacitive load **CMDI ≤ 25 pF**, valid for a mixing segment of up to 8 nodes and 25 m, made of about 10 pF for the transceiver block, 10 pF for the choke and 5 pF for the rest (ECU connector, the ESD element, PCB traces); the split is a recommended target, and more nodes need a lower CMDI. Microchip AN1718 rev. D (S39) §2.0 also asks for the line-interface traces to keep the differential capacitance to 15 pF, citing IEEE 802.3cg-2019 clause 147.9.2, Table 147-4 (that standard was not read for this check). If that 15 pF covered the whole node, the PHY and a Class III choke alone (18.5 pF) would already exceed it, with or without ESD; the OPEN Alliance budget, which counts both, is the one this design follows. The budget is a line-to-line (differential) figure: the choke specification measures Cpara between the two windings, the LAN8670 data sheet gives CDIFF, and Vishay rates the diode both alone and as "two devices in series according to OPEN Alliance 10BASE-T1S", which is one pair across the line.

**The node's load, across the line, at data-sheet maxima:**

| Item | Across the line | Source |
|---|---|---|
| LAN8670 TRXP/TRXN | 8.5 pF max (6.5 min), 20 MHz, characterised | LAN8670/1/2 data sheet DS60001573K (S1), Table 7-19 |
| FL501 ACT1210E-241 | ≤ 10 pF if Class III; TDK publishes no class (open risk above) | OA CMC test specification V1.1 (S22), Table A-1 |
| D501/D502 and D503/D504 | 2 × 1.0 pF max (2 × 0.85 typ); each diode 2.0 pF max to GND, so 4.0 pF per line to GND | Vishay VETH100A1DD1 data sheet, doc. 86195 rev. 1.3 (S40): CD at VR = 0 V, 1 MHz |
| C511/C512 DC block | none: 100 nF in series with about 20 pF changes it by 0.02 % | |
| K501 open contacts | about 0.03 pF per open contact (estimate, not a rating) | Derived from Omron's G6K isolation curve (S41, p. 5: G6K-2G, about 75 dB at 10 MHz in 50 Ω, so the S21 magnitude ≈ 2π f C × 100 Ω); Omron publishes no capacitance |
| **Total of the parts** | **20.5 pF** (the relay adds about 0.02 pF) | |
| Left for J903, J912, the trunk and the PHY stub | about 4.5 pF of 25 pF (3 pF against the 10 / 10 / 5 split) | |

**Result: two pairs fit** the CMDI ≤ 25 pF budget with every part at its maximum, provided the choke is Class III or better (the existing open risk). The second pair takes 1.0 pF of the margin, so the connectors and traces now have about 4.5 pF instead of about 5.5 pF on the same basis. GATE-NET-02 measures the node's capacitance in both termination states. If it comes out tight, either alternative frees capacitance: ACT1210E-131 (Class IV, ≤ 7 pF, same footprint) gives back 3 pF; Nexperia PESD1ETH10L(S)-Q (0.4 pF max per diode, different footprint, no distributor stock on 2026-10-22) at both connectors gives back about 1.6 pF.
