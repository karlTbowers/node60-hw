# Stage 3: critical blocks by hand

A block is reviewed by hand when its layout decides whether the board works and a router or
annealer cannot see that: a switching stage, a precision sense path, the critical link's line
interface, a crystal. Everything else is left to the annealer. A block is small: one IC (or
one function) with the parts that close its loops, about 30 parts at most, so it reads on one
screen and on a phone.

## What goes in a block

- The IC, every part on its private nets, and the decaps on any rail it has a pin on (a decap
  belongs to the IC that draws from the rail, not the one that makes it).
- Every part that closes one of its loops: a buck's input caps and output cap, a gate drive's
  return, a shunt's Kelvin taps and filter.
- A rail's test point and its 0R link go with the rail's maker.

## Composing it

Work on a copy (`blocks/<id>.kicad_pcb`). Read, in this order, and say which drove each
choice:

1. **The datasheet's layout figure** (or the application note's): where each part sits
   relative to the pins, which way it faces, where its ground lands.
2. **The datasheet's layout text**: distances, which loop is hot, what to keep away.
3. **The reference design or evaluation board**, matching the board's variant.
4. **House rules**: the handbook's chapter 05, and the plan's lanes and ports.

Match the figure to the board by net and pin function, never by designator: the datasheet's
C1 is not the board's C1. For switching stages and RF chains, KRT's `fit_template.py` does the
seating (its skill's §3.5: sketch in the footprint's frame, hot loop first); its result is the
starting pose table. For other blocks, place by hand with `place_pose.py set` or in KiCad.

Then extract the table and give every part its reason:

```bash
$KPY scripts/block_poses.py extract blocks/t1s.kicad_pcb --anchor K501 \
    --refs K501,FL501,C503,C504,D501,D502,R503,R504 --block t1s -o blocks/t1s.poses.json
```

- `why`: one line per part saying what places it there ("DC-block cap on the line side of
  K501, so the relay contacts see no DC; TI SNLA389 figure 3"). A part with no reason is a
  part nobody decided.
- `role`: `core` for anything on a loop, a Kelvin pair, a bootstrap or a crystal; `flex` with
  `flex_mm` (1–3 mm) for test points, pull-ups and slow filters.

## Checking it

- Switching stages: `hot_loop.py` with the stage's row in `switchers.json`. Its limits are
  the datasheet's (a distance it gives, or the figure's own: the HF cap's pads at the pins, the
  inductor at the SW pin). A limit nobody can source is left out and reported as `info`.
- Render each side zoomed with net names: KRT `render_placement.py blocks/t1s.kicad_pcb --view
  X0,Y0,X1,Y1 --side B -o blocks/t1s_B.png`. Look at it beside the datasheet figure before the
  user does.
- `check_assembly.py` on the copy: courtyards and bodies clear.

## switchers.json

```json
[{"name": "U303 1V5_CORE buck", "ic": "U303",
  "source": "TI LMQ66430-Q1 datasheet <number> rev <x>, section 11, figure <n>",
  "vin": ["3"], "pgnd": ["6", "13", "15"], "sw": ["7"], "fb": ["11"],
  "hf_cap": "C310", "input_caps": ["C310", "C311", "C312"],
  "limits": {"cin_gap_mm": 0.5, "l_gap_mm": 1.0, "fb_from_sw_mm": 2.0}}]
```

Pins by number from the footprint (`fit_template.py --pins U303` lists them). Name
`input_caps` when two stages share an input rail; leave `fb` out on a fixed-output part whose
FB pin is its output rail.

## The decision page for a block

One page per block. Pictures: each side of the block zoomed, net names readable; the
datasheet figure it follows (render the PDF page with KRT's `py_tools/pdf_text.py --render`;
the figure is shown on a private page and never committed). Facts: the parts, the sources.
Options: usually one ("as composed") plus any real alternative the composition weighed (the
inductor on the other side of the IC, a cap turned). Measures: the hot-loop rows. Costs: what
the arrangement gives up against the datasheet (a bigger courtyard gap, a longer leg).

On approval set `approved` to the date and decision id in the table. A later change to a core
part is a new version of the table and a new page.

## Identical channels

Compose and review one (Node60: output switch U601 with its parts); make the others' tables
with `block_poses.py copy ... --map 'U601=U701,C601=C701,...'` and place them with KRT
`place_pose.py replicate` or `block_poses.py apply --at`. A copy is checked (`block_poses.py
check`, `hot_loop.py`), not reviewed again, unless it had to differ: then only the difference
goes on a page.

## Holding an approved block while the rest is placed

- **The plan fixes its position** (Node60's T1S interface under the trunk's midpoint): apply
  the table at that pose and lock the parts before `place_simple` runs.
- **The annealer may move it** (a buck between its entry and its loads): give it to KRT as a
  template (`fit_template.py --write-intent`), so the annealer carries the block with its
  anchor. Template drift is graded by `check_floorplan`; `block_poses.py check` still decides.
