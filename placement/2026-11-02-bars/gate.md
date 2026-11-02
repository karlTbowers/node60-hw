# Placement gate: candidate.kicad_pcb

- Date: 2026-11-02; KiCad 10.0.7; board sha256 0c012b7fe2123f6e…
- Verdict: **NOT PASSED**

| Check | How it is measured | Status | Result |
|---|---|---|---|
| Buildable | KRT check_assembly --baseline (parts on the board, courtyards, bodies, pads) | FAIL |   VERDICT: NOT BUILDABLE / EXIT=4 |
| Floorplan intent | KRT check_floorplan --intent (edges, groups, templates, keep-outs, decaps) | PASS | 0 error(s) |
| Schematic parity | kicad-cli pcb drc --schematic-parity (field mismatches warn) | FAIL | footprint_symbol_field_mismatch 199, missing_footprint 2, footprint_symbol_mismatch 56 |
| Heights, B side, whole board | part_heights.py: model body, limit 6.17 mm (CLAUDE.md: board 6.17 mm off the floor (K501 5.2 mm accepted at 0.97 mm, user 2026-11-01)) | PASS | none over |
| Heights, F side, under the low lid | part_heights.py: model body, limit 9.0 mm (CLAUDE.md: 9.0 mm under the low lid above the board; the output and T1S headers stand under the raised front band and T1S hood (1 mm above the tallest header), not the low lid) | PASS | none over |
| Heights, F side, lid bosses, Ø8 mm at each SurLok M4 hole | part_heights.py: model body, limit 5.03 mm (scripts/enclosure_geometry.py v15: boss ends 16.2 mm, board top 11.17 mm) | PASS | none over |
| BGA escape U401 | escape_budget.py: layers needed vs planned, nothing over the ball field | PASS | diagonal gap 0.791 mm -> a 0.45 mm via between four balls: fits / deepest signal ring 8, 2 ring(s) per layer -> 4 signal layer(s) needed; 4 available (F.Cu, In2.Cu, In3.Cu, B.Cu) |
| Layer capacity | layer_capacity.py: MST demand vs tracks per 10 mm window | PASS | 0 window(s) over 100 % (ERROR), 0 over 60 % (WARN) |
| Switcher hot loops | hot_loop.py against each datasheet's layout limits | PASS | 0 FAIL |
| Critical blocks | block_poses.py check: core parts exact, flex within allowance, approved | FAIL | power: 13 parts, 0 off their table pose; approved 2026-11-02 (D04); t1s: 19 parts, 0 off their table pose; approved NOT YET |
| Fiducials | FID parts per assembled side; 2 or 4, not symmetric under a half turn | PASS | F: 3; B: 3 |
| Net classes | each planned class assigned to its nets, track width at least its minimum | PASS | 4 planned class row(s) on the board |
| Vias at high-current layer changes | free via sites within reach of each pad vs ceil(I / I per via) | PASS | 9 pad(s) have room |
| Fast route, KRT score | quick_score: blocking (open nets, floorplan, assembly) | PASS | blocking 0, joins_needed 0 |
| Fast route, board's own rules | grade_route.py: KiCad DRC with the board's .kicad_pro and .kicad_dru | PASS |   unconnected items : 0 /   not blocking (silk, dangling, library, mask): 614 /   NOTE: lib_footprint_issues, silk_overlap, silk_over_copper reached KiCad's 199-entry report cap; the count is a floor / BLOCKING=0 |
