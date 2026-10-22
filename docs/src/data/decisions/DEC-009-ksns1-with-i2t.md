---
id: DEC-009
title: KSNS1 current-sense gain while I²t is active
status: accepted
date: 2026-10-13
revision: A
page: subsystems/outputs
requirements: [REQ-MON-002]
parts: [TPS2HCS08AQPWPRQ1]
gates: [GATE-MON-02, GATE-OUT-01]
rejected:
  - option: KSNS2 with 8× ADC scaling
    reason: TI recommends KSNS2 and 8× ADC scaling only with I²t disabled; altered scaling can lower the effective I²t trip threshold.
  - option: Per-output shunt or external monitor
    reason: Not fitted; the shared 0.25 mΩ RSENSE and INA228A-Q1 independently monitor the total input rail.
---

## Context

KSNS2 improves low-current ratio accuracy (±10% at 100 mA versus ±18% for KSNS1), but interacts with I²t protection.

## Decision

Rev A keeps KSNS1 while I²t is active and budgets ±18% at 100 mA. The nominal count separation supports a 100 mA **resolution** claim after filtering and calibration; it does not imply ±100 mA absolute accuracy.
