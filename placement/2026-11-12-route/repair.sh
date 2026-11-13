#!/bin/zsh
# repair.sh BOARD OUTDIR NET [NET ...] -- route a few nets on a routed board with KRT at 0.35/0.20 mm vias
# (the board's preset under U401) and the routing run's keep-outs (route_hook.py, HOOK_REPAIR=1). As
# t1s/route_nets.sh, but the keep-outs follow the T1S tracks instead of boxing them, and U401's caps stay put.
# No rip-up (MAXRIP=0): copper already on the board stays. TW overrides the 0.15 mm track. The result is OUTDIR/r1.kicad_pcb, the router's copy: transplant_new.py
# --only puts those nets' copper on the real board.
set -e
IN=$1; OUT=$2; shift 2
HERE=${0:A:h}; RUN=${HERE:h}/2026-11-02-bars
KRT=~/Dev/KiCadRoutingTools
PY=${KRT_PY:-/Users/karl/.cache/dropout/krt-venv/bin/python}
mkdir -p $OUT
STOP_AFTER=crystal KEEP_DECAPS=1 HOOK_REPAIR=1 S0_HOOK=$HERE/route_hook.py KRT_PY=$PY zsh $RUN/judge_route.sh $IN $OUT > $OUT/prep.log 2>&1
for x in pro dru; do cp $OUT/s3.kicad_$x $OUT/r1.kicad_$x; done
cd $KRT
export KICAD_POUR_GUARD=${KICAD_POUR_GUARD:-0}   # short signals may cross a supply pour on B.Cu; the pour retreats
$PY -X utf8 py_router/route.py $OUT/s3.kicad_pcb $OUT/r1.kicad_pcb --nets "$@" --no-bga-zones --clearance 0.15 --clearance-ceiling 0.15 \
    --track-width ${TW:-0.15} --via-size ${VIA:-0.35} --via-drill ${DRILL:-0.2} --fab-tier standard --escalation off --fab-overrides ${FAB:-$RUN/rmii/fab.txt} --max-ripup ${MAXRIP:-0} \
    --layers F.Cu In1.Cu In2.Cu In3.Cu In4.Cu B.Cu --layer-costs 1.0 -1.0 1.0 -1.0 -1.0 1.0 > $OUT/r1.log 2>&1 || true
grep -h "Single-ended" $OUT/r1.log | tail -1
