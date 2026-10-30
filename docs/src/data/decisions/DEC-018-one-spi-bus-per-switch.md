---
id: DEC-018
title: One LPSPI bus per TPS2HCS08A-Q1 output switch
status: accepted
date: 2026-10-30
revision: B
page: subsystems/outputs
requirements: [REQ-OUT-001, REQ-OUT-002, REQ-SAF-001, REQ-FW-001]
parts: [TPS2HCS08AQPWPRQ1, S32K344EHT1MMMST]
gates: [GATE-OUT-02, GATE-MCU-01, GATE-FW-02]
rejected:
  - option: "Rev. A: one LPSPI4 daisy chain (shared SCLK and CS_L, U601 SDO → U701 SDI → U801 SDO → MCU)"
    reason: "Every frame passes through all three switches, so one open, unpowered or stuck switch cuts off control of all six outputs, and a CRC error does not say which switch failed. In Zephyr all three switches share one chip select, so they appear as a single SPI device: the driver has to build and split composite frames instead of being one driver with three instances. Changed in rev. B (user, 2026-10-30)."
  - option: One LPSPI bus with a separate chip select per switch (shared SCLK, SDI and SDO)
    reason: "Uses about two more pins than the chain and fits Zephyr's one-device-per-CS model, but a switch whose SDO is stuck driving still corrupts reads from all three, and a hung transfer holds the shared bus lock and stalls every switch until the driver times out. The pins and LPSPI instances are free, so the user chose full separation."
---

## Context

Rev A drove all three TPS2HCS08A-Q1 switches from one LPSPI4 daisy chain (DEC-008). The TPS2HCS08-Q1 data sheet (SLVSHR0, §8.3.3) supports both a daisy chain (its Figure 8-7) and independent devices with their own chip select (its Figure 8-6). The S32K344 has six LPSPI instances. Rev A used two of them (LPSPI4 for the switches, LPSPI2 for the log flash), and the 257-ball package has free balls for the rest. The firmware runs on Zephyr (DEC-019).

## Decision

**Each switch gets its own LPSPI instance, with its own SCLK, SDI, SDO and chip select. Nothing is shared between the three buses.**

| Switch | Outputs | LPSPI | SCK | SOUT → SDI | SIN ← SDO | PCS0 → CS |
|---|---|---|---|---|---|---|
| U601 | 1-2 | LPSPI4 | D15 (PTB10) | C15 (PTB9) | C17 (PTB11) | A14 (PTB8) |
| U701 | 3-4 | LPSPI5 | A16 (PTD26) | A15 (PTD27) | B13 (PTD28) | G16 (PTD4) |
| U801 | 5-6 | LPSPI3 | E14 (PTF13) | F14 (PTF15) | E15 (PTF12) | G15 (PTF16) |

- U601 keeps the Rev A LPSPI4 balls. LPSPI5 and LPSPI3 were chosen because their balls cluster near LPSPI4 at the top-right of the package, and each has PCS0 on a free ball.
- Net names follow the bus, instance and switch: `SPI4_SWITCH1_*`, `SPI5_SWITCH2_*`, `SPI3_SWITCH3_*`. The output-switch sheet, which is placed three times, now exposes generic `SDI`, `SDO`, `SCK` and `CS_L` ports.
- **SPI settings** (data sheet §8.3.3 and §6.6 SPI Timing Requirements): SDI is latched on the falling SCLK edge and SDO shifts on the rising edge, which is mode 1 (CPOL 0, CPHA 1). SCLK is 8 MHz maximum. With CRC on, every frame is 32 bits. CS setup and hold are 45 ns minimum each.
- **SPI watchdog on, limp-home to off.** Firmware sets WD_EN = 1 and WD_TO = 400 ms, and sets the CHx_LH_IN bits so that both channels are off in LIMP_HOME (version A, §8.3.7). If a bus or the firmware stops talking to a switch, that switch turns both of its outputs off and pulls FLT low. The other two switches keep running.

## Failure behaviour compared

| Failure | Rev A chain | Rev B: one bus per switch |
|---|---|---|
| One switch open, unpowered or SDO stuck | All 6 outputs lose control | 2 outputs lose control, then turn off on the SPI watchdog |
| Bus hangs in a transfer (Zephyr bus lock held until timeout) | All 6 stall | 2 stall |
| Locating a CRC or readback fault | The chain, not the switch | The switch |

## Consequences

- **Schematic:** 8 more U401 balls are used (A15, A16, B13, G16 on PTD; E14, E15, F14, G15 on PTF). The nets `SPI4_SWITCH_CHAIN1` and `SPI4_SWITCH_CHAIN2` are gone. The CS lines rely on each switch's internal pull-up to VDD through reset, as in Rev A. Every line of all three buses has an MCU-side test point: TP403–TP406 (SPI4), TP413–TP416 (SPI5) and TP417–TP420 (SPI3). Each switch's SDO also has one on its own page (TP603, TP703, TP803).
- **Pin audit:** U401's pin plan changed, so GATE-MCU-01 was re-run for the eight new balls (IBIS and BSDL cross-check). The user signed it off on 2026-10-30.
- **Firmware (Zephyr):** one `nxp,lpspi` node per bus, each with the switch as its child at `reg = <0>` (native PCS0, no `cs-gpios`), `spi-max-frequency` ≤ 8 MHz, and `pcs-sck-delay` / `sck-pcs-delay` ≥ 45 ns. One out-of-tree TPS2HCS08A driver with three instances. Each instance owns its FLT/WAKE interrupt, SNS ADC channel and NTC. A periodic task services every switch well inside the 400 ms watchdog window.
- **Verification:** GATE-OUT-02 now injects faults per bus (open SDO, stuck SDO, missing CS, firmware stall → watchdog limp-home off) and checks that the other two switches are unaffected.
- **Cost:** no added parts. Two more LPSPI instances and their balls, which were free.
