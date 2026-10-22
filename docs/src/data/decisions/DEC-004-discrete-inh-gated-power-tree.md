---
id: DEC-004
title: Discrete INH-gated power tree; FS26 removed
status: accepted
date: 2026-10-13
revision: A
page: subsystems/power
requirements: [REQ-PWR-001, REQ-PWR-003]
parts: [LMQ66430QMC5RXBRQ1, TBD-VDDAU-LDO]
gates: [GATE-NET-01]
rejected:
  - option: NXP FS26 system basis chip (earlier draft)
    outcome: removed
    reason: "Its original roles are covered by the two LMQ66430 bucks, the S32K344 internal windowed SWT, the TPS3702 rail supervisor, and the LAN8670 INH gatekeeper. Reconsider an SBC only in a later revision if wake or sequencing requirements outgrow direct INH gating and EN-pin chaining."
  - option: Wake latch or MCU-controlled gate in the INH → EN path
    reason: Not needed; EN-pin chaining establishes the rail order without extra logic or an MCU standby dependency.
---

## Context

The parked node must draw very little from the battery, and the S32K3 Zephyr standby implementation is missing. An earlier draft used an FS26 SBC for sequencing and supervision.

## Decision

FS26 is removed. A nanopower LDO supplies only LAN8670 VDDAU while parked; LAN8670 INH directly enables the two LMQ66430-Q1 bucks. EN-pin chaining establishes the 3.3 V / 1.5 V order without an SBC, wake latch, or extra logic. Do not place FS26 in the Rev A schematic or BOM.

## Consequences

- On bus wake, the external supplies must ramp within 1 ms. Verify EN-chain delay, regulator soft-start, MCU reset release, PHY-ready IRQ_N, and whole-board inrush together.
- VDDA must never exceed VDDAU by more than 0.5 V; the always-on-first topology satisfies that rule by construction.
- INH powers the complete switched tree at once, so the LM74910H TMR breaker ride-through is sized for the startup inrush.
- The nanopower LDO (target Iq ≈1–2 µA) is a schematic-selection item.
