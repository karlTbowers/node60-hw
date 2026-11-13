#!/bin/zsh
# build.sh [BASE.kicad_pcb] -- the run from main's board (85a8ca5; default: git's) to the repo's node60.kicad_pcb:
# the netlist from the schematic as it is, plan.json applied (the 13 resistors, their cuts and joins), the symbols'
# fields synced onto the footprints, the reference texts of silk_refs.txt placed (silk_place.json is written by
# this step from the board as it then stands), node60.kicad_pro restored, zones refilled and KiCad's DRC with
# schematic parity run on the result. plan.json is the record of where the parts and the copper went; plan.py
# proposed it (see REPORT.md for the order of its runs).
set -e
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
VPY=${KRT_PY:-/Users/karl/.cache/dropout/krt-venv/bin/python}; KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
H=${0:A:h}; ROOT=$(git -C $H rev-parse --show-toplevel); F=$ROOT/placement/2026-11-13-kicad-happy-fixes; mkdir -p $H/work; cd $ROOT
if [[ -n $1 ]]; then cp $1 $H/work/base.kicad_pcb; else git show 85a8ca5:node60.kicad_pcb > $H/work/base.kicad_pcb; fi
$KC sch export netlist --format kicadsexpr -o $H/work/node60.net node60.kicad_sch >/dev/null 2>&1
$KPY $H/apply_plan.py $H/work/base.kicad_pcb $H/plan.json $H/work/node60.net node60.kicad_pcb 2>&1 | grep -Ev 'swig|Debug|assert' | grep "^R" 
$KPY scripts/sync_footprint_fields.py . 2>&1 | grep "fields added"
$KPY $F/silk_export.py node60.kicad_pcb $H/work/silk.json 2>/dev/null | tail -1
$VPY $H/silk_new.py $H/work/silk.json $H/silk_place.json $(cat $H/silk_refs.txt) | tail -1
$KPY $F/silk_apply.py node60.kicad_pcb $H/silk_place.json node60.kicad_pcb 2>/dev/null | tail -1
git checkout node60.kicad_pro
zsh $F/drc.sh node60.kicad_pcb $H/checks/kicad_drc.json
