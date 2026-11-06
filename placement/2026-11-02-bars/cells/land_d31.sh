#!/bin/zsh
# land_d31.sh WORKDIR -- D31 onto node60.kicad_pcb (user: "Land both", 2026-11-06), from the repo root.
# The schematic edits (edit_sheets_d31.py) come first; this takes the pads' nets from the schematic, turns
# the three output switches (turn_cells.py --keep-nets), adds the cells' joins (d31_cell_joins.json) to
# power_shapes.json, draws the T1S line with FL501/K501 swapped and TXD0 and the power vias
# (t1s/build_trial.sh), routes the relay's termination (t1s/build_term.sh), and writes the board back.
set -e
W=${1:A}; ROOT=$PWD; RUN=$ROOT/placement/2026-11-02-bars
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
export KRT_PY=${KRT_PY:-/Users/karl/.cache/dropout/krt-venv/bin/python}
mkdir -p $W
kicad-cli sch export netlist --format kicadsexpr -o $W/node60.net node60.kicad_sch >/dev/null 2>&1
$KP scripts/apply_netlist.py node60.kicad_pcb $W/node60.net $W/a.kicad_pcb 2>/dev/null | tail -1
$KP $RUN/cells/turn_cells.py $W/a.kicad_pcb $RUN/power/power_shapes.json $W/b.kicad_pcb $W/spec_turned.json --keep-nets 2>/dev/null | grep -E "cleared|dropped"
python3 $RUN/power/joins/merge_plan.py $W/spec_turned.json $RUN/cells/d31_cell_joins.json $RUN/power/power_shapes.json | tail -1
for x in pro dru; do cp node60.kicad_$x $W/b.kicad_$x; done
zsh $RUN/t1s/build_trial.sh $W/b.kicad_pcb $W/tr 2>&1 | grep -E "SHORT|via\(s\)|tracks" || true
zsh $RUN/t1s/build_term.sh $W/tr/t4.kicad_pcb $W/term 2>&1 | grep -E "routed|tracks" || true
cp $W/term/m2.kicad_pcb node60.kicad_pcb
kicad-cli pcb drc --refill-zones --save-board -o /dev/null node60.kicad_pcb >/dev/null 2>&1 || true
git checkout -- node60.kicad_pro
echo "node60.kicad_pcb written"
