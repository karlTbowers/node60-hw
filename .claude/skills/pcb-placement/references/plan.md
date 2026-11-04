# Stage 1: the plan

The plan is short: one page of Markdown for the user and one JSON for the scripts. It is
written before any part moves, approved on a decision page, and versioned: a change after
approval is `plan.md` v2 with what it changes listed, and a new decision page.

Every item carries its source: a decision record (`DEC-018`), a file (`node60.kicad_dru`,
`scripts/place_connectors.py`), a datasheet (document, revision, section or figure), the user
(with the date), or **assumed** (and then it is listed under "Assumed" at the end, so nobody
mistakes it for a decision).

## plan.md

```markdown
# <board> placement plan, v1 (<date>)

Status: draft | approved <date> (decision D01)

## Stackup and layers
Layer count, finished thickness, copper weights, fab; decided or open.
| Layer | Job | Direction | Source |
L1 F.Cu signal + busbar seats ... / L2 GND plane / ...

## Fixed parts
| Ref | What | Pose or edge | Source |
How they are placed (a script, KRT fixed_poses, by hand) and locked.

## Enclosure keep-outs and height limits
| Area | Side | What may stand there | Height limit | Source |
Include rule areas that limit copper as well as parts: say which parts may stand under
each, judged by whether their nets can still leave (a part under an area that forbids
other-net vias can only route on its own side).

## Heat and quiet zones
| Zone | Parts | Why | Keep away from |
What dissipates (with the copper or via area it needs), what switches, what is quiet.

## Critical nets
| Id | Nets | Parts | Layers | Lane (port to port) | Budget | Rule |
Each lane is drawn on the plan picture.

## Blocks and ports
| Block | Anchor | Parts | Reviewed by hand? | Ports (edge each external net leaves from) |
Identical channels: which one is composed, which are copies.

## Net classes and high-current pads
| Nets | Class | Track width | Clearance | Source (current, rule) |
| Pad | Current | Current per via | Vias needed |

## Assembly
Sides assembled; fiducials (count and corners per side); heavy parts on the second side and
how they are held (glue, reflow order); parts that must stay on top (debug header).

## Switchers
One line per switcher pointing to its row in switchers.json and its datasheet figure.

## Assumed
Every item above marked assumed, with what would confirm it.
```

## plan.json

The scripts read only this. Paths are relative to the plan.

```json
{
  "board_name": "node60",
  "project": "../../node60.kicad_pro",
  "rules": "../../node60.kicad_dru",
  "schematic": "../../node60.kicad_sch",
  "krt": "~/Dev/KiCadRoutingTools",
  "intent": "intent.json",
  "baseline": "fixed.kicad_pcb",
  "signal_layers": ["F.Cu", "In2.Cu", "In3.Cu", "B.Cu"],
  "plane_nets": ["GND", "VBAT_PROT"],
  "plane_layers": {"In1.Cu": "GND", "In2.Cu": "VBAT_PROT", "In3.Cu": "VBAT_PROT", "In4.Cu": "GND"},
  "plane_windows": {"In1.Cu": "power_only", "In2.Cu": {"window": [145, 29.95, 215, 62], "keep": 0.5,
                    "cost": "U601/U701/U801 +1 to +2 % supply resistance (plane_model.py)", "decision": "D17"},
                    "In3.Cu": "power_only", "In4.Cu": "power_only"},
  "track_mm": 0.1, "space_mm": 0.1, "via_mm": 0.45,
  "bgas": ["U401"],
  "heights": [{"side": "B", "limit_mm": 6.17, "area": "whole board", "source": "CLAUDE.md: board 6.17 mm off the floor"}],
  "declared_heights": [{"ref": "TP201", "height_mm": 0.05, "source": "1 mm exposed pad, no part"}],
  "fiducials": {"sides": ["F", "B"], "count": [2, 4]},
  "net_classes": [{"nets": "/T1S_*", "class": "T1S_100R", "source": "DEC-012"}],
  "high_current": [{"pad": "U601.13", "amps": 10, "via_amps": 1.0, "radius_mm": 3, "source": "REQ, 10 A per output"}],
  "switchers": "switchers.json",
  "blocks": ["blocks/t1s.poses.json"],
  "accepted": [{"check": "Fiducials", "decision": "D07", "note": "panel fiducials only"}]
}
```

- `track_mm`, `space_mm`, `via_mm` are the board's own escape numbers (its `.kicad_pro` floors,
  or a scoped rule area's), never lower ones a router would like.
- `signal_layers` is the layer plan's, not every copper layer: a plane layer is not a signal
  layer because a track can be put on it.
- `plane_windows` is required whenever `plane_layers` is set: for **every** plane layer, either
  `"power_only"` (no signal tracks anywhere on it; vias pass, since through vias cross every
  layer) or a `window` rectangle (mm, x0, y0, x1, y1) where signal tracks may run and the plane
  is not poured, with its `cost` (the plane model's supply resistance to each load with and
  without it) and the `decision` that approved it. `keep` is the plane copper left in the window
  across that net's plane layers (0.5 = one of two equal layers windowed). Windows go where the
  plane carries little current (away from the path from source to loads); the model shows how
  little. `scripts/draw_rule_areas.py --window LAYER:X0,Y0,X1,Y1 --power-only LAYER` draws them
  (SIGNAL_WINDOW_* with no pour, POWER_ONLY_* with tracks not allowed), and the fast route
  runs with them, so the judge never puts a signal where the plane must be whole.
- `accepted` grows only from decision pages.

## The plan picture

The plan's decision page shows the board drawn with what the plan says, not a placement:

- The outline, the fixed parts placed and labelled (ref and purpose).
- Keep-outs and rule areas, tinted by kind, each labelled with what may stand in it.
- Heat and quiet zones as outlined areas; critical-net lanes as named lines between the
  blocks' ports.

KRT draws most of it: `render_placement.py fixed.kicad_pcb --intent intent.json --view
X0,Y0,X1,Y1 -o plan.png` draws zones, keep-outs and labels. Draw the lanes and zones on top
as an SVG (they are a few lines and rectangles in board millimetres); put the plan's tables in
the page's facts and options text.
