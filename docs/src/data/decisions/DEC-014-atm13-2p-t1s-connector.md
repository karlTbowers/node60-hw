---
id: DEC-014
title: Amphenol SINE ATM13-2P-BM04 for the 10BASE-T1S connector
status: accepted
date: 2026-10-25
revision: A
page: subsystems/harness
requirements: [REQ-NET-001]
parts: [ATM13-2P-BM04, ATM13-2P-BM01, ATM13-2P-BM02, ATM13-2P-BM03]
gates: [GATE-THM-02, GATE-BOM-01]
rejected:
  - option: ATM13-2P-BM01 / BM02 (gold-plated contacts)
    reason: Same receptacle and footprint. The user chose the tin-plated, potted BM04 on 2026-10-25. Gold is the usual choice for low-current signal contacts, so it stays available as a drop-in.
    outcome: alternative
  - option: ATM13-2P-BM03 (tin, no potting in the reservoir)
    reason: Same receptacle and footprint, without the potted pin reservoir.
    outcome: alternative
---

## Context

Rev A's harness plan gives the T1S link its own **sealed two-way connector** carrying the twisted pair. It is one of the node's exactly four conductors (REQ-NET-001), and no part had been chosen for it. The schematic had a placeholder (J903). The output connectors are TE DEUTSCH DT13-2P (DEC-013); the power input and return connectors are still open.

The OPEN Alliance 10BASE-T1S Implementation Specification (S21, §5.4.3) says the ECU connector and the complete channel must meet the OPEN Alliance channel and connector RF requirements.

## Decision

**One Amphenol SINE ATM13-2P-BM04 per board, carrying the T1S pair** (user's decision 2026-10-25, replacing placeholder J903).

It is a BoardLock ATM series 2-pin right-angle PCB receptacle with a flange and flange seal. The tin-plated size 20 pins sit at 4.20 mm, the pin reservoir is potted, and it mates the ATM06-2S plug. It is fixed by 3× #4-20 thread-forming screws from the solder side.

**Ratings** (drawing ATM13-2P-BMXX rev. A2; BoardLock flyer):

| Parameter | Rating |
|---|---|
| Current per contact | 7.5 A |
| Voltage | 250 V |
| Temperature | −55 to +125 °C |
| Insulation resistance | 1000 MΩ |
| Dielectric withstanding | 1500 VAC |
| Ingress protection | IP67 mated |
| Durability | 100 mating cycles |
| Potted versions | rated for up to 5 psi |

It is not AEC qualified, like DT13-2P.

**Observed 2026-10-25 (not quotes):**
- DigiKey 889-3357-ND: $8.23 @1, $5.24 @600, 14 in stock.
- Mouser 654-ATM13-2P-BM04: $8.23 @1, $5.03 @1050, 120 in stock.

**Alternates:** ATM13-2P-BM01, BM02 and BM03 are the other plating and potting versions on the same footprint.

## Consequences

- **Pin 1 must be verified before release.** The drawing marks pin 1 only in its mounting-face view. The library footprint mirrors that to the component side; check it against the cavity marks on a sample, as for DT13-2P. The schematic assigns the pair to pins 1 and 2.
- **Mating set:** freeze the ATM06-2S plug, its size 20 sockets, wedgelock, seals and wire size with the harness. Match the socket plating to the receptacle: tin with tin, gold with gold. Don't mix them.
- **Contact plating:** T1S is a low-current signal. If dry-circuit contact reliability is a concern over the vehicle life, the gold BM02 is a drop-in: same potting, same footprint.
- **The ATM is not an OPEN Alliance-qualified T1S connector.** Check its effect on the channel (return loss and mode conversion of the connector and harness) as part of EMC validation (GATE-THM-02). Keep the pair symmetric and short from the connector to the ESD diodes and the choke (DEC-012).
- **Library:** all four versions are in dropout-kicad-library PR #26, footprint `DropOut_Connector_Amphenol:Amphenol_ATM13-2P-BMxx_1x02_P4.20mm_Horizontal`.
