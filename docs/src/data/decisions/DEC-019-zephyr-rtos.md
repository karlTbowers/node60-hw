---
id: DEC-019
title: Zephyr is Node60's core RTOS
status: accepted
date: 2026-10-30
revision: B
page: subsystems/firmware
requirements: [REQ-FW-001, REQ-SAF-001]
parts: [S32K344EHT1MMMST]
gates: [GATE-FW-02, GATE-MCU-01]
---

## Context

Rev A listed Zephyr as a basis requirement (REQ-FW-001) and relied on it in several decisions: the `nxp,s32-swt` watchdog driver (DEC-005), the FCB and NVS flash storage (DEC-011), and the reference clock configuration (DEC-015). No decision recorded the RTOS itself or what it requires of the hardware. On 2026-10-30 the user confirmed Zephyr as the core RTOS and asked for the pin plan to be reviewed against it. This record does not compare other RTOS options; the user made the choice.

## Decision

**All Node60 firmware runs on Zephyr RTOS on the S32K344's Cortex-M7 core, using the upstream S32K344 SoC support** (`dts/arm/nxp/s32/nxp_s32k344_m7.dtsi`; the closest upstream board is NXP's MR-CANHUBK344, `mr_canhubk3`). Hardware choices should make each device a separate, standard Zephyr devicetree node wherever possible. That rule drove DEC-018.

## Driver map (upstream Zephyr `main`, checked 2026-10-30)

| Function | Node60 part / peripheral | Zephyr compatible | Status |
|---|---|---|---|
| Pin mux | SIUL2 | `nxp,s32k3-siul2-pinctrl` | Upstream |
| GPIO and pin interrupts | SIUL2 GPIO + EIRQ | `nxp,siul2-gpio`, `nxp,siul2-eirq` | Upstream. Every interrupt ball in the pin plan is in the driver's EIRQ map, on distinct lines (0, 1, 2, 6, 17, 23) |
| Output switch SPI | LPSPI3 / 4 / 5 | `nxp,lpspi` | Upstream; native PCS0 chip selects |
| Output switch device | TPS2HCS08A-Q1 × 3 | none | **Out-of-tree driver to write**, three instances |
| Log flash | LPSPI2 + IS25LP032D | `nxp,lpspi` + `jedec,spi-nor` | Upstream (FCB, NVS) |
| Telemetry I²C | LPI2C0 | `nxp,lpi2c` | Upstream |
| Total-rail monitor | INA228A-Q1 | `ti,ina228` | Upstream |
| Board temperature | TMP175-Q1 | `lm75` (register-compatible) | Upstream driver; the 12-bit resolution setting is to be confirmed at GATE-FW-02 |
| NTC inputs, SNS, BATT_MON | ADC1, ADC2 (SAR) | `nxp,s32-adc-sar`, `ntc-thermistor` | Upstream. One `group-channel` per ADC instance: ADC1 and ADC2 use only precision (P) channels |
| Ethernet MAC + MDIO | EMAC, RMII | `nxp,s32-gmac`, `snps,dwmac-mdio` | Upstream |
| T1S PHY | LAN8670 rev. D0 | `microchip,t1s-phy` | Upstream; supports LAN8670/1/2 rev. C1, C2 and D0, with PLCA |
| Watchdog | SWT | `nxp,s32-swt` | Upstream (DEC-005) |
| Console | LPUART0 | `nxp,lpuart` | Upstream |
| DMA (optional) | eDMA | `nxp,mcux-edma` | Upstream |

## Consequences

- **Pin-plan rules** (applied in the review of 2026-10-30, recorded on the compute page):
  - Every interrupt input goes on a ball that the `nxp,siul2-gpio` EIRQ map lists, on its own EIRQ line.
  - Each ADC instance carries one channel group only.
  - SPI chip selects go on LPSPI PCS signals, so the driver can use native CS.
- **Driver work:** the TPS2HCS08A driver is the only device driver Node60 needs that Zephyr doesn't have. The TPS3702, LM74910H and termination relay need GPIO handling only.
- **Board port:** a Node60 board definition (devicetree, pinctrl, clock tree from the 16 MHz FXOSC) based on `mr_canhubk3`. GATE-FW-02 covers it.
- **No parked-state dependency:** the S32K3 Zephyr port has no standby implementation, and Node60 doesn't need one (DEC-004, DEC-007).
