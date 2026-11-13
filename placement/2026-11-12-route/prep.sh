#!/bin/zsh
# prep.sh OUTDIR -- the board the bulk route starts from (routing run 2026-11-12), from the repo root:
# main's board, the relay-termination drive lines ripped (they caged U401 ball E1), hand/h0.json (part
# nudges and supply-join changes), the In2 signal window and the power-only keep-outs of decision D17 A
# drawn again, then the stubborn nets pre-routed by mini_route.py (hand/h1.jobs.json -> hand/h1.json).
set -e
B=$1; W=${0:A:h}; S=${W:h}/2026-11-12-passives; R=${W:h}/2026-11-02-bars
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
VPY=${KRT_PY:-/Users/karl/.cache/dropout/krt-venv/bin/python}
mkdir -p $B
python3 ~/Dev/KiCadRoutingTools/py_router/copy_board.py node60.kicad_pcb $B/p0.kicad_pcb >/dev/null; git show HEAD:node60.kicad_pro > $B/p0.kicad_pro
$KPY $W/rip_nets.py $B/p0.kicad_pcb $B/p0.kicad_pcb /T1S_TERM_END /T1S_TERM_DROP 2>/dev/null | tail -1
$KPY $S/apply_attempt.py $B/p0.kicad_pcb $W/hand/h0.json $B/p0.kicad_pcb 2>&1 | grep -v "Debug\|assert\|swig" | tail -1
$KPY scripts/draw_rule_areas.py $B/p0.kicad_pcb --window In2.Cu:39.95,29.95,270.05,70.0 --power-only In1.Cu --power-only In3.Cu --power-only In4.Cu >/dev/null 2>&1
git show HEAD:node60.kicad_pro > $B/p0.kicad_pro
$KPY $R/power/joins/export_copper.py $B/p0.kicad_pcb $B/p0.copper.json 2>/dev/null | tail -1
$VPY $W/mini_route.py $B/p0.copper.json $W/hand/h1.jobs.json $W/hand/h1.json
for x in pro dru; do cp $B/p0.kicad_$x $B/p1.kicad_$x; done
$KPY $S/apply_attempt.py $B/p0.kicad_pcb $W/hand/h1.json $B/p1.kicad_pcb 2>&1 | grep -v "Debug\|assert\|swig" | tail -1
kicad-cli pcb drc --refill-zones --save-board --severity-all --format json -o $B/p1.drc.json $B/p1.kicad_pcb >/dev/null 2>&1 || true
python3 $S/drc_counts.py $B/p1.drc.json; python3 $W/drc_pairs.py $B/p1.drc.json | grep -v "open:"
