---
id: DEC-002
title: INA228A-Q1 total-current monitor on the shared RSENSE
status: accepted
date: 2026-11-03
revision: B
page: subsystems/power
requirements: [REQ-MON-003]
parts: [INA228AQDGSRQ1, INA281A2QDBVRQ1, BVR-Z-R0003-1.0]
gates: [GATE-MON-01]
rejected:
  - option: INA281A2QDBVRQ1
    outcome: fallback
    reason: "Budget fallback only. Analog output needs an S32K344 ADC channel; ±300 µV maximum offset refers to about 1.0 A at 0.3 mΩ, so substantially higher offset and lower low-current accuracy."
  - option: INA240-Q1 (analog)
    reason: Zero stock, restock indicated around February 2027. INA228A-Q1 adds only about $0.90 at 1,000 pieces versus an INA240-class analog implementation.
  - option: INA229-Q1
    reason: Zero stock, restock indicated around February 2027.
  - option: INA186-Q1
    reason: 40 V common-mode ceiling leaves no margin for clamped load-dump transients; no authorized stock observed.
  - option: ST TSC2011
    reason: Automotive grade, exact part number, and pricing were not verified.
  - option: Microchip PAC1932/34 (PAC193x)
    reason: No AEC-Q100 qualification.
---

## Context

The shared 0.3 mΩ resistor (BVR-Z-R0003-1.0, 4-terminal since rev. B; 0.25 mΩ in rev. A) sees regulator, MCU, PHY, controller, and load current that the six channel readings cannot fully reconstruct. At 60 A it drops 18 mV and dissipates 1.08 W.

## Decision

**INA228AQDGSRQ1** is the plan of record: AEC-Q100 automotive qualified; 20-bit delta-sigma ADC; ±1 µV maximum shunt offset; ±0.05% maximum gain error; ±85 V bus range; I²C; VSSOP-10 (DGS). ADCRANGE = 1 gives ±40.96 mV; 18 mV at 60 A uses ≈44% of range. Firmware configures and verifies SHUNT_CAL for 0.3 mΩ (below). IN+ and IN− take the shunt's sense terminals, `RS_SENSE_P` and `RS_SENSE_N`.

## Why

INA228A-Q1 avoids an MCU ADC channel and preserves useful low-current accuracy despite the 0.3 mΩ resistor. It also digitizes the protected rail and reports current and power.

## Consequences

- Keep both voltage measurements: INA228 measures the protected rail, the LM74910H SW divider measures VBAT_RAW before the ideal-diode FET.
- Current diverted ahead of RSENSE, including through the primary TVS, remains outside this measurement.
- A single 60 A RSENSE cannot also resolve parked sleep current; parked-drain verification remains a validation-lab measurement.

## Calibration for 0.3 mΩ (rev. B, 2026-11-03)

INA228-Q1 SLYS022A equations 2 and 3, ADCRANGE = 1. The current LSB spreads the whole ADC range over 2¹⁹ counts:

- Maximum current = 40.96 mV / 0.3 mΩ = 136.53 A.
- CURRENT_LSB = 136.53 A / 2¹⁹ = **260.4167 µA**.
- SHUNT_CAL = 13107.2 × 10⁶ × CURRENT_LSB × RSHUNT × 4 = 13107.2 × 10⁶ × 260.4167 µA × 0.3 mΩ × 4 = **4096** (exact, no rounding).
- Power LSB = 3.2 × CURRENT_LSB = 833.3 µW.

Firmware writes SHUNT_CAL = 4096 and reads it back. If a round LSB is wanted instead, 300 µA (I max 150 A) gives SHUNT_CAL 4718.6 → 4719, at 0.009 % scaling error; this record uses 260.4167 µA. Rev. A's 0.25 mΩ shunt needed CURRENT_LSB 312.5 µA, with the same SHUNT_CAL 4096.

