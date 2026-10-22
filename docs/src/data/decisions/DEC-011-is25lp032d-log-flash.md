---
id: DEC-011
title: IS25LP032D-JNLA3 diagnostic log flash
status: accepted
date: 2026-10-13
revision: C
page: subsystems/firmware
requirements: [REQ-PWR-003]
parts: [IS25LP032D-JNLA3, W25Q32JVSSSQ]
gates: [GATE-FW-01, GATE-BOM-01]
rejected:
  - option: W25Q32JVSSIG, MX25L12833F, ISSI non-A3 grades, Micron -0SIT standard versions, GD25Q128C
    reason: Do not substitute; not the automotive grade required.
  - option: 16 Mbit device
    reason: Sufficient capacity, but 32 Mbit is the commodity availability sweet spot.
---

## Context

The node powers down completely when parked, so the diagnostic log must live in non-volatile memory that survives complete power-down.

## Decision

Fit **IS25LP032D-JNLA3**, a 32 Mbit AEC-Q100 Grade 1 SPI NOR, on switched 3V3_MAIN. It holds 65,536 fixed 64-byte records, about 1.8 years before wrap at 100 events per day. **Winbond W25Q32JVSSSQ** is the Grade 1 second-source candidate; verify its price and stock, and review hardware/software interchangeability.

## Consequences

- Controller-commanded shutdown provides the flush window before PHY sleep: up to 10 pages = ≤8 ms worst case.
- Ahead-erase during normal operation; never begin sector erase at sleep entry.
- Constrained supply observed (no backorders, 2,000 units per 30 days; 50-week factory lead at an aggregator): reconfirm at BOM lock.
