#!/bin/zsh
# checks.sh [BASE.kicad_pcb] -- the checks of the run on the repo's node60.kicad_pcb, outputs in checks/; with BASE
# (main's board, zones filled) the before/after pairs. Run from anywhere; takes about five minutes.
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
H=${0:A:h}; ROOT=$(git -C $H rev-parse --show-toplevel); O=$H/checks; R=$ROOT/placement/2026-11-02-bars; F='swig|Debug|assert'
cd $ROOT; mkdir -p $O
$KPY $R/rules/prove_rules.py node60.kicad_pcb 2>&1 | grep -Ev $F > $O/prove_rules.txt
$KPY $R/rules/t1s_stubs.py node60.kicad_pcb 2>&1 | grep -Ev $F > $O/t1s_stubs.txt
$KPY $R/rmii/trunk_check.py node60.kicad_pcb --all 2>&1 | grep -Ev $F > $O/trunk_check.txt
$KPY $R/rmii/rmii_timing.py node60.kicad_pcb 2>&1 | grep -Ev $F > $O/rmii_timing.txt
$KPY .claude/skills/pcb-placement/scripts/block_poses.py check node60.kicad_pcb $R/blocks/*.poses.json 2>&1 | grep -Ev $F > $O/block_poses.txt
zsh placement/2026-11-12-route/measure_paths.sh node60.kicad_pcb > $O/measure_paths.txt 2>&1
$KPY placement/2026-11-12-route/pour_crossings.py node60.kicad_pcb $1 2>&1 | grep -Ev $F > $O/pour_crossings.txt
if [[ -n $1 ]]; then
  $KPY $H/plane_pieces.py node60.kicad_pcb $1 2>&1 | grep -Ev $F > $O/plane_pieces.txt
  $KPY $R/rules/t1s_stubs.py $1 2>&1 | grep -Ev $F > $O/t1s_stubs.before.txt
  $KPY $R/rmii/rmii_timing.py $1 2>&1 | grep -Ev $F > $O/rmii_timing.before.txt
  zsh placement/2026-11-12-route/measure_paths.sh $1 > $O/measure_paths.before.txt 2>&1
fi
git checkout node60.kicad_pro 2>/dev/null
tail -1 $O/prove_rules.txt; tail -1 $O/trunk_check.txt; tail -1 $O/rmii_timing.txt; grep -c "0 off" $O/block_poses.txt; grep -v " 0 off" $O/block_poses.txt
[[ -n $1 ]] && { diff <(tail -n +2 $O/t1s_stubs.before.txt) <(tail -n +2 $O/t1s_stubs.txt) && echo "T1S lengths as before"; diff $O/measure_paths.before.txt $O/measure_paths.txt && echo "supply paths as before"; cat $O/plane_pieces.txt }
