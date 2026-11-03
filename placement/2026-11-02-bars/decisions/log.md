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

## Skill gaps found in this run

- `escape_budget.blocking_areas` (used by `gate.py`'s via-site row) treats a rule that disallows only tracks as one that disallows vias, so the via-site row can't tell the two readings of the busbar rule apart. D01's option B numbers were measured with the areas filtered to via-forbidding rules. Fix in this run's PR.
- `gate.py`'s via-site row counts no via inside the pad itself, so a large tab (Q201–Q204's 8 × 10 mm drain pad) gets no credit for via-in-pad, which JLCPCB's filled and capped vias allow.
- Plan v1's busbar net tie (BB901/BB902 with a pad in each terminal, tied as a net tie) does not work: KiCad's net tie only lets copper of different nets touch without a DRC error; it joins nothing, and VBAT_IN still had 17 unconnected items with it. The fix is a schematic net-tie part between two nets (to be decided, D02). Reverted; J901 and J902 stay reported unconnected until then.
- `escape_budget.blocking_areas` fixed in this run: it takes `blocks=("via",)` or `("via", "track")`, and the via checks (`escape_budget.py`, `gate.py` via sites) ask only about vias.
