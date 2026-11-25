---
id: DEC-029
title: Regulator power-good lines to the MCU, and a loop-test link on the 3.3 V buck
status: accepted
date: 2026-11-25
revision: B
page: subsystems/power
requirements: [REQ-PWR-001, REQ-PWR-003]
parts: [LMQ66430MC3RXBRQ1, TPS628502QDRLRQ1, S32K344EHT1MMMST]
gates: [GATE-MCU-01, GATE-SUP-02]
rejected:
  - option: Pull the PG lines up to VDDAU_AON
    reason: "VDDAU_AON stays on while parked, and U302 holds its PG low whenever it is disabled, so a 10 kΩ pull-up there would draw 330 µA from a parked budget of about 52 µA. It is also live before 3V3_MAIN, the supply of the MCU pads."
  - option: Pull U302's PG up to its VCC pin
    reason: "TI allows it, but VCC is up before 3V3_MAIN and overshoots at start-up (SNVSBV1F, 7.3.4), so the line would drive an MCU pad whose supply is not there yet."
  - option: 100 kΩ pull-ups
    reason: "Nothing is saved: a PG line is high in normal operation and the rail is off while parked. 10 kΩ keeps the drop from the pad's worst-case leakage (about 1.5 µA) at 15 mV and is the value the other open-drain lines use."
  - option: Wire a PG line into RESET_L
    reason: "Not asked for. RESET_L stays with the TPS3702 window supervisor, whose thresholds are tighter than either PG window."
---

## Context

Both buck regulators have an open-drain power-good output that Rev A left unconnected, and the 3.3 V buck had no way to measure its control loop. On 2026-11-25 the user asked for a 0 Ω resistor in U302's feedback node, so the loop can be measured by fitting 10 Ω and injecting across it, and for the two PG outputs to go to the MCU with test points, after checking that this causes no leakage or sequencing problem.

## Decision

**U302's VOUT/FB pin reaches the output through a 0 Ω link, R309. Both PG outputs go to MCU inputs, each with a 10 kΩ pull-up to `3V3_MAIN` and a test point.**

| Net | From | To | Pull-up | Test point |
|---|---|---|---|---|
| `3V3_MAIN_FB` | U302 pin 11 (VOUT/FB) | R309 0 Ω to `3V3_MAIN_REG` | | |
| `3V3_MAIN_PG` | U302 pin 14 (PG) | U401 U1 (PTB21), GPIO input | R310 10 kΩ | TP309 |
| `1V5_CORE_PG` | U303 pin 6 (PG) | U401 T17 (PTC10), GPIO input | R311 10 kΩ | TP310 |

High means the rail is in regulation.

## Why

**Loop-test link.** U302 is the fixed 3.3 V variant, so its feedback divider is inside the part and VOUT/FB is the top of that divider. The only place to break the loop is between the output capacitors and that pin. TI asks for a Bode plot of every design before production (SNVSBV1F, 8.2.1.2.4).

**No leakage path.** Both pull-ups go to `3V3_MAIN`, which is the supply of the MCU's pads (VDD_HV_A and VDD_HV_B) and U303's input. A PG line can therefore never sit above its pad's supply, and U303's PG stays inside its limit of VIN + 0.3 V (SLUSDM0N, 6.1). While the node is parked `3V3_MAIN` is off, so the pull-ups carry nothing and the parked budget is unchanged, although U302 holds its PG low the whole time (it does so whenever EN is low and VIN is above 1.5 V).

**No sequencing effect.** The lines are inputs only: the power-up order is still INH, then U302, then U303 through the EN divider. Both MCU pads are high impedance during and after every kind of reset (NXP IOMUX table, pad state columns). When a line is low it sinks 0.33 mA, against limits of 4 mA (U302) and 2 mA (U303).

**Ball choice.** U1 is the corner of U401 nearest U302 and T17 is on the edge facing U303; both were unconnected, with no copper beside them on the board. Each is in Zephyr's EIRQ table on a line no other Node60 interrupt uses (8 and 18), so firmware can take an edge interrupt later without a hardware change. They are plain GPIO inputs in the pin plan for now.

## Limits

- **`3V3_MAIN_PG` is not a brown-out warning.** U302 pulls PG low below 89 to 94.2 % of 3.3 V (2.94 to 3.11 V); the TPS3702 resets the MCU at 3.10 V, at or before that point. Firmware can see this line low only on overvoltage (PG trips at 104 to 111 %, the supervisor at 3.50 V) or at start-up. Its main use is on the bench, at TP309.
- **`1V5_CORE_PG` is informative.** U303 pulls PG low below 87 to 93 % or above 107 to 113 % of 1.5 V, during soft start and in thermal shutdown. With its input under 2 V the pin is undefined and may read high through the pull-up.
- **The 10 Ω resistor shifts the output.** On the fixed variant VOUT/FB also feeds the internal LDO that powers the control circuits once the output is above 3.15 V (7.3.4). The data sheet gives that current only when not switching (4.2 µA typical), so the shift at 2.2 MHz is unknown until measured: every 1 mA through 10 Ω raises `3V3_MAIN` by 10 mV. Check the rail against the supervisor's 3.50 V limit before trusting a measurement, and fit 0 Ω again afterwards.
- **Measure in PWM.** MODE/SYNC is grounded (auto mode), so at light load the part runs in PFM and a Bode plot means nothing there. Load the rail above the PFM range.

## Consequences

- Five parts are added: R309 (0 Ω 0402, as R301), R310 and R311 (10 kΩ 0402, as R213) and the pad test points TP309 and TP310.
- The PCB must be updated from the schematic. R309 goes close to U302 pin 11, on the sense trace, away from the switch node (TI layout guidelines). `3V3_MAIN_PG` runs about 80 mm from U302 to U401, round the T1S zone.
- GATE-MCU-01 is open for U1 and T17 as well as DEC-028's three balls. The IOMUX, IBIS and BSDL checks passed for all five; the user's sign-off is outstanding.
- Firmware: two GPIO inputs. What it does when `1V5_CORE_PG` falls (log, or shed loads) is not decided here.
- No test point was added on `3V3_MAIN_FB`: the injection transformer and both probes go on R309's pads.
