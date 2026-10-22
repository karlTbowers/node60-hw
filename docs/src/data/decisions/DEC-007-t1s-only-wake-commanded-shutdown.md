---
id: DEC-007
title: T1S-only wake with controller-commanded shutdown
status: accepted
date: 2026-10-13
revision: A
page: subsystems/network
requirements: [REQ-NET-001, REQ-PWR-001, REQ-PWR-003]
parts: [LAN8670D0-E/LMXVAO, IS25LP032D-JNLA3]
gates: [GATE-NET-01, GATE-PWR-02]
rejected:
  - option: Bus-idle timeout as the sleep source
    reason: Shutdown must be transactional (outputs off, log flushed, then PHY sleep). Bus idle alone must not be able to sleep the node.
  - option: KL15, ignition, or local hardwire wake input
    reason: The node cable has exactly four conductors; the controller ECU owns the only wake source.
  - option: MCU standby with wake latch
    reason: The parked node is powered down except for the LAN8670 always-on domain, so the missing S32K3 Zephyr standby implementation is no longer on the critical path.
---

## Context

The node connects with four wires only: T1S twisted pair, battery-direct power, and ground. The controller ECU, powered from battery and switched ignition, owns the only wake source and sends the T1S wake-up pattern over the same pair used for data.

## Decision

- **Wake:** controller sends T1S wake-up tone → PHY detects it → INH high → bucks ramp → S32K344 cold boot → PHY re-initialization → link up → outputs become commandable. A roughly 1 s application-ready latency is acceptable.
- **Shutdown:** controller sends an application-level “go to sleep” message → firmware turns all six outputs off → flushes pending log entries → commands PHY sleep → INH releases after tSLPINHDLY → power tree collapses. Write-before-sleep ordering is mandatory.

## Consequences

- If the controller ECU does not emit the wake pattern, the node stays off. This is a controller-interface requirement, not a recoverable local condition.
- PHY registers are lost while VDDA/VDDP are down; IRQ_N indicates readiness for configuration.
- No logging occurs while parked.
