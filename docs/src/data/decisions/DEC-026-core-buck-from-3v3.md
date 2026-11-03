---
id: DEC-026
title: 1.5 V core buck from 3V3_MAIN (TPS628502-Q1)
status: accepted
date: 2026-11-02
revision: B
page: subsystems/power
requirements: [REQ-PWR-001, REQ-QUAL-001]
parts: [TPS628502QDRLRQ1, LMQ66430MC3RXBRQ1]
gates: [GATE-NET-01]
rejected:
  - option: Keep U303 as an LMQ66430-Q1 on the battery and let the emissions test decide
    reason: "At a 13.5 V battery the 1.5 V buck needs about 50 ns on-time, below the LMQ66430's 65–75 ns minimum, so it folds back to about 1.5–1.7 MHz: inside the AM broadcast band (0.53–1.71 MHz), with spread spectrum switched off while folded back (TI SNVSBV1F §6.5, §7.3.7)."
  - option: Feed the LMQ66430-Q1 from 3V3_MAIN
    reason: "The LMQ66430 needs 3.6 V on VIN to start (SNVSBV1F §6.3, input voltage range for start-up)."
  - option: LDO from 3V3_MAIN
    reason: "1.8 V × 245 mA is about 0.44 W; at a 125 °C ambient a 50 °C/W package reaches about 147 °C, against a 150 °C junction limit."
  - option: TPS628122GQWRWYRQ1 (TPS6281x-Q1, fixed 1.5 V, 2 A)
    reason: "Fits, and needs no divider, but DigiKey sells it only on full reels (2026-11-02) and its 3 × 2 mm VQFN-HR is harder to rework than SOT-583."
  - option: MAX20004E (ADI)
    reason: "3.5 V minimum input, above the 3.3 V rail."
  - option: TPS62903-Q1
    reason: "3.0 V minimum input, with the rail's supervisor floor at 3.10 V; no DigiKey stock on 2026-11-02."
  - option: MPQ2143-AEC1 (MPS)
    reason: "DigiKey status Not for new designs (2026-11-02)."
---

## Context

DEC-004 made the power tree from two LMQ66430-Q1 bucks on VBAT_FILT, the 3.3 V one (U302) enabled by the PHY's INH and the 1.5 V one (U303) chained after it. The MC3 variant switches at a fixed 2.2 MHz, above the AM broadcast band. A ripple check of 1V5_CORE on 2026-11-02 (after placement run 2026-11-02-bars) found that U303 cannot hold 2.2 MHz: making 1.5 V from a 13.5 V battery needs an on-time of about 50 ns, below the LMQ66430's 65–75 ns minimum, so the device lowers its frequency to about 1.5–1.7 MHz, into the AM band, and turns spread spectrum off while it does (TI LMQ66430-Q1 data sheet SNVSBV1F). It holds 2.2 MHz only below about 9 V input. U302 (3.3 V out) keeps 2.2 MHz up to about 20 V and reaches the AM band only above about 26 V, during transients.

The ripple itself was within NXP's window: V15 must stay within 1.425–1.65 V (S32K3xx data sheet Rev. 14, operating conditions), and the worst-case DC set point plus ripple left about 42 mV at the bottom and 72 mV at the top.

## Decision

- **U303 becomes a TI TPS628502QDRLRQ1** (TPS62850x-Q1, 2.7–6 V in, 2 A, AEC-Q100 Grade 1, SOT-583; data sheet SLUSDM0N, January 2026), **fed from 3V3_MAIN** (user, 2026-11-02).
- At 3.3 V in and 1.5 V out the duty cycle is about 45 %, far from its 50 ns maximum minimum on-time, so it **holds a fixed 2.25 MHz with spread spectrum on**: COMP/FSET tied to VIN (Table 8-1: internal 2.25 MHz, compensation setting 2, spread spectrum enabled, at least 18 µF effective on the output).
- **MODE/SYNC tied high: forced PWM.** In auto mode the light-load pulses have no fixed frequency and could fall back into the AM band; the rail is off while the node is parked, so the light-load efficiency forced PWM costs does not reach the parked budget.
- **Parts around it** (TI's Table 9-2 for 1.5 V): 76.8 kΩ / 51 kΩ divider with a 10 pF feed-forward capacitor (FB regulates to 0.6 V); a Würth 744383560056HT 0.56 µH inductor (WE-MAPI 4020 HT, −55…150 °C, the same 4020 package as the 1.0 µH it replaces; TI's inductor table lists 0.56 µH); 10 µF and 100 nF at VIN; the existing 3 × 22 µF and 100 nF at the output.
- **EN stays chained from 3V3_MAIN** through the existing 100 kΩ / 100 kΩ divider: 1.65 V on EN once 3.3 V is up, against a 1.05–1.15 V rising threshold; the device's own UVLO covers the ramp.
- **U302 stays an LMQ66430-Q1** on VBAT_FILT, and now also supplies U303.

## Consequences

- **U302's load** grows by about half the 1.5 V current (1.5 V / 3.3 V at about 85 % efficiency): at the S32K344's worst-case 245 mA V15 current (125 °C, dual core at 160 MHz; S32K3xx data sheet Rev. 14, Table 17), about 130 mA more, well inside its 3 A.
- **VBAT_FILT** feeds only U302 now; L201/C208 (still to be chosen with the emissions test) see less load.
- **Wake timing (GATE-NET-01):** the TPS628502 soft-starts in 1 ms from EN, so 1V5_CORE follows 3V3_MAIN sooner than with the LMQ66430's ramp. Measure the whole chain at GATE-NET-01 as before.
- **Opening R302** (3V3_MAIN's 0 Ω debug link) now also removes 1V5_CORE's input.
- **Board:** U303's cell is redrawn around the new part (placement decision D06 approved the LMQ66430 cell); its hot loop is checked against the TPS62850x-Q1 data sheet's layout section.
- **Second source:** TPS628501QDRLRQ1 (1 A) and TPS628503QDRLRQ1 (3 A) are pin-compatible in the same package. No other maker's drop-in was found.
