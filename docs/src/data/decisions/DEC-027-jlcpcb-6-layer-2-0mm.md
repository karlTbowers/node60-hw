---
id: DEC-027
title: 6-layer, 2.0 mm board on JLCPCB's JLC062012-1080 stackup
status: accepted
date: 2026-11-03
revision: B
page: pcb-fabrication
requirements: [REQ-QUAL-001]
rejected:
  - option: 6 layers, 1.6 mm (JLC061612-1080)
    reason: "$70 cheaper for five boards ($193.01 against $263.21, 2026-11-01), but the enclosure (DEC-023 to DEC-025, version 15) is built around a 2.0 mm board: the REDCUBE spigot stands 0.6 mm proud for the busbars and the AT13/ATM13 pin tails come through 0.7–1.5 mm. Version 12 records what 1.6 mm would change."
  - option: 8 layers, 2.0 mm (JLC082012-1080)
    reason: "$386.66 for five boards, 47 % more than 6 layers; with 2 oz inner copper JLCPCB forces its own \"special stackup\" and an $84.80 stackup fee, and the placement run's escape budget (4 signal layers) fits 6 layers."
  - option: 8 layers, 1.6 mm (JLC081612-1080)
    reason: "$349.46 for five boards, a forced special stackup with the same $84.80 fee, and the 1.6 mm drawbacks above."
  - option: PCBWay
    reason: "About 2.5 times JLCPCB's price for a 6-layer board (2026-11-01, 250 × 160 mm), and its board-wide minimum track for 2 oz copper (6/6 mil inner, 8/8 mil outer) conflicts with the 0.8 mm BGA escape."
---

## Context

DEC-023 made the board 2.0 mm thick, partly because JLCPCB builds 6 and 8 layers only up to 2.0 mm, and left the layer count, stackup and fab house open. On 2026-11-01 the user priced the 230 × 110 mm board (DEC-024) at JLCPCB in 6 and 8 layers at 1.6 and 2.0 mm, all with 1 oz outer and 2 oz inner copper, S1000-2M, ENIG and 0.20 mm filled vias (S34). The quotes, every form selection, JLCPCB's stackups and the via stack are on the [PCB stackup & fab quotes](../../pcb-fabrication/) page.

## Decision

- **6 layers, 2.0 mm, made by JLCPCB** (user, 2026-11-03).
- **Stackup JLC062012-1080**, as quoted: 1 oz outer, 2 oz inner copper; F.Cu / 1080 × 2 / In1.Cu / 0.55 mm core / In2.Cu / 2116 × 3 / In3.Cu / 0.55 mm core / In4.Cu / 1080 × 2 / B.Cu, 2.000 mm in all. `node60.kicad_pcb` already carries it, so the board file doesn't change.
- **Layer roles** are not part of this decision. The board file names In1.Cu and In4.Cu GND and In2.Cu and In3.Cu power; the placement plan (2026-11-02) proposes GND and VBAT_PROT planes with four signal layers. Routing settles it.
- **Reference price:** $263.21 for five boards before shipping (2026-11-01, without Gerbers). Re-quote with the real files before ordering.

## Consequences

- **Design rules follow JLCPCB's capabilities** (S35): 0.09 mm track and space on 1 oz layers (0.076 mm in BGA fan-outs), 0.15 / 0.15 mm on the 2 oz inner layers, so signals routed on In1–In4 need 0.15 mm; via hole to inner copper at least 0.20 mm; PTH annular ring 0.254 mm on the 2 oz layers.
- **Vias** are through only (no blind, buried or micro vias on this product), epoxy filled and capped free of charge, with a 10 : 1 aspect ratio at 0.20 mm.
- **Still open:**
  - **Outer copper weight.** Handbook chapter 05 asks for 2 oz on high-current paths. JLCPCB's 2 oz outer layers need 0.15 mm track and space, against the 0.10 mm the BGA escape uses, and a different outer copper weight is a different JLCPCB stackup, so it would amend this decision. Not decided here.
  - **Via option.** The 0.20 mm hole costs $37.90 (with the forced 4-wire test); the 0.3 mm option is enough if every via pad stays 0.45 mm or larger. The routing decides.
  - JLCPCB also offers **JLC062012-3313 and JLC062012-2116** at this thickness; they were not viewed. Changing to one is a stackup change to this decision.
- **Würth's approval** of the REDCUBE spigot standing 0.6 mm proud of the 2.0 mm board still blocks board release (DEC-023).
