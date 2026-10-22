---
id: DEC-003
title: XLD8A24CA as primary load-dump TVS
status: accepted
date: 2026-10-13
revision: C
page: subsystems/power
requirements: [REQ-PWR-002]
parts: [XLD8A24CA]
gates: [GATE-PWR-01, GATE-THM-02]
rejected:
  - option: SMBJ24CA
    reason: Not accepted as the sole primary load-dump element.
---

## Context

The node sits on a 12 V nominal vehicle supply with protected automotive transients, and its regulators are 40 V-class parts behind a load-dump clamp.

## Decision

A 24 V bidirectional **XLD8A24CA** TVS (7 kW class, AEC-Q101) is preferred after the source fuse.

## Consequences

- Verify the clamp against regulator and MOSFET limits.
- Price and stock were not verified for Rev C.
