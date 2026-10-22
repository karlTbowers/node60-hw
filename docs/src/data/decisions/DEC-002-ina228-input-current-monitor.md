---
id: DEC-002
title: INA228A-Q1 total-current monitor on the shared RSENSE
status: accepted
date: 2026-10-13
revision: C
page: subsystems/power
requirements: [REQ-MON-003]
parts: [INA228AQDGSRQ1, INA281A2QDBVRQ1, TBD-RSENSE-0R25]
gates: [GATE-MON-01]
rejected:
  - option: INA281A2QDBVRQ1
    outcome: fallback
    reason: "Budget fallback only. Analog output needs an S32K344 ADC channel; ±300 µV maximum offset refers to about 1.2 A at 0.25 mΩ, so substantially higher offset and lower low-current accuracy."
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

The shared 0.25 mΩ resistor sees regulator, MCU, PHY, controller, and load current that the six channel readings cannot fully reconstruct. At 60 A it drops 15 mV and dissipates 0.9 W.

## Decision

**INA228AQDGSRQ1** is the plan of record: AEC-Q100 automotive qualified; 20-bit delta-sigma ADC; ±1 µV maximum shunt offset; ±0.05% maximum gain error; ±85 V bus range; I²C; VSSOP-10 (DGS). ADCRANGE = 1 gives ±40.96 mV; 15 mV at 60 A uses ≈37% of range. Firmware configures and verifies SHUNT_CAL for 0.25 mΩ.

## Why

INA228A-Q1 avoids an MCU ADC channel and preserves useful low-current accuracy despite the 0.25 mΩ resistor. It also digitizes the protected rail and reports current and power.

## Consequences

- Keep both voltage measurements: INA228 measures the protected rail, the LM74910H SW divider measures VBAT_RAW before the ideal-diode FET.
- Current diverted ahead of RSENSE, including through the primary TVS, remains outside this measurement.
- A single 60 A RSENSE cannot also resolve parked sleep current; parked-drain verification remains a validation-lab measurement.
