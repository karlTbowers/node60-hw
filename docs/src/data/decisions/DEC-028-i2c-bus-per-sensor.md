---
id: DEC-028
title: One I²C bus per sensor, and the INA228 ALERT to the MCU
status: accepted
date: 2026-11-19
revision: B
page: subsystems/compute
requirements: [REQ-MON-003]
parts: [INA228AQDGSRQ1, TMP175-Q1, S32K344EHT1MMMST]
gates: [GATE-MCU-01, GATE-TMP-02]
rejected:
  - option: Keep both sensors on LPI2C0 (Rev A)
    reason: "Rev A's arrangement, replaced on the user's decision of 2026-11-19. On one bus, a device holding SDA or SCL low stops both the current monitor and the temperature sensor."
  - option: Leave the INA228 ALERT pin open (Rev A)
    reason: "Rev A never listed the pin, and no reason was recorded. Without it the MCU learns of an INA228 limit or a finished conversion only by polling."
  - option: LPI2C1 on PTD8 / PTD9 (R8 / U8)
    reason: "Free and valid, but on U401's north edge, the far side from the sensors. PTC6 / PTC7 are on the south edge beside the two alert balls."
---

## Context

Rev A put the INA228A-Q1 (U202, address 0x40) and the TMP175-Q1 (U203, address 0x48) on one bus, LPI2C0, and left the INA228's ALERT pin open. Only the TMP175's ALERT was reserved for the MCU. The S32K344 has a second controller, LPI2C1, that the pin plan did not use. On 2026-11-19 the user chose to use both controllers and to wire the INA228's ALERT.

## Decision

**Each sensor has its own I²C bus, and both ALERT outputs go to MCU interrupt balls.**

| Net | Device | MCU ball | Function | Pull-up | Test point |
|---|---|---|---|---|---|
| `I2C0_TELEMETRY_SDA` | U202 INA228 | P5 (PTD13) | LPI2C0_SDA | R407 2.2 kΩ | TP410 |
| `I2C0_TELEMETRY_SCL` | U202 INA228 | M4 (PTD14) | LPI2C0_SCL | R406 2.2 kΩ | TP409 |
| `I2C1_TEMP_SDA` | U203 TMP175 | C12 (PTC6) | LPI2C1_SDA | R420 2.2 kΩ | TP422 |
| `I2C1_TEMP_SCL` | U203 TMP175 | B12 (PTC7) | LPI2C1_SCL | R419 2.2 kΩ | TP421 |
| `INA228_ALERT_L` | U202 pin 3 | A12 (PTA16) | EIRQ[4] | R213 10 kΩ | TP210 |

All pull-ups go to `3V3_MAIN`. The LPI2C0 balls, pull-ups and test points are unchanged; U203 leaves that bus.

## Why

- The INA228's ALERT is an open-drain output, active low by default (SLYS022A, pin table), so it takes a pull-up like the TMP175's: 10 kΩ, as R211.
- PTA16 is in Zephyr's `nxp,siul2-gpio` pin-to-EIRQ table on line 4, which no other Node60 interrupt uses (lines 0, 1, 2, 6, 17 and 23 are taken), so the DEC-019 pin-plan rule holds. Checked against `nxp_s32k344_m7.dtsi` on Zephyr `main`, 2026-11-19.
- LPI2C1_SDA and LPI2C1_SCL are in the IOMUX alternate lists of C12 and B12 (library pin table, generated from NXP's IOMUX table).
- The three balls were unconnected with no-connect flags. They sit on the south edge of U401, the side that faces the power entry, next to `TMP175_ALERT_L` (A11) and `LM_FLT_L` (B11).

## Consequences

- Six parts are added: R213, R419, R420 (0402) and the pad test points TP210, TP421, TP422.
- The PCB must be updated from the schematic: U203's SDA and SCL pads change net, so the LPI2C0 copper at U203 is re-routed, and the three new lines are routed to U401.
- GATE-MCU-01 is open again for A12, B12 and C12. The IOMUX check passed; the IBIS and BSDL checks and the user's sign-off are outstanding.
- Firmware: a second `nxp,lpi2c` node (`&lpi2c1`) for the TMP175, and an interrupt on `INA228_ALERT_L` (falling edge). What the ALERT reports (a limit or conversion ready) is set in the INA228's DIAG_ALRT register and is a firmware choice, not decided here.
- PTC6 / PTC7 were also the nearest free LPUART1 pair. LPUART1 can still go on M6 / M7 or N14 / N15.
- `TMP175_ALERT_L` still has no test point, although handbook chapter 05 asks for one on interrupt lines. Not changed here.
