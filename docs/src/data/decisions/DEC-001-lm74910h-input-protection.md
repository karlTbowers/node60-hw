---
id: DEC-001
title: LM74910H-Q1 input protection with shared RSENSE
status: accepted
date: 2026-10-13
revision: C
page: subsystems/power
requirements: [REQ-PWR-002, REQ-PWR-001, REQ-MON-004]
parts: [LM74910HQRGERQ1, TBD-RSENSE-0R25, TBD-OCP-NETWORK]
gates: [GATE-PWR-01, GATE-MON-01]
rejected:
  - option: LM74800-Q1 (LM74800QDRRRQ1) with a standalone 0.5 mΩ shunt
    outcome: replaced
    reason: The prior architecture had no input-rail overcurrent protection, and a separate measurement shunt doubled shunt heat at 60 A.
  - option: LM74900-Q1
    reason: Saves about $1 at 1,000 pieces but latches off after SLEEP-mode overcurrent instead of auto-retrying. That is the wrong trade for a battery-parked node whose MCU may be asleep when the fault occurs.
---

## Context

The 60 A-capable VBAT path needs reverse-battery blocking, overvoltage disconnect, overcurrent protection, and a total-current measurement. The prior architecture used LM74800-Q1 plus a standalone 0.5 mΩ shunt and had no input-rail overcurrent protection.

## Decision

Use **LM74910HQRGERQ1** to control the DGATE ideal-diode MOSFET bank and the HGATE disconnect MOSFET bank. One shared 0.25 mΩ, 1%, AEC-Q200 RSENSE sits between the two FET stages; LM74910H and INA228A-Q1 Kelvin-connect to it with independent star taps.

- Circuit breaker OCP 75 A: R(ILIM) = 32 kΩ, 1%; RSET = 50 Ω.
- Fast SCP 20 mV default = 80 A with 0.25 mΩ; no RISCP resistor fitted.
- TMR ≈68 nF for an ≈1 ms starting-point breaker delay.
- FLT to S32K344; SLEEP OCP auto-retry. IMON not populated while INA228 is fitted.

## Why

One resistor now serves both protection and precise measurement, cutting shunt heat in half at 60 A. More importantly, LM74910H adds a programmable breaker, fast short-circuit trip, separate UVLO, FLT warning, and SLEEP-mode OCP auto-retry. LM74910H adds about $1.70 at 1,000 pieces versus the prior controller/shunt pair.

## Consequences

- BATT_MON moves to the LM74910H SW-pin OV/UV divider. The OV threshold is 0.6 V rather than the LM74800’s 1.23 V, so all divider values are recalculated at schematic review.
- MOSFETs (80–100 V AEC-Q101) are chosen after surge/thermal calculation.
- LM74910HQRGERQ1 carries a 26-week manufacturer lead if distributor stock is depleted.
