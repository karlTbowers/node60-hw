---
id: DEC-010
title: TMP175-Q1 plus four NTCs for hotspot coverage
status: accepted
date: 2026-10-13
revision: A
page: subsystems/temperature
requirements: [REQ-OUT-001]
parts: [TMP175-Q1, TBD-NTC-10K]
gates: [GATE-TMP-01, GATE-TMP-02, GATE-TMP-03, GATE-TMP-04, GATE-TMP-05]
rejected:
  - option: TI TMP126-Q1
    reason: "The only verified higher-accuracy option (±0.4 °C maximum, AEC-Q100 Grade 0, approximately $1.80 at 1,000 pieces, in DigiKey stock), but SPI-only: it needs a chip-select and LPSPI allocation and cannot share the INA228 I²C bus. The added interface cost and complexity outweigh the accuracy gain for the NFET-bank ambient role."
  - option: TPS2HCS08A-Q1 FET temperature as package-temperature evidence
    reason: ±17 °C maximum, and disabled on all channels whenever any channel enters the I²t loop.
---

## Context

The external LM74910H NFET bank is the primary thermal blind spot; the shared RSENSE and the three switch packages need their own temperature evidence.

## Decision

**TMP175-Q1** is the plan-of-record digital sensor beside the NFET bank: AEC-Q100 Grade 1, 2.7–5.5 V supply, SOIC-8 or VSSOP-8, I²C/SMBus, up to 27 devices per bus, no address conflict with the INA228. Add four 10 kΩ AEC-Q200 NTCs: one at the shared RSENSE and one beside each TPS2HCS08A-Q1 package.

## Consequences

- Five added sensors, ≈$1.50–2.50 total added BOM estimate.
- Firmware never trusts switch temperature registers during an I²t event and uses the package NTCs instead.
