---
id: DEC-015
title: 16 MHz crystal on the S32K344 FXOSC instead of running from FIRC only
status: accepted
date: 2026-10-28
revision: A
page: subsystems/compute
requirements: [REQ-QUAL-001]
parts: [ABM8AIG-16.000MHZ-8-1Z-T, CX3225CA16000D0HSSCC, ECS-160-8-36Q-AES-TR]
gates: [GATE-MCU-01, GATE-SUP-04, GATE-FW-02, GATE-BOM-01]
rejected:
  - option: No crystal; FIRC clocks the core, EXTAL/XTAL unconnected (schematic draft, 2026-10-23)
    reason: The user wants better timing accuracy than the internal fast oscillator gives (2026-10-28).
  - option: 40 MHz crystal
    reason: The top of the FXOSC range. Higher drive level and fewer Grade 1 parts to choose from, for no gain on Node60.
  - option: 8 MHz crystal
    reason: The bottom of the FXOSC range. It moves away from NXP's S32K3 reference designs, so clock-tree and Zephyr board settings would not carry over.
  - option: KYOCERA AVX CX3225CA16000D0HSSCC
    reason: Same size and load as the selected part, deepest stock, but ±20 ppm at 25 °C and 100 Ω ESR. Kept as the second source; it has its own land pattern and leaves pads 2/4 unconnected, so a swap is a footprint change.
    outcome: alternative
  - option: ECS ECS-160-8-36Q-AES-TR
    reason: Cheapest and smallest (2.5 × 2.0 mm), but ±25 ppm at 25 °C, the least accurate of the three.
    outcome: alternative
  - option: NDK STDCQS1-16M (the crystal on NXP's FRDM-A-S32K344 and S32K344MINI-EVB)
    reason: No DigiKey stock and not listed at Mouser or Newark on 2026-10-28. ±15 ppm, 120 Ω ESR.
  - option: Jauch Q 16,0-JXS32P4-8-10/50-T3-AEC-LF
    reason: Its ±10 ppm tolerance code is not offered with the −40 to +125 °C (T3) range in Jauch's JXS32P4 datasheet, so the listing is doubtful; DigiKey only.
---

## Context

Architecture Rev A named no MCU clock source. The schematic draft (2026-10-23) clocked the S32K344 from its internal fast oscillator (FIRC) and left EXTAL/XTAL unconnected. The RMII interface does not depend on it: the 50 MHz ECS-3225SMVQ oscillator clocks both the LAN8670 and the MCU's RMII reference.

In the schematic review on 2026-10-28 the user chose to fit a crystal, for better timing accuracy than FIRC.

## Decision

**One 16 MHz crystal on the S32K344 FXOSC (EXTAL ball K1, XTAL ball L1)**, with load capacitors sized from the crystal's load capacitance and NXP's S32K3 Hardware Design Guidelines.

- 16 MHz is inside the FXOSC's 8–40 MHz crystal range and matches NXP's S32K3 reference designs, so their clock-tree settings and Zephyr board configuration carry over.
- **Crystal: Abracon ABM8AIG-16.000MHZ-8-1Z-T** (selected by the user, 2026-10-28). AEC-Q200, −40 to +125 °C, 3.2 × 2.5 mm, CL 8 pF, ±10 ppm at 25 °C, ±50 ppm over temperature, ±2 ppm first-year aging, ESR 70 Ω max, C0 2 pF max, drive level 100 µW max (ABM8AIG datasheet, revised 06-13-19). Second source: KYOCERA AVX CX3225CA16000D0HSSCC.
- **Load and series parts:** 2 × 10 pF C0G on EXTAL and XTAL and a 0 Ω series resistor (RsEXT) on XTAL, the circuit on NXP's FRDM-A-S32K344 (Y1 16 MHz 8 pF, C65/C66 10 pF, R80 0 Ω) and the worked example in the Hardware Design Guidelines (Rev. E2, Table 23). Final values are tuned on the first boards (HDG §3.1: characterize on the PCB with the crystal maker).

## Numbers

Start-up margin (S32K3xx data sheet Rev. 14, Figure 46; HDG Rev. E2 §3.2), with RsEXT = 0 Ω:

gm_crit = 4 × (ESR + RsEXT) × (2π × 16 MHz)² × (C0 + CL)² = 4 × 70 Ω × 1.011 × 10¹⁶ s⁻² × (10 pF)² = **0.28 mA/V**

NXP asks for gm > 5 × gm_crit = 1.4 mA/V. The FXOSC amplifier's GM is 9.7 mA/V minimum (data sheet Table 45), about 34 × gm_crit.

Drive level, estimated from the EXTAL swing limit: 1.4 V peak-to-peak with ALC enabled gives about 0.5 V rms, so about 0.5 mA through C0 + CL and about 17 µW in 70 Ω. With ALC disabled (2.75 V peak-to-peak) it is about 67 µW. Both are under the crystal's 100 µW maximum, so RsEXT stays 0 Ω; its footprint allows a limiting resistor if the board measurement needs one.

## Consequences

- **Schematic:** Y401 with C424/C425 (GCM1555C1H100JA16D, 10 pF C0G 50 V ±5 %) and R408 (0 Ω) on p4, nets FXOSC_EXTAL, FXOSC_XTAL and FXOSC_XTAL_X. All three crystals and the capacitor come from dropout-kicad-library PR #35.
- **Pin audit:** EXTAL/XTAL change from unconnected to used. GATE-MCU-01 covers them.
- **Layout:** crystal and load capacitors next to K1/L1, short traces with no vias, a clean ground area under the oscillator, both capacitor grounds close together (HDG Rev. E2 §3.2, Figure 37 for the 257MAPBGA), away from the switch outputs' high di/dt loops and the SNS/ADC returns (safety page layout rules).
- **Firmware:** the clock tree runs from FXOSC through the PLL. The Clock Monitoring Unit watches FXOSC as well as FIRC, so GATE-SUP-04 adds an FXOSC-failure injection; GATE-FW-02 covers the Zephyr clock configuration.
- **Cost and supply:** one crystal and two capacitors; checked at BOM lock (GATE-BOM-01).
