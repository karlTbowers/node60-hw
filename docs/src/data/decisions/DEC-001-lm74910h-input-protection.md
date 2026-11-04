---
id: DEC-001
title: LM74910H-Q1 input protection with shared RSENSE
status: accepted
date: 2026-11-03
revision: B
page: subsystems/power
requirements: [REQ-PWR-002, REQ-PWR-001, REQ-MON-004]
parts: [LM74910HQRGERQ1, BVR-Z-R0003-1.0, CSS2725FTL250, TBD-OCP-NETWORK]
gates: [GATE-PWR-01, GATE-MON-01]
rejected:
  - option: LM74800-Q1 (LM74800QDRRRQ1) with a standalone 0.5 mΩ shunt
    outcome: replaced
    reason: The prior architecture had no input-rail overcurrent protection, and a separate measurement shunt doubled shunt heat at 60 A.
  - option: LM74900-Q1
    reason: Saves about $1 at 1,000 pieces but latches off after SLEEP-mode overcurrent instead of auto-retrying. That is the wrong trade for a battery-parked node whose MCU may be asleep when the fault occurs.
  - option: Stackpole CSS2725FTL250 (0.25 mΩ, 2-terminal)
    outcome: replaced
    reason: "Rev. A's RSENSE. A 2-terminal part makes the Kelvin taps depend on where the layout lands them on the pads. Replaced in rev. B by the 4-terminal BVR-Z-R0003-1.0 (decision D14-1, user, 2026-11-03); no 0.25 mΩ 4-terminal code exists."
  - option: 0.2 mΩ 4-terminal shunt (BVR-Z-R0002-1.0, BVB-Z-R0002-1.0)
    reason: "Even with RISCP = 0 Ω the fast short-circuit trip sits at 20 mV / 0.2 mΩ = 100 A typical (89–115 A), against 80 A today. Rejected at D14-1 (2026-11-03)."
---

## Context

The 60 A-capable VBAT path needs reverse-battery blocking, overvoltage disconnect, overcurrent protection, and a total-current measurement. The prior architecture used LM74800-Q1 plus a standalone 0.5 mΩ shunt and had no input-rail overcurrent protection.

## Decision

Use **LM74910HQRGERQ1** to control the DGATE ideal-diode MOSFET bank and the HGATE disconnect MOSFET bank. One shared 0.3 mΩ, 1%, AEC-Q200, 4-terminal RSENSE (Isabellenhütte **BVR-Z-R0003-1.0**, R201) sits between the two FET stages; LM74910H and INA228A-Q1 connect to its two sense terminals with independent pairs.

- Circuit breaker OCP 75 A: R(ILIM) = 12 × RSET / (RSENSE × ILIM) = 12 × 49.9 Ω / (0.3 mΩ × 26.7 kΩ) = 74.8 A, with R(ILIM) 26.7 kΩ 1 % (R208) and RSET 49.9 Ω (R209).
- Fast SCP 80 A typical: RISCP 383 Ω 1 % (R210) shifts the trip to 10.5 µA × 383 Ω + 20 mV = 24.0 mV. Over the data sheet limits (17.86–23 mV, 9.3–12 µA bias) that is 21.4–27.6 mV, **71.4–92 A, the same window** as rev. A's 0 Ω on 0.25 mΩ.
- TMR 68 nF for an ≈1 ms starting-point breaker delay (unchanged).
- FLT to S32K344; SLEEP OCP auto-retry. IMON not populated while INA228 is fitted.

## Why

One resistor now serves both protection and precise measurement, cutting shunt heat in half at 60 A. More importantly, LM74910H adds a programmable breaker, fast short-circuit trip, separate UVLO, FLT warning, and SLEEP-mode OCP auto-retry. LM74910H adds about $1.70 at 1,000 pieces versus the prior controller/shunt pair.

## Consequences

- BATT_MON moves to the LM74910H SW-pin OV/UV divider. The OV threshold is 0.6 V rather than the LM74800’s 1.23 V, so all divider values are recalculated at schematic review.
- MOSFETs (80–100 V AEC-Q101) are chosen after surge/thermal calculation.
- LM74910HQRGERQ1 carries a 26-week manufacturer lead if distributor stock is depleted.

## Rev. B: 0.3 mΩ 4-terminal RSENSE (2026-11-03)

Decision D14-1 A (user, 2026-11-03) replaced rev. A's 2-terminal 0.25 mΩ CSS2725FTL250 with the 4-terminal 0.3 mΩ **BVR-Z-R0003-1.0** (Isabellenhütte ISA-WELD, 4026, 10.1 × 6.6 mm, ±1 %, TCR 0 ±20 ppm/K, 5 W above 100 °C terminal temperature, AEC-Q200). No 0.25 mΩ 4-terminal code exists, so the thresholds were rescaled (LM74910H-Q1 SNOSDE6C equations 3 and 6):

| | Rev. A (0.25 mΩ) | Rev. B (0.3 mΩ) |
|---|---|---|
| R(ILIM), R208 | 32 kΩ 0.1 % (TNPW0603) | 26.7 kΩ 1 % (AC0402FR-0726K7L) |
| Breaker | 74.9 A | 74.8 A |
| RISCP, R210 | 0 Ω | 383 Ω 1 % (AC0402FR-07383RL) |
| Fast SCP | 20 mV = 80 A (71.4–92 A) | 24.0 mV = 80 A (71.4–92 A) |
| RSET, CTMR | 49.9 Ω, 68 nF | unchanged |
| At 60 A | 15 mV, 0.9 W | 18 mV, 1.08 W |

- **Sense nets.** The shunt's sense terminals are their own nets: pad 2 (S1, on the VBAT_D side) is `RS_SENSE_P`, pad 3 (S2) is `RS_SENSE_N`. As in the data sheet's Figures 8-7 and 9-1, RSET and RISCP go to the VS side of the shunt (`RS_SENSE_P`) and CS− to the other side (`RS_SENSE_N`); the CS+ and ISCP filter caps (C212, C213) return to CS−, so `RS_SENSE_N`. VS and C stay on the force net VBAT_D. INA228 IN+/IN− take `RS_SENSE_P`/`RS_SENSE_N`.
- **Rejected:** 0.2 mΩ moves the fast trip to 100 A even with RISCP = 0 Ω.
- **Supply:** DigiKey had 5,311 BVR-Z-R0003-1.0 at $5.20 each (2026-11-03); Mouser does not list it. AC0402FR-07383RL had no stock at DigiKey or Mouser that day (DigiKey sells only full reels).

