#!/bin/zsh
# apply_jobs.sh DIR IN OUT JOBS.json -- mini_route.py with a given job list on DIR/IN.kicad_pcb, applied as
# DIR/OUT.kicad_pcb and graded by KiCad (as round.sh, for jobs not made from the DRC report).
set -e
D=$1; I=$2; O=$3; J=$4
W=${0:A:h}; S=${W:h}/2026-11-12-passives; R=${W:h}/2026-11-02-bars
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
VPY=${KRT_PY:-/Users/karl/.cache/dropout/krt-venv/bin/python}
[[ -f $D/$I.copper.json ]] || $KPY $R/power/joins/export_copper.py $D/$I.kicad_pcb $D/$I.copper.json 2>/dev/null | tail -1
$VPY $W/mini_route.py $D/$I.copper.json $J $W/hand/$O.json | tee $D/$O.route.txt | grep -c "^routed" || true
grep "^FAILED" $D/$O.route.txt || true
for x in pro dru; do cp $D/$I.kicad_$x $D/$O.kicad_$x; done
$KPY $S/apply_attempt.py $D/$I.kicad_pcb $W/hand/$O.json $D/$O.kicad_pcb 2>&1 | grep -v "Debug\|assert\|swig" | tail -1
kicad-cli pcb drc --refill-zones --save-board --severity-all --format json -o $D/$O.drc.json $D/$O.kicad_pcb >/dev/null 2>&1 || true
python3 $W/count_open.py $D/$O.drc.json
