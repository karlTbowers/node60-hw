# Where this skill comes from

Written 2026-11-02 for Node60 by combining the two placement processes used on it. The user
chose (2026-11-02) to keep the skill in the Node60 repo for now, and how to treat each source:

## KiCadRoutingTools `plan-pcb-placement` (MIT)

[drandyhaas/KiCadRoutingTools](https://github.com/drandyhaas/KiCadRoutingTools), MIT
licence, as of commit `bf0405d8`. Its tools are **used in place** from a clone
(`~/Dev/KiCadRoutingTools`), not copied: the annealer (`py_placer/place_simple.py`), the intent
and groups files, `check_floorplan.py`, `check_assembly.py`, `check_groups.py`,
`fit_template.py`, `place_pose.py`, `render_placement.py`, `judge_seeds.py`, `quick_score.py`,
`copy_board.py`, `add_rule_area.py`, and its skill as the manual for them. Kept from it as
process: the annealer proposes the placement; groups by function; datasheet templates for
switching stages; many seeds, judged by a fast route; DONE means a fast route with no blocking
net; "better" is lexicographic; the stop rule after three approaches that don't lower blocking.

## ee-skills `pcb-placement` and its siblings (no licence)

[charlesh97/ee-skills](https://github.com/charlesh97/ee-skills), as of commit `eded36c`:
`pcb-placement`, `ee-layout-rules` (`rules/layout.md`), `layout-constraints`, `dcdc-layout`,
`hdi-breakout`, `pcb-routing`. The repo has no licence, so, as the handbook did for its
schematic rules (handbook chapter 05, "Where these rules come from"), **nothing is copied**:
every idea taken is restated in DropOut's words, and every script here was written new. Its
rule IDs are cited where an idea came from one, so it can be traced back.

| Taken (restated) | From | Here |
|---|---|---|
| A short written plan before placing: fixed parts, keep-outs, height limits, zones, layer plan, critical nets with lanes, block ports; each item with its source; assumed items marked | `pcb-placement` stage 1, L-05 | stage 1, `plan.md` |
| Mechanical facts come from the human, never invented | L-05, L-14 | rule 3 |
| Layer count from capacity: demand across cuts against tracks that fit | L-37, L-76 | `layer_capacity.py` (new code; per-window MST demand) |
| BGA escape budget: tracks between balls, a via between four balls, rings per layer | `hdi-breakout` §2, L-47 | `escape_budget.py` (new code; adds rule areas over the ball field) |
| A switcher's layout is checked against its datasheet: HF cap at the pins, loop on one side, inductor at SW, feedback away from SW | L-11, L-28, `dcdc-layout` cell check | `hot_loop.py` (new code; placement-stage measures only) |
| Critical blocks as pose tables with a reason per part; core and flexible parts; identical channels reviewed once and copied | `pcb-placement` stage 2, L-78 | stage 3, `block_poses.py` |
| An approved block never changes silently | `pcb-placement` rule 8 | rule 6 |
| A decap belongs to the IC that draws from the rail | L-78, `pcb-placement` rule 4 | `blocks.md` |
| One gate table before routing, with exceptions accepted by name | `pcb-placement` stage 5, `gates.md` | stage 6, `gate.py` |
| Fiducials per assembled side, asymmetric, never three | L-17 | gate row |
| Via room beside high-current pads, count from current | L-39 (moved to its power-integrity rules), `gates.md` | gate row |
| Exceptions are scoped `.kicad_dru` rules, never board-wide floor changes | L-04, L-20 | `fast-route.md` |
| The human approves each step on a page with pictures | `pcb-placement` review page | decision pages (the user's own requirement, 2026-11-02; built differently: a static page per decision, no server) |

| Not taken | Why |
|---|---|
| "The AI decides every position; scripts only check" | The annealer proposes the board; only critical blocks are composed by hand |
| Blocks of ~30 parts for the whole board, a block gate for each | Only the blocks the plan names as critical are reviewed |
| "The bottom side carries only light parts" (L-17) | Node60 places nearly everything on the bottom on purpose (`lessons.md`) |
| `board_rules.py` profiles, `drc.json`, KiCad templates | The board's own `.kicad_pro`, stackup decision and fab quote set its rules |
| `datasheets/<MPN>/capture.json`, `project.yaml`, `power_tree.yaml` | DropOut keeps datasheets in `dropout-vendor-docs` and project answers in `CLAUDE.md` |
| The review server and feedback files | Decision pages are published as private Artifacts and answered in the session |
| "No router on the master board" (L-69) | Applies to routing, not placement; here the router only judges seeds on copies |

## Node60's own runs

`placement-compare/` (local, excluded from git): the V11, V14 and V15 runs with KRT, the
repair scripts, and the V15F fast route that `grade_route.py` was tested on. Their lessons are
in `lessons.md`.
