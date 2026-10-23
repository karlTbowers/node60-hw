---
id: DEC-013
title: TE DEUTSCH DT13-2P headers for the six outputs, replacing the MX150 plan
status: accepted
date: 2026-10-22
revision: A
page: subsystems/harness
requirements: [REQ-OUT-001, REQ-OUT-002, REQ-NET-001]
parts: [DT13-2P, CH-AK-DT13-02, DT13-2P_Jorch]
gates: [GATE-THM-01, GATE-THM-02, GATE-BOM-01]
rejected:
  - option: Molex MX150 sealed connector sets (Rev A plan, TBD-MX150-SETS)
    reason: The user chose DEUTSCH DT13-2P headers on 2026-10-22, a connector they have used in an earlier design. No MX150 housing, terminal or seal had been chosen, so nothing released changes.
  - option: AliExpress or Alibaba DT13-2P copies as the primary part
    reason: No authorized distributor, no drawing, no ratings backed by test data, and no traceable manufacturer. The genuine TE part is stocked at DigiKey and Mouser.
    outcome: alternative
  - option: OUTx on both pins of each header, loads returning to vehicle ground
    reason: Halves the current per contact (about 5 A) and keeps load current out of the node ground. The user chose a local ground return on pin 2 instead (2026-10-22). Paralleled pins would also need two wires or a splice per output, and open-load detection cannot see one broken contact.
---

## Context

Rev A planned "MX150 sealed" output connectors, 10 A each with 14 AWG minimum wire (REQ-OUT-002), but never chose a part (`TBD-MX150-SETS`, exact mating sets open). On 2026-10-22 the user chose DEUTSCH DT series instead: DT13-2P 2-pin right-angle PCB headers mating DT06-2S plugs. The user named two marketplace listings (AliExpress, Alibaba) as sources, then made the genuine TE part primary and kept the marketplace parts as alternates.

The output target is unchanged: six independently switched outputs (REQ-OUT-001), 10 A continuous each (REQ-OUT-002), −40 to +125 °C ambient (REQ-QUAL-001 is the board-wide grade target).

## Decision

**One TE DT13-2P per output, six per board** (J904 placeholder on the schematic becomes six headers).

- **TE Connectivity DT13-2P:** DEUTSCH DT series 2-position right-angle PCB receptacle with molded-in pins, panel flange and flange seal, gray, 5.46 mm pitch. It mates the DT06-2S plug with a W2S wedgelock and size 16 sockets.
  - Ratings (TE 108-151009 rev. E §3.2): **13 A per contact with 14 AWG or 16 AWG wire**, 250 V, **−55 to +125 °C**. Header ingress protection: **"Not Tested"**.
  - PCB layout (TE 114-151046 rev. A §3.4): two Ø1.88 mm pin holes, three Ø3.43 mm holes for #4-20 Plastite 48 screws from the solder side.
  - Library: `DropOut_Connector:DT13-2P`, footprint `DropOut_Connector_TE-Connectivity:TE_DEUTSCH-DT_DT13-2P_1x02_P5.46mm_Horizontal` (dropout-kicad-library PR #19).
- **Alternates (no authorized distributor), same footprint:**
  - HISENG (Shenzhen Haisheng Hongye Technology) **CH-AK-DT13-02**, from Alibaba. The seller claims 13 A, 250 V and IP67.
  - **Jorch DT13-2P**, from AliExpress, sold as a set with a DT06-2S plug. The seller gives no ratings.

**Observed 2026-10-22, not quotes:**

| Part | Source | Price | Stock / terms |
|---|---|---|---|
| TE DT13-2P | DigiKey 1734-1452-ND | $8.23 @1, $6.99 @10, $5.66 @200 | 217 |
| TE DT13-2P | Mouser 571-DT13-2P | $8.15 @1, $6.99 @10, $5.65 @100 | 508 |
| HISENG CH-AK-DT13-02 | Alibaba listing 1601383533915 | $0.10–0.50 | MOQ 100, shipping negotiated |
| Jorch DT13-2P + DT06-2S set | AliExpress listing 3256804973396267 | $5.02 per set, $38.32 per 10 sets | – |

Six TE headers cost about $49 per board at single quantity, or about $34 at 200.

## Pin assignment

**Pin 1 = OUTx, pin 2 = local ground return** (the user's decision, 2026-10-22). Each load gets a two-wire cable with its own return, and every output's load current comes back through the node.

- Each contact carries the full 10 A, which is 77 % of TE's 13 A rating.
- Each pin 2 connects to the power-entry ground/star region, not to the logic plane (system partitioning rule).

## Consequences

- **Current at +125 °C:** TE rates the contact 13 A but publishes no derating curve. Its +125 °C limit includes self-heating, so at +125 °C ambient there is no headroom for any temperature rise. TE's data supports 10 A per contact only below the ambient where measured rise keeps the contact at or under +125 °C.
  - GATE-THM-01 and GATE-THM-02 must measure contact temperature rise at 10 A with all six headers loaded.
  - The result may be a derated ambient for 10 A. Both contacts of each header carry 10 A (output and return), so each header dissipates twice a single contact's heat.
- **60 A node ground return:** with every load returning through pin 2, up to 60 A (six outputs at 10 A) flows from the output headers into the power-entry ground/star region and out through the node's single ground conductor (REQ-NET-001).
  - The ground conductor, its input connector contacts, and the PCB ground path from the six headers to the star point must each carry 60 A continuous, matched to the battery feed. This is the harness page's "matched high-current return": no chassis-only return.
  - Load current must not cross the logic ground plane. Route each pin 2 return to the star region with the same copper and via treatment as its OUTx net.
  - The node's ground sits above vehicle ground by the drop along the ground conductor and its contacts at up to 60 A. The rest of the T1S segment sees that offset. Cover it in the six-channel assembly tests (ground offsets, verification step 15).
  - The ground conductor carries the same current as the battery feed, so size it and its contacts like the battery feed, including the worst fault current the source-end fuse lets through.
- **Wire gauge:** 14 AWG stays the minimum. TE rates size 16 contacts at 13 A with 14 AWG. The DT06-2S plug, sockets and wedgelock are harness parts, not board parts: freeze the exact socket for 14 AWG, the wire insulation diameter against the DT06-2S seal range, and the wedgelock together (harness connector freeze condition).
- **Sealing:** TE rates DT inline connectors IP68 and IP6K9K, but lists PCB headers and flanged versions as "Not Tested". The DT13-2P seals with its flange seal against the enclosure wall.
  - The enclosure needs TE's panel cutout (DT13-2P drawing, sheet 2) and two #6-19 screws per header.
  - Enclosure sealing must be validated as an assembly.
- **Mechanical:** each header is 35.3 mm wide along the pin row and 27.4 mm tall above the board. The flange seal face is 15.5 mm in front of the pin row, and the shroud runs 14.6 mm beyond it through the panel. Six side by side need at least 212 mm of board edge, so the board outline and enclosure wall follow from this decision. Each header is held by three #4-20 screws from the solder side.
- **Pin numbering to verify (now release-blocking):** TE's drawing and TE's application-spec layout figure disagree on which hole is pin 1. The library follows the drawing, which TE says takes priority. With pin 2 as the ground return, a swap would put OUTx on the harness's ground cavity. Check the molded cavity numbers on a real DT13-2P before PCB release (PR #19), and label the cavities on the harness drawing.
- **Alternate-source risk (CH-AK-DT13-02, Jorch):**
  - Neither listing has an authorized distributor, a drawing, a datasheet, or automotive qualification evidence. TE's DT qualification (test report 501-151032) covers only TE parts.
  - The Jorch listing uses the DEUTSCH name, so treat it as a possible counterfeit. Expect lot-to-lot variation in dimensions, housing material, plating and seals.
  - Seller ratings (13 A, IP67, −55 to +125 °C) are claims only.
  - Use only TE parts for qualification and validation builds.
  - Before any alternate is fitted, check a sample against the TE drawing: holes, cavity numbering, fit and latch with a genuine DT06-2S, and temperature rise at 10 A. Never mix sources on one board without that check.
- **Procurement:** the TE part is stocked at DigiKey and Mouser (GATE-BOM-01). Re-check stock at BOM lock.
- **Library:** all three parts are in dropout-kicad-library PR #19. Node60 picks them up with the next library submodule update. Then set `library:` in `parts.yaml`.
