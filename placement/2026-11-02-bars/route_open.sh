#!/bin/zsh
# route_open.sh BOARD LOG [PASSES] [FIRST_NETS...] -- targeted rip-up passes on the nets still open.
# Each pass routes the nets the previous pass (or LOG's last JSON_SUMMARY) left open, with rip-up of
# any neighbour allowed, in place on BOARD; stops when nothing is open or after PASSES (default 3).
# The bulk passes lose a different few PHY nets each run (REFCLK, IRQ_L, RBIAS, a 3V3_MAIN pad) though
# every one reads PASSABLE; one targeted pass closes most, a second the one it breaks.
B=$1; LOG=$2; PASSES=${3:-3}; shift 3 2>/dev/null || shift $#
KRT=${KRT_PY:?set KRT_PY to a Python with numpy, scipy and shapely}
HERE=${0:A:h}
L=(--layers F.Cu In1.Cu In2.Cu In3.Cu In4.Cu B.Cu --layer-costs 1.0 -1.0 1.0 1.0 -1.0 1.0)
open_nets() { python3 $HERE/open_nets.py $1 }
OPEN=("$@"); [ ${#OPEN} = 0 ] && OPEN=(${(f)"$(open_nets $LOG)"})
cd /Users/karl/Dev/KiCadRoutingTools
for p in $(seq 1 $PASSES); do
  [ ${#OPEN} = 0 ] && { echo "route_open: nothing open after $((p-1)) pass(es)"; exit 0; }
  echo "route_open pass $p: ${OPEN[*]}"
  $KRT -X utf8 py_router/route.py $B $B --nets $OPEN --no-bga-zones --clearance 0.15 --clearance-ceiling 0.15 \
    --track-width 0.1 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off \
    --fab-overrides $HERE/node60_fab.txt --max-ripup 40 --rip-existing-nets '*' $L > $LOG.p$p 2>&1
  OPEN=(${(f)"$(open_nets $LOG.p$p)"})
done
[ ${#OPEN} = 0 ] && echo "route_open: nothing open" || echo "route_open: still open: ${OPEN[*]}"
