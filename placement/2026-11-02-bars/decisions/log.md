# Decisions, placement run 2026-11-02-bars

| Id | Date | Question | Page | Answer | What changed |
|---|---|---|---|---|---|
| D01 | 2026-11-02 | The placement plan: strict busbar via rule (A) or tented vias allowed under the bars (B) | https://claude.ai/artifact/6BbrzSQ6KqUGT5fSrQau5U | B, tented vias (user, 2026-11-02) | `node60.kicad_dru` drops `via` from both busbar rules; DEC-025 notes it; plan v1 approved; parts may stay under the bars |

## Skill gaps found in this run

- `escape_budget.blocking_areas` (used by `gate.py`'s via-site row) treats a rule that disallows only tracks as one that disallows vias, so the via-site row can't tell the two readings of the busbar rule apart. D01's option B numbers were measured with the areas filtered to via-forbidding rules. Fix in this run's PR.
- `gate.py`'s via-site row counts no via inside the pad itself, so a large tab (Q201–Q204's 8 × 10 mm drain pad) gets no credit for via-in-pad, which JLCPCB's filled and capped vias allow.
- Plan v1's busbar net tie (BB901/BB902 with a pad in each terminal, tied as a net tie) does not work: KiCad's net tie only lets copper of different nets touch without a DRC error; it joins nothing, and VBAT_IN still had 17 unconnected items with it. The fix is a schematic net-tie part between two nets (to be decided, D02). Reverted; J901 and J902 stay reported unconnected until then.
