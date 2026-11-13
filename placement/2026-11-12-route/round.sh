#!/bin/zsh
# round.sh DIR IN OUT [--supply] [extra gen_jobs flags] -- one repair round on DIR/IN.kicad_pcb: jobs from its DRC
# report (gen_jobs.py), mini_route.py, the result applied as DIR/OUT.kicad_pcb and graded by KiCad.
# The jobs and the spec are kept as hand/OUT.jobs.json and hand/OUT.json.
set -e
D=$1; I=$2; O=$3; shift 3
W=${0:A:h}; S=${W:h}/2026-11-12-passives; R=${W:h}/2026-11-02-bars
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
VPY=${KRT_PY:-/Users/karl/.cache/dropout/krt-venv/bin/python}
[[ -f $D/$I.drc.json ]] || kicad-cli pcb drc --refill-zones --save-board --severity-all --format json -o $D/$I.drc.json $D/$I.kicad_pcb >/dev/null 2>&1 || true
$KPY $S/dump_board.py $D/$I.kicad_pcb $D/$I.json 2>/dev/null | tail -1
$KPY $R/power/joins/export_copper.py $D/$I.kicad_pcb $D/$I.copper.json 2>/dev/null | tail -1
python3 $W/gen_jobs.py $D/$I.drc.json $D/$I.json $W/hand/$O.jobs.json ${@:---signal}
$VPY $W/mini_route.py $D/$I.copper.json $W/hand/$O.jobs.json $W/hand/$O.json | tee $D/$O.route.txt | grep -c "^routed" || true
grep "^FAILED" $D/$O.route.txt || true
for x in pro dru; do cp $D/$I.kicad_$x $D/$O.kicad_$x; done
$KPY $S/apply_attempt.py $D/$I.kicad_pcb $W/hand/$O.json $D/$O.kicad_pcb 2>&1 | grep -v "Debug\|assert\|swig" | tail -1
kicad-cli pcb drc --refill-zones --save-board --severity-all --format json -o $D/$O.drc.json $D/$O.kicad_pcb >/dev/null 2>&1 || true
python3 $S/drc_counts.py $D/$O.drc.json | head -2
