#!/bin/zsh
# route_rmii.sh BOARD OUTDIR -- route only the PHY-to-MCU link (RMII and MDIO) on a placement, with
# KRT at the board's own sizes (Node60, 2026-11-05; user: "route JUST the RMII interface").
#
# 1. judge_route.sh prepares the board and fans out U401 and U501 (STOP_AFTER=phy_first), as the
#    placement judge does: busbar footprints out, ring pads round, the T1S pairs and the crystal routed.
# 2. The UNDER_Y401 / UNDER_Y501 rule areas become via keep-outs on the router's copy: node60.kicad_dru
#    allows only the crystals' own nets and GND on B.Cu and In4.Cu under them, and a via passes through
#    both, but KRT models that rule for tracks only.
# 3. MDIO and MDC route first (alone they always find a way; last, the RMII lines cage them), then the
#    eight RMII lines with REF_CLK. 0.35/0.20 mm vias (the board's preset; a via fits a BGA cell),
#    0.15 mm track and clearance, F.Cu, In2.Cu (window north of y 70) and B.Cu.
# The result (OUTDIR/v2.kicad_pcb) is the router's copy; transplant_nets.py puts only these nets'
# copper on a real board, and KiCad DRC with the real rules judges it.
set -e
IN=$1; OUT=$2
HERE=${0:A:h}; RUN=${HERE:h}
KRT=~/Dev/KiCadRoutingTools
PY=${KRT_PY:-/Users/karl/.cache/dropout/krt-venv/bin/python}
mkdir -p $OUT
STOP_AFTER=phy_first KRT_PY=$PY zsh $RUN/judge_route.sh $IN $OUT > $OUT/prep.log 2>&1
python3 - $OUT/s4.kicad_pcb $OUT/s4v.kicad_pcb <<'PY'
import re, sys
s = open(sys.argv[1]).read(); out = []; last = 0
for m in re.finditer(r'\n\t\(zone\n[\s\S]*?\n\t\)', s):
    z = m.group(0)
    if '(name "UNDER_Y501")' in z or '(name "UNDER_Y401")' in z:
        out += [s[last:m.start()], z.replace('(vias allowed)', '(vias not_allowed)')]; last = m.end()
out.append(s[last:]); open(sys.argv[2], 'w').write(''.join(out))
PY
for x in pro dru; do cp $OUT/s4.kicad_$x $OUT/s4v.kicad_$x; cp $OUT/s4.kicad_$x $OUT/v1.kicad_$x; done
COMMON=(--no-bga-zones --clearance 0.15 --clearance-ceiling 0.15 --track-width 0.15 --via-size 0.35 --via-drill 0.2
        --fab-tier standard --escalation off --fab-overrides $HERE/fab.txt --max-ripup 5
        --layers F.Cu In1.Cu In2.Cu In3.Cu In4.Cu B.Cu --layer-costs 1.0 -1.0 1.0 -1.0 -1.0 1.0)
cd $KRT
$PY -X utf8 py_router/route.py $OUT/s4v.kicad_pcb $OUT/v1.kicad_pcb --nets /MDIO0_T1S_MDIO /MDIO0_T1S_MDC ${COMMON[@]} > $OUT/v1.log 2>&1
$PY -X utf8 py_router/route.py $OUT/v1.kicad_pcb $OUT/v2.kicad_pcb --nets /RMII0_T1S_TXD0 /RMII0_T1S_TXD1 /RMII0_T1S_TX_EN \
    /RMII0_T1S_RXD0 /RMII0_T1S_RXD1 /RMII0_T1S_CRS_DV /RMII0_T1S_RX_ER /RMII0_T1S_REF_CLK ${COMMON[@]} > $OUT/v2.log 2>&1
grep -h "Single-ended" $OUT/v1.log $OUT/v2.log | tail -2
grep -o '"pad_pairs_open": {[^}]*}' $OUT/v2.log | tail -1
