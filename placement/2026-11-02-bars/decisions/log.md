# Decisions, placement run 2026-11-02-bars

| Id | Date | Question | Page | Answer | What changed |
|---|---|---|---|---|---|
| D01 | 2026-11-02 | The placement plan: strict busbar via rule (A) or tented vias allowed under the bars (B) | https://claude.ai/artifact/6BbrzSQ6KqUGT5fSrQau5U | B, tented vias (user, 2026-11-02) | `node60.kicad_dru` drops `via` from both busbar rules; DEC-025 notes it; plan v1 approved; parts may stay under the bars |
| D02 | 2026-11-02 | How the board shows the VBAT_IN busbar joining J901 to J910 | https://claude.ai/artifact/QQyG6R4BYMt8VuPG6xff9c | A, a busbar part in the schematic (user, 2026-11-02) | library net-tie part, fiducial footprint and schematic change in their own session; judging route keeps J901 on a stand-in net until it lands |
| D03 | 2026-11-02 | Board fiducials, 3 per side, via a new library footprint | https://claude.ai/artifact/WKcHKSLmrtASeteVD7FHuo | A, board fiducials, 3 per side (user, 2026-11-02) | a DropOut fiducial footprint through the library's add-part; six placed by `place_connectors.py` at the measured spots; spots reserved as keep-outs meanwhile |
| D04 | 2026-11-02 | Power-entry block: INA228 beside its shunt | https://claude.ai/artifact/TmF2g6F2qwuSfKVdGnomnn | A, as composed (user, 2026-11-02) | power block v1 approved: U202 beside R201, C214 on B.Cu at U202 pin 6; held through placement |
| D05 | 2026-11-02 | T1S block as it stands | https://claude.ai/artifact/3qNtDXwTVFXDRsiMQj4BjQ | A, as it stands (user, 2026-11-02) | T1S block v1 approved, held through placement; R503 swap dropped |
| D06 | 2026-11-02 | Buck cells (U302, U303) as composed, U303 divider on the SW side | https://claude.ai/artifact/WajY8VuzyCVy9FZJmUXBPT | A, as composed (user, 2026-11-02) | buck cells approved as seated; route U303's FB round the north of the chip, away from SW; check 1V5_CORE ripple on the first boards |
| D07 | 2026-11-02 | MCU crystal block as composed, with a no-via rule on the crystal nets | https://claude.ai/artifact/7cWymGEgGDMhtveNwaRFJy | A, as composed with the no-via rule (user, 2026-11-02) | crystal block approved; node60.kicad_dru forbids vias on the FXOSC nets; routing routes them first on B.Cu |
| D08 | 2026-11-02 | One output-switch cell, U701's, copied to U601 and U801 | https://claude.ai/artifact/V4af2FuXFsyNta7XuYQYwC | A, as composed (user, 2026-11-02) | output cells approved: U601 turned 90° and moved 4.3 mm, U801 to (224, 113), TP806 at (231, 107.75) |
| D09 | 2026-11-02 | Placement gate: accept the four open items (busbar tie-pad overlaps, schematic parity, U501 pin 29, KRT's busbar join) and open the PR | https://claude.ai/artifact/1z4TKiSdvHmywjzRExvkxU | A, open the PR (user, 2026-11-02) | the four items accepted (REPORT.md); composed placement applied to node60.kicad_pcb |
| D10 | 2026-11-02 | U303's 1.5 V core buck cell recomposed round the TPS628502-Q1 (DEC-026) | https://claude.ai/artifact/FcS4kULQHc7bRbmQPYejuZ | A, as composed (user, 2026-11-02) | buck_1v5 cell table approved for the TPS628502-Q1; replaces D06's LMQ66430 cell |
| D11 | 2026-11-03 | Ready for routing: start full routing on this placement | https://claude.ai/artifact/FQKm81rbkJqD8XYJGVBc1m | A, start routing (user, 2026-11-03: after a review of KRT's routing tools and ee-skills' ee-layout-rules) | placement done; routing next |
| D12 | 2026-11-03 | Routing review: layer roles, outer copper, output cells, supply balance, input shunt, via current, routing method (7 decisions) | https://claude.ai/artifact/CYdagJE6yYyxJGvN8GtZcC | 1A 2A 3A 4B 5C 6A 7A (user, 2026-11-03). 4B: shift the power-entry group right without changing it much, and spread it for the vias. 5C: a bigger 4-terminal shunt, or two 0.5 mΩ in parallel if none is found | layer roles In1 GND / In2+In3 VBAT_PROT / In4 GND; 1 oz outer; output cells re-composed; power entry shifted right; shunt search; 0.65 A per via; staged routing |
| D13 | 2026-11-03 | The three output cells turned to 0° and centred between their headers (D12-3) | https://claude.ai/artifact/KSbSL664A3kcrYLYsxawG9 | awaiting answer | |
| D14 | 2026-11-03 | The input shunt (BVR 4026 0.3 / 0.2 mΩ, or 2 × 0.5 mΩ) and how the power entry moves right (shift, re-order, or compact) | https://claude.ai/artifact/KmXzdSwfgmrct2UQr6QukC | D14-1 A, D14-2 B (user, 2026-11-03) | R201 becomes Isabellenhütte BVR-Z-R0003-1.0 (0.3 mΩ, 4-terminal; R208 26.7 kΩ, R210 383 Ω); the power entry re-ordered to flow east |

## Skill gaps found in this run

- `escape_budget.blocking_areas` (used by `gate.py`'s via-site row) treats a rule that disallows only tracks as one that disallows vias, so the via-site row can't tell the two readings of the busbar rule apart. D01's option B numbers were measured with the areas filtered to via-forbidding rules. Fix in this run's PR.
- `gate.py`'s via-site row counts no via inside the pad itself, so a large tab (Q201–Q204's 8 × 10 mm drain pad) gets no credit for via-in-pad, which JLCPCB's filled and capped vias allow.
- Plan v1's busbar net tie (BB901/BB902 with a pad in each terminal, tied as a net tie) does not work: KiCad's net tie only lets copper of different nets touch without a DRC error; it joins nothing, and VBAT_IN still had 17 unconnected items with it. The fix is a schematic net-tie part between two nets (to be decided, D02). Reverted; J901 and J902 stay reported unconnected until then.
- `escape_budget.blocking_areas` fixed in this run: it takes `blocks=("via",)` or `("via", "track")`, and the via checks (`escape_budget.py`, `gate.py` via sites) ask only about vias.

## D15 Power entry block (2026-11-03)

Published (https://claude.ai/artifact/ESfjfBiHEvP6z8EAyY6TFh): the re-ordered power entry (D14-2 B) as a block page; `blocks/power.poses.json` replaces D04's table (approved: null). Recommendation A. C214 moved to F.Cu over U202 pin 6. Awaiting the user's answer.

D15 answered 2026-11-03: **A, as composed** (user). `blocks/power.poses.json` approved; it replaces D04's table. Board already matched to node60 #54 (R201 Kelvin nets, R208 0402, R210 383 Ω).

D13 answered 2026-11-03: **A, as turned** (user). `blocks/out_6x`, `out_34`, `out_8x` approved; they replace D08's cells.

D12 rules adopted 2026-11-03 (D12-1 A, D12-7 step 1): `node60.kicad_dru` routing rules, net classes PWR_BATT / PWR_RAIL / SW_NODE, T1S class extended to the K501 legs, mask web 0.10 mm, rule areas ESCAPE_U401/U501 and UNDER_Y401/Y501 (`scripts/draw_rule_areas.py`). `rules/prove_rules.py`: 24 of 24 cases pass (16 fire, 8 controls quiet). Real board: DRC 0 errors, parity 0, ERC 0.

D12-6 applied 2026-11-03: `plan.json` counts 0.65 A per via; R201's high-current pads are now its force pads 1 and 4 (BVR4026). Gate row "Vias at high-current layer changes" PASS, free/needed: Q201–Q204.9 242/47, R201.1 206/93, R201.4 199/93, U601/U701/U801.17 55/31 (R201's two pads share some sites).

## D16 T1S line layout (2026-11-03) — https://claude.ai/artifact/Y3JvotHyv5ecsbPLXwQEUK

User 2026-11-03: T1S runs short and equal; either connector may be used, also as an end node; move the PHY if needed. Composed: PHY chain north of the trunk's midpoint, K501 centred on it, trunk on F.Cu with via taps. `blocks/t1s.poses.json` re-extracted (approved: null). D16-2 asks about a second ESD pair at J912. Awaiting the user's answer.
