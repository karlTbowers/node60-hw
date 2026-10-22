---
id: DEC-008
title: Three TPS2HCS08A-Q1 dual smart high-side switches
status: accepted
date: 2026-10-13
revision: A
page: subsystems/outputs
requirements: [REQ-OUT-001, REQ-OUT-002, REQ-MON-001]
parts: [TPS2HCS08AQPWPRQ1]
gates: [GATE-THM-01, GATE-OUT-01, GATE-OUT-02, GATE-MON-02]
rejected:
  - option: TPS481HS04-Q1
    outcome: future
    reason: Advance Information only; remains a future higher-current revision only after production release.
---

## Context

Six independently commanded battery-side outputs each target 10 A continuous, with per-output current and voltage telemetry and wire protection.

## Decision

Use three **TPS2HCS08A-Q1** dual-channel smart high-side switches (TPS2HCS08AQPWPRQ1, HTSSOP-16 PowerPAD) for the six-output active design: SPI control in a daisy chain with CRC, shared analog SNS telemetry, diagnostics, and programmable I²t wire protection.

## The 8 A both-on limit

TI specifies 13 A continuous at 85 °C with one channel enabled, but only **8 A per channel when both channels are enabled**. Because every device serves two outputs, 10 A continuous on all six outputs cannot be released until the complete PCB, enclosure, ambient, and adjacent-channel thermal matrix proves it. If direct thermal proof fails, derate the output, improve thermal spreading, or move the higher-current revision forward.

## Consequences

- RON 8.9 mΩ typical at 25 °C and 17.8 mΩ at 150 °C: six outputs at 10 A dissipate about 5.34 W cold or 10.68 W hot before other losses.
- Zero distributor stock was observed on 2026-10-13, with a 20-week standard lead.
