# Decisions, kicad-happy fixes (2026-11-13)

Taken by Claude while working through `reviews/2026-11-12-kicad-happy/REPORT.md`; none changes a `DEC-*` or
anything `CLAUDE.md` records as decided, and `node60.kicad_dru` and `node60.kicad_pro` are untouched. Each
entry says how to undo it. `build.sh` rebuilds the board from main's (`264352a`) out of `specs/`; leaving a
spec out leaves its step out.

**F01. U501's pad vias (N1): nine GND vias, 3 × 3 at 1.20 mm pitch, 0.33 mm hole, 0.60 mm pad.**
Source: Microchip LAN8670/1/2 data sheet DS60001573K (Oct 2025). §6.4 Power Connectivity, p. 230: "The exposed
ground pad (ePAD) of the package serves as the primary ground connection of the device and must be adequately
connected to the PCB ground plane through an array of vias as specified in the Packaging Information section."
§8.1, p. 267, recommended land pattern, Microchip Technology Drawing C04-2500 Rev B: a 3 × 3 array in the
3.50 mm centre pad, Thermal Via Diameter V 0.33 mm, Thermal Via Pitch EV 1.20 mm, note 2 "thermal vias, if
used, should be filled or tented". The board's vias are filled and capped. No LAN867x layout guide or
evaluation-board layout was found that says more.
- Hole 0.33 mm as drawn. It is not one of the board's presets (0.60/0.30 is the nearest); pad 0.60 mm gives a
  0.135 mm ring.
- The array stands **0.10 mm north of the pad's centre** (rows y 42.25, 43.45, 44.65; columns x 154.8, 156.0,
  157.2): centred, the south row's pads would be 0.71 mm from T1S_N's trunk track on F.Cu (rule: 0.75) and
  0.05 mm from the trunk corridor's edge. Now 0.81 mm and 0.15 mm. Every via is inside the pad (edges 0.15 mm
  or more from the pad's edge).
- Three locked tracks ran where vias go and were re-laid between the rows, locked again: RMII0_T1S_TXD1 on
  F.Cu from y 43.3 to y 44.05 (+0.6 mm, 311 to 315 ps), MDIO0_T1S_MDC on F.Cu from its diagonal to a path
  between the north row's middle and east vias (+0.4 mm), RMII0_T1S_TX_EN on In2 from y 42.2 to y 42.85
  (+0.5 mm, 403 to 407 ps). RMII windows as before: TX setup 0.601, TX hold 0.69, RX setup 3.319, RX hold
  1.367 ns.
- In3's 3V3 plane under U501 loses 5.8 mm² to the nine antipads and stays one piece.
Undo: leave `specs/n1_u501.json` out of `build.sh` (its `delete` and `tracks` lists are the three tracks before
and after).

**F02. Leftovers deleted (N3), and every exact duplicate on the board.** The two 0.475 mm pin stubs of MDC and
MDIO at U501 (locked, from the time their test points stood there) and a 0.25 mm MDC piece lying on its own
track. `dedupe_tracks.py` then found 32 items lying exactly on another of the same net, layer, width and ends:
the T1S_REFCLK via at (157.0, 47.35) and its two tracks (B.Cu and In2), two 3V3 tracks at U501 pin 29, three
SW_VDD tracks of outputs 3-4, and 24 locked GND stubs (22 pieces of the pad stubs near (151.5, 40.8), one at
(158.96, 47.6), one at (156.98, 108.9)). One of each pair stays, the locked one. Connectivity as before (0
unconnected); REF_CLK's path length unchanged (34.6 mm to the PHY). `power_shapes.json` still lists some GND
stubs twice; harmless, since the spec is not redrawn on a routed board.
Undo: none needed (the copper is identical).

**F03. Via sizes (N2).** Of the 213 vias of 0.35/0.20 mm, 129 stood outside U401's body (the review counted
124). `n2_enlarge.py` set them all to 0.45/0.25 and let KiCad's DRC step down every via named in an error;
`n2_retry.py` then tried each shrunken one again alone. A via that fits neither goes to **0.40/0.20 mm where
that fits**: it has the same 0.10 mm ring as the board's default via, so it leaves the 0.075 mm question too
(not in the task's wording, which named 0.45/0.25 only).
- 59 are 0.45/0.25 now, 22 are 0.40/0.20, 48 stay 0.35/0.20 (`n2_vias.json` lists all 129 with reasons).
- 24 of the 48 have no room at either size: 9 round U501 and in the T1S zone, 4 at U401's east and south edge
  (SPI escapes), 8 north of the power band (the switch 2 SPI and fault lines along y 62 to 66, the lane tops
  at y 70, RXD0 at (181.7, 34.7)), 2 in the power band (GND at (159.1, 80.85), VBAT_PROT at (161.41, 71.7)),
  1 at the west output cell.
- **24 of the 48 fit but were left small: the vias in the middle of the power band (x 130-180, y > 70.5).**
  Growing them widens their antipads in the battery pours and planes: VBAT_D 0.298 -> 0.299 mΩ (outer layers
  0.717 -> 0.720), OUT3 1.579 -> 1.580 mΩ, VBAT_PROT to U701 10.58 -> 10.59 mV at 20 A. The task's rule was
  that no supply path gets worse, so they stay; `specs/n2_band_option.json` applies them
  (`apply_fix.py BOARD specs/n2_band_option.json OUT`, DRC clean) if the user prefers the ring. The enlarged
  vias in the west and east output cells cost nothing measurable and are in.
- 24 supply vias that `power_shapes.json` lists changed size; their points moved to groups of the new size.
Undo: leave `specs/n2_resize.json` out of `build.sh`.

**F04. Return vias and stitching (N6): 363 GND vias, `stitch.py`.** Rules of a legal site are in the script's
header: wider clearances than the rule file asks (0.20 mm stitching, 0.16 mm return vias; 0.85 mm from T1S
copper), never in a pad, never through a battery pour or plane on any layer (so nothing in the power band and
nothing on the In3 VBAT_PROT fingers to U301 and L201 or the In2 finger `PWR_VBAT_IN_U201_In2`), not in the
trunk corridor, not under Y401/Y501, not under U401; 3V3_MAIN on In3 is the one plane a via may pass through,
and a stitching via only where that plane is whole for 0.75 mm round it.
- 130 return vias: for each signal via with no GND via within 1.0 mm, the nearest legal site within 1.0 mm
  (0.45/0.25, else 0.40/0.20: 8 of them), else within 1.5 mm (21). Fast nets first: of the 106 vias of RMII,
  REF_CLK, oscillator, MDIO and SPI nets, 5 had one, 60 got one, 41 have no site (20 under U401, 7 in the power
  band, 14 hemmed in; `specs/n6_stitch.json` `no_site` lists every one). Buses and reset: 13 of 28. Other
  signals: 57 of 152 (most of the rest are in the power band).
- 233 stitching vias: a 5 mm grid, one via at the legal site nearest each grid point that had no GND via within
  2.5 mm.
- **The rule proofs' test ground (x 93.5-102.5, y 34.5-42.5) is left without stitching**: `prove_rules.py`
  plants its test tracks there and needs copper-free ground (a first pass with four vias there failed one
  proof, 38 of 39).
- No T1S vias got return vias (the 0.75 mm rule leaves no site within 1.0 mm).
- Planes: In1, In2, In3 and In4 keep their piece counts (`checks/plane_pieces.txt`). In3's 3V3 plane loses
  174 mm² of 15,745 over the whole run (1.1 %). The outer GND pours gain 230 mm² and 20 pieces: patches
  KiCad used to drop as islands now have a via. GND vias on the board 446 -> 818.
- All 372 new GND vias (with F01's nine) are in `power_shapes.json` as one group and locked.
Undo: leave `specs/n6_stitch.json` out of `build.sh`.

**F05. Reference text (N4): `silk_place.py`.** Each reference goes to the free spot nearest its part where it
touches no solder-mask opening, no silkscreen graphic, no other reference, stays 0.5 mm inside the edge and
lies **under no part** (handbook chapter 05: readable after assembly). 1.0 mm high, 0.15 mm stroke, flat or
turned 90 degrees. No part moved, no reference hidden.
- DRC silk warnings 377 -> 19. The 19 are footprint graphics, not text: 16 `silk_edge_clearance` (the body
  outlines of J903 to J909 and J912 pass the board edge, as the connectors do) and 3 `silk_over_copper` (the
  pin 1 marker of U601/U701/U801 reaches about 0.13 mm into the mask opening of R605/R705/R805 pad 2).
- 16 references stand 3 to 6.2 mm from their part, where nothing nearer is free: R210, U201, C202, C213, R202,
  C211, R209, R203, U202, R208, R501, C214, R301, C302, C212, U301 (the power entry's U201/U202 column and the
  parts beside U501).
Undo: leave `specs/silk_place.json` out of `build.sh`.

**F06. L302 (N5): not moved.** Its courtyard is 0.96 mm from the north edge, its pads 1.63 mm (copper-to-edge
rule 0.3 mm), the nearest edge-ring vias (214.48, 31.0) and (219.48, 31.0) are 0.40 mm clear of pad 2 and DRC
is clean. Nothing in `enclosure_geometry.py` puts a ledge or rail on that edge: the removable north panel's inner face
stands 0.5 mm off the board (`back_gap`), so L302's courtyard is 1.46 mm from it. Nothing is violated; the analyzer's 1.0 mm is its own limit.

**F07. Datasheets.** DigiKey credentials are set on this workstation, so `sync_datasheets_digikey.py` fetched
59 PDFs into `datasheets/` (80 MB; ignored by git: third-party documents). The analyzers' structured
extraction (`datasheets/extracted/`, the kicad-happy `datasheets` skill's scout, plan and merge pipeline with
one model task per part) was not run: it is a job of its own. Checked by hand from the PDFs instead, for the
review's two "from memory" statements: LM74910H-Q1 (SNOSDE6C, pin table) "RTN, Thermal Pad: Leave exposed pad
floating. Do not connect to GND plane", as the schematic has it; TPS62850x-Q1 feedback voltage 0.6 V, so
U303's 76.8 kΩ / 51 kΩ gives 1.504 V.

**F08. JLCPCB pad spacing.** The review left SMD pad-to-pad spacing between nets unchecked (JLCPCB 0.15 mm,
board clearance 0.10 mm). Measured from the pad polygons: no two pads of different nets are closer than
0.15 mm on either side.
