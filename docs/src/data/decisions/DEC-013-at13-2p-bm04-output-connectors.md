---
id: DEC-013
title: Amphenol Sine AT13-2P-BM04 headers for the six outputs, replacing the MX150 plan
status: accepted
date: 2026-10-25
revision: B
page: subsystems/harness
requirements: [REQ-OUT-001, REQ-OUT-002, REQ-NET-001]
parts: [AT13-2P-BM04]
gates: [GATE-THM-01, GATE-THM-02, GATE-BOM-01]
rejected:
  - option: Molex MX150 sealed connector sets (Rev A plan, TBD-MX150-SETS)
    reason: The user chose DEUTSCH-style DT headers on 2026-10-22, a connector family they have used in an earlier design. No MX150 housing, terminal or seal had been chosen, so nothing released changes.
  - option: TE DEUTSCH DT13-2P (DEC-013 rev. A primary, 2026-10-22)
    reason: The user replaced it with Amphenol Sine AT13-2P-BM04 on 2026-10-25. TE publishes no derating curve and lists the PCB header's ingress protection as "Not Tested"; Amphenol rates the AT13 for 13 A across −55 to +125 °C and IP67 mated, potted, at a lower price. DT13-2P stays in the library.
  - option: HISENG CH-AK-DT13-02 (Alibaba) and Jorch DT13-2P (AliExpress), rev. A alternates
    reason: Copies of the DT13-2P, on its footprint, with no authorized distributor, drawing, or qualification data. They were alternates to the TE part and lapse with it. They stay in the library.
  - option: OUTx on both pins of each header, loads returning to vehicle ground
    reason: Halves the current per contact (about 5 A) and keeps load current out of the node ground. The user chose a local ground return on pin 2 instead (2026-10-22). Paralleled pins would also need two wires or a splice per output, and open-load detection cannot see one broken contact.
---

## Context

Rev A of the architecture planned "MX150 sealed" output connectors, 10 A each with 14 AWG minimum wire (REQ-OUT-002), but never chose a part (`TBD-MX150-SETS`). On 2026-10-22 the user chose DEUTSCH-style DT headers instead, and DEC-013 rev. A selected the TE DT13-2P with two marketplace copies as alternates. On 2026-10-25 the user replaced the TE part with **Amphenol Sine Systems AT13-2P-BM04**, a BoardLock AT13 header that Amphenol sells as the DT13-2P equivalent and that mates the AT06-2S plug (Amphenol's DT06-2S equivalent). This is revision B.

The output target is unchanged: six independently switched outputs (REQ-OUT-001), 10 A continuous each (REQ-OUT-002), −40 to +125 °C ambient (REQ-QUAL-001 is the board-wide grade target).

## Decision

**One Amphenol Sine AT13-2P-BM04 per output, six per board** (J904 to J909 on the schematic).

- **AT13-2P-BM04:** BoardLock AT13 2-position 90° flange-mount PCB receptacle, grey. It has tin-plated pin contacts, self-threading screw bosses, a flange gasket, and a potted rear reservoir. It mates the AT06-2S plug, which takes size 16 sockets for 14 to 20 AWG.
  - Ratings (drawing C-AT13-2P-BMXX rev. A2; BoardLock flyer, updated 09-2026, p. 2): **13 A, 250 V, −55 to +125 °C "at rated current"**, **IP67 mated**, 100 mating cycles. The potted versions are specified for up to 5 psi.
  - PCB layout (drawing, "recommended PCB layout"): two Ø1.80 +0.1/−0 pin holes at **5.40 mm** pitch, and three Ø3.43 holes for #4-20 thread-forming screws from the solder side (0.68 to 1.13 N·m).
  - This is not TE's DT13-2P layout (5.46 mm pitch, Ø1.88 holes), so the header has its own footprint.
  - Library: `DropOut_Connector:AT13-2P-BM04`, footprint `DropOut_Connector_Amphenol:Amphenol_AT13-2P-BMxx_1x02_P5.40mm_Horizontal` (dropout-kicad-library PR #25).
- **No alternates selected.** The same drawing covers AT13-2P-BM01 to BM03 (gold or tin pins, with or without potting). BM03, the unpotted tin version, is the one Amphenol calls comparable to DT13-2P.

**Observed 2026-10-25, not quotes:**

| Part | Source | Price | Stock |
|---|---|---|---|
| AT13-2P-BM04 | DigiKey 889-3345-ND | $5.93 @1, $5.04 @10, $4.11 @180, $3.62 @1080 | 174 |
| AT13-2P-BM04 | Mouser 654-AT13-2P-BM04 | $5.41 @1, $5.04 @10, $4.11 @100, $3.26 @1080 | 129 |

Six headers cost about $36 per board at single quantity, or about $25 at 180.

## Pin assignment

**Pin 1 = OUTx, pin 2 = local ground return** (the user's decision, 2026-10-22, unchanged in rev. B). Each load gets a two-wire cable with its own return, and every output's load current comes back through the node.

- Each contact carries the full 10 A, which is 77 % of the 13 A rating.
- Each pin 2 connects to the power-entry ground/star region, not to the logic plane (system partitioning rule).

## Consequences

- **Current at +125 °C:** Amphenol rates the contact 13 A across −55 to +125 °C "at rated current", so 10 A at +125 °C ambient sits inside its rating. Amphenol publishes no temperature-rise data. GATE-THM-01 and GATE-THM-02 still measure contact temperature rise at 10 A with all six headers loaded. Both contacts of each header carry 10 A (output and return), so each header dissipates twice a single contact's heat.
- **60 A node ground return:** with every load returning through pin 2, up to 60 A (six outputs at 10 A) flows from the output headers into the power-entry ground/star region and out through the node's single ground conductor (REQ-NET-001).
  - The ground conductor, its input connector contacts, and the PCB ground path from the six headers to the star point must each carry 60 A continuous, matched to the battery feed. This is the harness page's "matched high-current return": no chassis-only return.
  - Load current must not cross the logic ground plane. Route each pin 2 return to the star region with the same copper and via treatment as its OUTx net.
  - The node's ground sits above vehicle ground by the drop along the ground conductor and its contacts at up to 60 A. The rest of the T1S segment sees that offset. Cover it in the six-channel assembly tests (ground offsets, verification step 15).
  - The ground conductor carries the same current as the battery feed, so size it and its contacts like the battery feed, including the worst fault current the source-end fuse lets through.
- **Wire gauge:** 14 AWG stays the minimum, the top of the AT06-2S range (14 to 20 AWG). The plug, sockets and wedgelock are harness parts, not board parts. Freeze these together (harness connector freeze condition):
  - the exact size 16 socket for 14 AWG
  - the wire insulation diameter against the plug seal range
  - the wedgelock
  - AT06-2S or DT06-2S: Amphenol calls them comparable. Mixing brands on one mated pair needs a fit and seal check.
- **Sealing:** Amphenol rates the header IP67 mated. The flange gasket seals against the enclosure wall, and the potted rear reservoir seals the pins. Potting is specified for up to 5 psi.
  - The panel cutout is the same as TE's DT13-2P cutout: 25.40 mm between two Ø3.94 holes, with #6-19 thread-forming screws at 11 to 15 in-lb.
  - Enclosure sealing must still be validated as an assembly.
- **Mechanical:** each header is 35.2 mm wide along the pin row and 27.4 mm tall above the board. The mating axis is 13.8 mm above the board. The flange seal face is 15.5 mm in front of the pin row, and the shroud reaches 30.1 mm. Six side by side need at least 212 mm of board edge, so the board outline and enclosure wall follow from this decision. Each header is held by three #4-20 screws from the solder side.
- **Pin numbering:** Amphenol's drawing labels the pins "1" and "2" on its mounting-face view, and the library footprint follows it. TE's DT13-2P drawing shows the same arrangement. With pin 2 as the ground return, a swap would put OUTx on the harness's ground cavity. Confirm the moulded cavity numbers on the first sample, and label the cavities on the harness drawing.
- **Procurement:** stocked at DigiKey and Mouser (GATE-BOM-01), with no second source chosen. Re-check stock at BOM lock.
- **Library:** AT13-2P-BM04 is in dropout-kicad-library PR #25. Node60 picks it up with the next library submodule update. Then set `library:` in `parts.yaml`.
