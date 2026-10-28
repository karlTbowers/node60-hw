---
id: DEC-015
title: 16 MHz crystal on the S32K344 FXOSC instead of running from FIRC only
status: accepted
date: 2026-10-28
revision: A
page: subsystems/compute
requirements: [REQ-QUAL-001]
parts: [TBD-XTAL-16M]
gates: [GATE-MCU-01, GATE-SUP-04, GATE-FW-02, GATE-BOM-01]
rejected:
  - option: No crystal; FIRC clocks the core, EXTAL/XTAL unconnected (schematic draft, 2026-10-23)
    reason: The user wants better timing accuracy than the internal fast oscillator gives (2026-10-28).
  - option: 40 MHz crystal
    reason: The top of the FXOSC range. Higher drive level and fewer Grade 1 parts to choose from, for no gain on Node60.
  - option: 8 MHz crystal
    reason: The bottom of the FXOSC range. It moves away from NXP's S32K3 reference designs, so clock-tree and Zephyr board settings would not carry over.
---

## Context

Architecture Rev A named no MCU clock source. The schematic draft (2026-10-23) clocked the S32K344 from its internal fast oscillator (FIRC) and left EXTAL/XTAL unconnected. The RMII interface does not depend on it: the 50 MHz ECS-3225SMVQ oscillator clocks both the LAN8670 and the MCU's RMII reference.

In the schematic review on 2026-10-28 the user chose to fit a crystal, for better timing accuracy than FIRC.

## Decision

**One 16 MHz crystal on the S32K344 FXOSC (EXTAL ball K1, XTAL ball L1)**, with load capacitors sized from the crystal's load capacitance and NXP's S32K3 Hardware Design Guidelines.

- 16 MHz is inside the FXOSC's 8–40 MHz crystal range and matches NXP's S32K3 reference designs, so their clock-tree settings and Zephyr board configuration carry over.
- The part is not selected yet (`TBD-XTAL-16M`): AEC-Q200, −40 to +125 °C, 3.2 × 2.5 mm or smaller, with ESR and drive level inside the FXOSC limits in the S32K3 data sheet.

## Consequences

- **Library:** the selected crystal goes into dropout-kicad-library first (add-part), then onto the MCU page with its load capacitors.
- **Pin audit:** EXTAL/XTAL change from unconnected to used. GATE-MCU-01 covers them.
- **Layout:** crystal and load capacitors next to K1/L1, short traces, ground guard, away from the switch outputs' high di/dt loops and the SNS/ADC returns (safety page layout rules).
- **Firmware:** the clock tree runs from FXOSC through the PLL. The Clock Monitoring Unit watches FXOSC as well as FIRC, so GATE-SUP-04 adds an FXOSC-failure injection; GATE-FW-02 covers the Zephyr clock configuration.
- **Cost and supply:** one crystal and two capacitors; checked at BOM lock (GATE-BOM-01).
