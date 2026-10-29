---
id: DEC-006
title: TPS3702-Q1 window supervisor on 3V3_MAIN
status: accepted
date: 2026-10-13
revision: A
page: subsystems/supervision
requirements: [REQ-SAF-001]
parts: [TPS3702-Q1]
gates: [GATE-SUP-01, GATE-SUP-02, GATE-SUP-03, GATE-SUP-05]
rejected:
  - option: Another watchdog instead of a rail supervisor
    reason: No watchdog can detect a rail fault after its own supply has collapsed.
  - option: Separate 1.5 V supervisor
    reason: The S32K344 internal low-voltage detector already monitors the core domain.
---

## Context

Cold-crank droops and load-dump disturbances can move 3V3_MAIN outside the MCU/PHY operating window.

## Decision

Add **1 × TPS3702-Q1** to supervise the 3.3 V MCU/PHY rail. It provides separate overvoltage and undervoltage detection with ±0.9% threshold accuracy over −40…+125 °C and is AEC-Q100 Grade 1 in SOT-6. Its reset output drives **RESET_L**.

## Consequences

- Budget about $1; confirm the exact fixed-threshold 3.3 V orderable code, pricing, and authorized stock at BOM lock.
- Route TPS3702-Q1 directly from 3V3_MAIN to RESET_L; document threshold variant, reset timing, pull-up domain, and interaction with MCU POR/LVD.
