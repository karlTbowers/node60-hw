# Lessons from Node60's placement runs

Each one cost a run. Read them before stage 1; add one in the same shape when a run teaches
something new.

## A placement can pass every placement check and still not route

**What happened (V15, 2026-11-01).** KRT's annealer, fed a hand-edited intent and groups,
gave a seed that was buildable with no floorplan error. Its first fast route left 9 nets
open. The annealer had put U401 (S32K344, 257 balls, 0.8 mm) on the bottom under the VBAT_IN
busbar, where `node60.kicad_dru` allows only VBAT_IN on F.Cu, so no other net may have a
through via there: 52 balls had one routing layer.

**What the skill does.** The plan says which parts may stand under each rule area, judged by
whether their nets can still leave; the intent gets a keep-out on every side the rule reaches
(the V15 intent had the busbars on the top side only); `escape_budget.py` names the balls
under a rule area before anything is routed.

## The judging route ignored the board's copper rules and floors

**What happened.** KiCad's DRC with the board's own rules found, on that fast route, 53 vias
under the busbars (against the busbar rules) and 40 vias below the board's 0.35 mm via floor.
`route.py` reads net-filtered `disallow` rules from the sibling `.kicad_dru`, but the plane and
fanout steps lay copper with their own search, and `autoplan.py` routes at the fab's floors
(0.25 mm fine via, 0.09 mm clearance), which it also wrote into the judging copy's project.

**What the skill does.** Every fast route is graded by `grade_route.py` against the board's
real `.kicad_pro` and `.kicad_dru` (`references/fast-route.md`); the judging copy gets the
DRU-only areas as native keep-outs; a finer via for an escape is a user decision written as a
scoped rule, never a floor the router picks.

## Heights come from the model's body, not from every point in the STEP file

**What happened.** K501 (Omron G6K relay) read 5.58 mm in KRT; the STEP file's highest point of
any kind is 7.82 mm; its body is 5.2 mm, as Omron's drawing says. STEP files hold axis
placements and B-spline control points outside the body.

**What the skill does.** `part_heights.py` measures a tessellated body (CadQuery) or the B-rep
vertices, and prints the all-points maximum beside it. A part with no model gets a datasheet
height in the plan, never a guess. With 0.97 mm between K501 and the floor, a 0.4 mm error
decides whether the board fits.

## The bottom side carries heavy parts on purpose

ee-skills' assembly rule says the second side carries only light parts. Node60 puts nearly
every part on the bottom (DEC-024, user, 2026-11-01) and keeps only decoupling, D201 and the
debug header on top, so the light-parts rule does not apply. What does: the plan's assembly
section says which side is reflowed first and how heavy bottom parts are held during the
second reflow (or that the board is reflowed bottom-only and the top parts are placed after),
and asks the assembler's limits as a decision.

## ee-skills' inputs don't exist here

Its board-rule profiles (1.6 mm, 2 and 4 layers), datasheet captures
(`datasheets/<MPN>/capture.json`) and project YAMLs are not part of DropOut's process.
Node60's rules come from its stackup decision and fab quote, its datasheets from the
manufacturer through `dropout-vendor-docs`, its project answers from `CLAUDE.md`. The skill
reads those.

## Repair loops are a symptom

**What happened.** V15 needed four hand-written repair scripts (`repair.sh`, `fix_crystal.sh`,
`wide_repair.sh`, `nudge.sh` in `placement-compare/`): each tried poses round a target with KRT's
`place_pose.py --near --snap` and kept the first that lowered the floorplan error count and
stayed buildable. They worked, but each repair was a part the intent had not held (the crystal
Y401 had to be brought back to its oscillator balls).

**What the skill does.** The crystal and other critical parts are approved blocks, held through
placement; a part that needs a repair in every seed is an input to fix (KRT §3.6), and every
repair move that remains goes in REPORT.md.

## Grade the kept seed, not the last file written

The fast-routed board is never the placement. Copy the seed's own `s<S>.kicad_pcb` (with
`copy_board.py`) as the kept placement; the fast route is evidence only.

## A net tie doesn't join two pads of the same net

**What happened (2026-11-02).** Plan v1 tied the busbar footprint's two pads (one inside each
terminal's pad, same net) as a KiCad net tie, so the bar would join J901 to J910 on the board.
VBAT_IN had 17 unconnected items before and after: KiCad's net tie only lets copper of different
nets touch without a DRC error.

**What the skill does.** A part that joins two points with no board copper between them (a busbar,
a cable, a jumper wire) is a two-net part in the schematic (a net-tie symbol between two nets), or
an accepted exception on a decision page. The judging route moves the far terminal to a stand-in
net meanwhile, so the router doesn't lay copper in parallel with the part.

## A rule that forbids tracks is not a rule that forbids vias

**What happened (2026-11-02).** After decision D01 the busbar rules forbid other nets' tracks and
pours but not vias. `escape_budget.blocking_areas` returned any area whose rule named a via *or* a
track, so the via checks still treated the bars as via-free and couldn't measure the decision.

**What the skill does.** `blocking_areas(..., blocks=("via",))` for via questions; tracks only where
a check is about tracks.

## Measure parts by courtyard or pads, never by a footprint's bounding box

**What happened (2026-11-02).** `hot_loop.py` measured a feedback resistor's distance from the switch
node with `FOOTPRINT.GetBoundingBox()`, which includes the reference and value text: an 0402 read
4.1 x 4 mm, and R304 read 0.0 mm from U303's SW pin, which it is 1.5 mm from (courtyard to pad).
The run reported it as touching the switch node before the number was checked.

**What the skill does.** Footprints are measured by their courtyard (their pads when they have none);
a surprising number is checked against the courtyard or pad geometry before it reaches a page.
