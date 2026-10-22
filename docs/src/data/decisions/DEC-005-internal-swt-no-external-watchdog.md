---
id: DEC-005
title: S32K344 internal SWT; no external watchdog
status: accepted
date: 2026-10-13
revision: A
page: subsystems/supervision
requirements: [REQ-SAF-001]
parts: [S32K344EHT1MMMST, TPS3430WQDRCRQ1]
gates: [GATE-SUP-04, GATE-SUP-05]
rejected:
  - option: TPS3430WQDRCRQ1 external window watchdog
    outcome: deferred
    reason: Windowed, AEC-Q100 Grade 1, and observed in stock, but duplicates the internal windowed SWT without improving rail-fault coverage because it dies with the same supply. Evaluate it only if a later revision must support an ASIL safety case; it is not part of the current BOM.
  - option: TPS3823-Q1-class supervisor/watchdog combination
    reason: Its non-windowed watchdog is a functional downgrade from the internal SWT.
---

## Context

Software failure detection is needed without adding parts that share a failure mode with the MCU supply.

## Decision

The S32K344 Software Watchdog Timer is the plan-of-record watchdog; no external watchdog is fitted. It is window-capable, enabled by default out of reset, and can be hard-locked so runaway code cannot disable or reconfigure it. Configure a legal service window, verify reset action, hard-lock its configuration after startup checks, and test early, late, missing, and malformed service sequences.

## Why

The S32K3 Clock Monitoring Unit already converts monitored clock failure into reset, closing the other major gap an ordinary external watchdog would address. The upstream Zephyr `nxp,s32-swt` driver avoids custom driver work.
