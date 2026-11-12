#!/bin/zsh
# build.sh NAME SPEC.json [SPEC2.json ...] -- one study attempt on a copy of main's board:
# copy (with project and rules), apply the spec(s), refill and DRC with the board's own rules.
# Writes boards/NAME.kicad_pcb, boards/NAME.moves.json, boards/NAME.drc.json and prints the DRC counts.
set -e
HERE=${0:A:h}; REPO=${HERE:h:h}
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
NAME=$1; shift
mkdir -p $HERE/boards
python3 ~/Dev/KiCadRoutingTools/py_router/copy_board.py $REPO/node60.kicad_pcb $HERE/boards/$NAME.kicad_pcb >/dev/null
if (( $# )); then
  $KPY $HERE/apply_attempt.py $HERE/boards/$NAME.kicad_pcb "$@" $HERE/boards/$NAME.kicad_pcb --moves $HERE/boards/$NAME.moves.json 2>/dev/null || echo "(apply exited $?: pcbnew teardown; the board was saved if the stats line is above)"
fi
rm -f $HERE/boards/$NAME.drc.json
kicad-cli pcb drc --refill-zones --save-board --severity-all --format json -o $HERE/boards/$NAME.drc.json $HERE/boards/$NAME.kicad_pcb >/dev/null 2>&1 || true
python3 $HERE/drc_counts.py $HERE/boards/$NAME.drc.json
