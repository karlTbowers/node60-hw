#!/bin/zsh
# route_clock.sh BOARD OUTDIR [extra route.py args for the clock step] -- the RMII link with its
# clock first (Node60, 2026-11-05; D27, the RMII clock skew). As route_rmii.sh, but the judge stops
# after the T1S pairs (STOP_AFTER=diff) and the order is: RBIAS; the three clock nets (OSC_OUT,
# the PHY's REFCLK, the MCU's REF_CLK), with any extra args (a length-match group); the three TX
# lines; MDIO and MDC; the four RX lines. The T1S trunk's corridor on F.Cu is kept free of tracks and vias.
set -e
IN=$1; OUT=$2; shift 2
HERE=${0:A:h}; RUN=${HERE:h}
KRT=~/Dev/KiCadRoutingTools
PY=${KRT_PY:-/Users/karl/.cache/dropout/krt-venv/bin/python}
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
mkdir -p $OUT
STOP_AFTER=diff KRT_PY=$PY zsh $RUN/judge_route.sh $IN $OUT > $OUT/prep.log 2>&1
python3 - $OUT/s4.kicad_pcb $OUT/r0.kicad_pcb <<'PY'
import re, sys
s = open(sys.argv[1]).read(); out = []; last = 0
for m in re.finditer(r'\n\t\(zone\n[\s\S]*?\n\t\)', s):
    z = m.group(0)
    if '(name "UNDER_Y501")' in z or '(name "UNDER_Y401")' in z:
        out += [s[last:m.start()], z.replace('(vias allowed)', '(vias not_allowed)')]; last = m.end()
out.append(s[last:]); open(sys.argv[2], 'w').write(''.join(out))
PY
# The T1S trunk's corridor on F.Cu (y 44.8-47.2 between the connectors) closed to tracks and vias:
# the user hand-routes the pair there (D27: an RX line crossed it, a via sat in pin 27 on it)
$KP - $OUT/r0.kicad_pcb <<'PY'
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName("TRUNK_KEEPOUT_F")
ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); z.SetLayerSet(ls)
z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowPads(False)
z.SetDoNotAllowZoneFills(False); z.SetDoNotAllowFootprints(False)
o = z.Outline(); o.RemoveAllContours(); o.NewOutline()
for x, y in ((138.8, 44.8), (171.2, 44.8), (171.2, 47.2), (138.8, 47.2)):
    o.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
b.Add(z); b.Save(sys.argv[1])
PY
for i in 0 1 2 3 4 5; do for x in pro dru; do cp $OUT/s4.kicad_$x $OUT/r$i.kicad_$x; done; done
COMMON=(--no-bga-zones --clearance 0.15 --clearance-ceiling 0.15 --track-width 0.15 --via-size 0.35 --via-drill 0.2
        --fab-tier standard --escalation off --fab-overrides $HERE/fab.txt --max-ripup 5
        --layers F.Cu In1.Cu In2.Cu In3.Cu In4.Cu B.Cu --layer-costs 1.0 -1.0 1.0 -1.0 -1.0 1.0)
cd $KRT
r() { local i=$1 o=$2; shift 2; $PY -X utf8 py_router/route.py $OUT/r$i.kicad_pcb $OUT/r$o.kicad_pcb ${COMMON[@]} "$@" > $OUT/r$o.log 2>&1 || true; grep -h "Single-ended" $OUT/r$o.log | tail -1; }
r 0 1 --nets /T1S/T1S_RBIAS
r 1 2 --nets /T1S/T1S_OSC_OUT /T1S/T1S_REFCLK /RMII0_T1S_REF_CLK "$@"
r 2 3 --nets /RMII0_T1S_TXD0 /RMII0_T1S_TXD1 /RMII0_T1S_TX_EN
r 3 4 --nets /MDIO0_T1S_MDIO /MDIO0_T1S_MDC
r 4 5 --nets /RMII0_T1S_RXD0 /RMII0_T1S_RXD1 /RMII0_T1S_CRS_DV /RMII0_T1S_RX_ER
grep -o '"pad_pairs_open": {[^}]*}' $OUT/r5.log | tail -1
