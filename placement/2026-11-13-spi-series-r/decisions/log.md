# Decisions, SPI series resistors (2026-11-13)

Asked by the user on 2026-11-13: "kick off another session to add the series resistors on the SPI bus"
(the kicad-happy review's open note under CK-002: no series resistor on any SPI clock). Taken by Claude from the
sources below; none changes a `DEC-*` or anything `CLAUDE.md` records as decided, no part moved, and
`node60.kicad_dru` and `node60.kicad_pro` are untouched. Each entry says how to undo it. S03 is open and is the
user's: its page is `decisions/S03-sdo-resistor.json`.

**S01. Which lines get a resistor: all four lines of each output-switch bus, and the log flash's SCK. 13 parts.**
- The DropOut handbook (v0.10.0, chapter 05) has no rule on series resistors, so nothing here disagrees with it.
- TI, TPS2HCS08-Q1 data sheet SLVSHR0 (May 2025), Figure 9-1 (system diagram, TPS2HCS08A-Q1) draws a resistor
  `RSPI` in each of CSN, SDI and SCLK and "RSPI or (RSDO if last in daisy chain)" in SDO. Table 9-1, Recommended
  External Components: `RSPI` 22 Ω typical, "(Optional) For EMI or other transient limits on the SPI pins";
  `RSDO` 768 Ω (S03). The board's switch sheet already follows that table for every other part (RVDD, CVDD,
  RPROT, RPU, RSNS, CSNS, COUT); RSPI was the one left out. So the switch buses get TI's four, not SCK alone.
- NXP: the S32K3xx Hardware Design Guidelines (Rev. E2) ask for series termination on the Ethernet MII/RMII
  lines only (33 to 50 Ω) and say nothing for LPSPI. NXP's S32K3xx data sheet (Rev. 14) gives its LPSPI timing
  "with ... pad configured DSE = 1, SRC = 0" (§12.1); at that setting its 3.3 V pads switch in 0.8 to 6.6 ns
  (medium pad, 25 pF) or 1.9 to 10 ns (standard-plus) (§7, GPIO output AC specification). `mcu-config.yaml`
  does not set the SPI pads' drive yet; it now notes NXP's condition.
- ISSI's IS25LP032D data sheet says nothing about series resistors. The flash bus is 41 to 54 mm long, a quarter
  of the shortest switch bus. Its SCK gets a resistor (the clock is the line that toggles every bit, and the
  task's minimum); MOSI, MISO and CS_L do not: no source asks for them.
- Every bus is point to point (DEC-018; the flash alone on LPSPI2), so each resistor is a source resistor: at
  U401 on SCK, MOSI and CS_L (R409 to R418, MCU sheet, p4), at the switch's SDO pin on MISO (R608, R708, R808,
  one symbol on the output-switch sheet, p6 to p8).
Undo: `git revert` the commit; or leave a line out by deleting its entry from `plan.json` and its symbol.

**S02. Value and part: 33 Ω, Yageo AC0402JR-0733RL (0402, ±5 %, AEC-Q200, −55 to +155 °C), already in the
library and on the board as R503/R504.**
TI's typical RSPI is 22 Ω. TI gives the bus's timing with a 220 Ω protection resistor (§6.6: "CSDO = 30 pF, IO
protection resistor 0.22 kΩ"), so 22 to 220 Ω is inside what TI specifies. 33 Ω is the board's existing series
value and needs no new library part; 22 Ω (AC0402JR-0722RL) is not in the library. On the 0.15 mm lines the
MCU's pad already has 30 to 100 Ω of its own at DSE = 1 (ROUT_33_M, data sheet §7), so neither value is a
matched termination: the resistor limits edge current and what a transient on the line can push into a pin.
RC cost: 33 Ω into about 35 pF (212 mm of line, a pin, two test points; estimated) is 1.2 ns.
Undo: change the `Value`/MPN of the 13 symbols (and add the 22 Ω part to the library first); same footprint.

**S03. OPEN, the user's: SDO's resistor, 33 Ω (as fitted) or TI's RSDO 768 Ω.**
TI's Table 9-1 gives RSDO 768 Ω, "Higher values to increase the total resistance to MCU VDD to 768 Ω for ground
loss detection", and Table 8-5 lists "Loss of GND: protection Y, with RSDO ≥ 768 Ω". Each Node60 switch is the
last (only) device on its bus, so the note applies to R608/R708/R808. 768 Ω into the line's capacitance slows
SDO: about 5 MHz SPI clock at most on the longest bus instead of 8. Fitted now: 33 Ω. Same footprint either way.
Page: `decisions/S03-sdo-resistor.json` (published as a private Artifact; link in REPORT.md).
Undo / change: the `Value` and MPN of one symbol on the output-switch sheet (a 768 Ω 0402 goes into the library).

**S04. Net names.** The line keeps its name, its sheet pin and its test points (`SPI4_SWITCH1_SCK`, ...). The
short net from the driver to the resistor is new: `<line>_MCU` at U401 (`SPI4_SWITCH1_SCK_MCU`), `SW_SDO` at the
switch (local to each placed sheet, like `SW_SNS` and `SW_DI`). `mcu-config.yaml` is keyed by the ball's net, so
its ten entries are renamed to `<line>_MCU`; `mcu-pins.json` is regenerated. U401's pin plan (ball to function)
is unchanged, so GATE-MCU-01 is not re-run.
Undo: with S01.

**S05. Where each stands: on B.Cu, in the first free spot along its line from the driver, before the line's
first test point; no other part moved.** `plan.py` walks each route from the driver's pad, takes 0.9 mm out of
it, puts the 0402 in a free spot within reach (pads and courtyard clear), and has the routing run's
`mini_route.py` (plain mode) join the two loose ends to the pads; the best cut by copper length wins. Result
(`checks/measure.md`): the three at the switches 1.5 to 4.8 mm from the SDO pin; at U401 9.9 to 20.5 mm of
copper from the ball, because the balls are two to five rows inside the BGA and B.Cu under and beside it is
taken. 20.5 mm is 0.14 ns one way, against a fastest pad edge of 0.8 ns: electrically at the driver.
- R418 (flash SCK, 20.5 mm): the line runs 17 mm on In2 under U401 from ball D2 on the west side before it can
  come up. Its test point TP407 hung on a branch that left the line there; the branch was rebuilt so the
  resistor sits in it and TP407 stays on the line (via to pin 1, pin 2 to TP407, the line re-joined to pin 2).
- R414 (SPI5 CS_L): planned last, with a wider reach, before the branch to TP416.
- Vias stand in ten pads (R410 to R414, R416); every via on the board is filled and capped (CLAUDE.md, via
  protection), as the in-pad vias of D501/D504 and the switches' VBB pads already rely on.
- 26 reference texts were placed again (`silk_refs.txt`): the 13 new ones and 13 whose old spot a new pad took.
Undo: `plan.json` is the record; `build.sh` rebuilds the board from main's (`85a8ca5`) with it.
