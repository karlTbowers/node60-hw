# Stage 6: the placement gate

One table, every row measured on the kept seed by `gate.py`, written to `gate.md` with the
date, the KiCad version and the board's hash. Routing does not start, and the repo's board
is not replaced, until every row is PASS, WARN or ACCEPTED.

| Row | Measured by | Passes when | Owner if it fails |
|---|---|---|---|
| Buildable | KRT `check_assembly --baseline`: parts on the board, courtyards, bodies, pads off the outline | buildable | stage 4 (repair or re-place) |
| Floorplan intent | KRT `check_floorplan --intent`: edges, groups, templates, keep-outs, decap limits | 0 errors | stage 4, or the intent (stage 1) |
| Schematic parity | `kicad-cli pcb drc --schematic-parity` | no structural item; field mismatches WARN | the schematic or the footprint import |
| Heights, per side and area | `part_heights.py` against the plan's limits | nothing over; a part with no height is a WARN until declared | stage 2 (declare) or stage 4 (move) |
| BGA escape, per BGA | `escape_budget.py` | layers needed ≤ the plan's signal layers, and no rule area over its balls | stage 4 (move), or a stackup decision |
| Layer capacity | `layer_capacity.py`: MST demand vs tracks per 10 mm window | no window over 100 %; over 60 % is a WARN | stage 4, or the layer plan |
| Switcher hot loops | `hot_loop.py` against each datasheet's limits | every graded row PASS | stage 3 |
| Critical blocks | `block_poses.py check` | core parts at their table pose, flex within allowance, every table approved | stage 3 (new version) |
| Fiducials | per assembled side: count and half-turn symmetry | 2 or 4 per side, not symmetric | stage 1 (assembly) |
| Net classes | the `.kicad_pro` assignments against the plan's rows | every planned net in its class, width at least its minimum | the project file (a net-class change) |
| Vias at high-current layer changes | free via sites near each listed pad vs ceil(current / current per via) | enough room at every pad | stage 4 |
| Fast route, KRT score | `quick_score` of the judging route | blocking 0 | stage 5 |
| Fast route, board's own rules | `grade_route.py` | `BLOCKING=0` | stage 5 |

## Reading the rows

- **NOT RUN blocks like a FAIL.** It means the plan did not give the row its input (no
  height limits, no switcher spec). Fill the plan; never delete a row.
- **ACCEPTED** is a FAIL the user accepted on a decision page; the plan's `accepted` names
  the row, the decision and why. The gate keeps printing the measurement.
- **Fiducials** are counted from parts named `FID…` or with "Fiducial" in their footprint.
  Panel fiducials instead of board fiducials is a valid answer, but it is the user's, on a
  page.
- **Via sites** count a grid of via positions at via-plus-space pitch within `radius_mm` of
  the pad, clear of every other pad (a through via meets every layer's pads) and of any rule
  area that forbids the pad's net a via. It reserves nothing: it says whether room exists.
  Routing must then put the vias there.
- **Schematic parity**: `footprint_symbol_field_mismatch` items are fields (MPN, value) that
  differ between symbol and footprint; they do not change the copper, so they warn. Anything
  else (a footprint missing, extra, or on another library footprint) fails.

## What the gate does not measure

Said in the hand-back, so nobody reads the table as more than it is:

- Return paths and plane splits under signals (no copper yet).
- Thermal copper area: the plan states it; routing draws it.
- Lane corridors for critical nets: drawn on the plan picture and checked by eye on the
  decision page. A corridor checker is a follow-up.
- Anything a datasheet asks that the hot-loop spec does not encode.
