#!/bin/zsh
# build_term.sh BOARD OUTDIR -- route the relay's termination and coil nets with KRT (Node60, 2026-11-05).
# Two passes, so KRT sees the T1S-class legs as routed copper when it routes the rest: (1) the four legs
# K501 to R516-R519 (T1S_*_DROP, T1S_*_END, class T1S_100R); (2) the centre tap TERM_CT, the coil (TERM_COIL_S/R)
# and its drive lines from U401 (TERM_DROP/END), with route_nets.sh's via keep-outs round every T1S track
# and via (KRT keeps the T1S rule track to track only). OUTDIR/m2 is the result, zones refilled, DRC'd.
set -e
IN=${1:A}; OUT=${2:A}
HERE=${0:A:h}
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
LEGS=(/T1S/T1S_P_DROP /T1S/T1S_P_END /T1S/T1S_N_DROP /T1S/T1S_N_END)
REST=(/T1S/T1S_TERM_CT /T1S/T1S_TERM_COIL_S /T1S/T1S_TERM_COIL_R /T1S_TERM_DROP /T1S_TERM_END)
mkdir -p $OUT
cp $IN $OUT/m0.kicad_pcb; for x in pro dru; do cp ${IN:r}.kicad_$x $OUT/m0.kicad_$x; cp ${IN:r}.kicad_$x $OUT/m1.kicad_$x; cp ${IN:r}.kicad_$x $OUT/m2.kicad_$x; done
rm -rf $OUT/ra $OUT/rb
zsh $HERE/route_nets.sh $OUT/m0.kicad_pcb $OUT/ra $LEGS 2>/dev/null | tail -1
$KP $HERE/../rmii/transplant_nets.py $OUT/ra/r1.kicad_pcb $OUT/m0.kicad_pcb $OUT/m1.kicad_pcb $LEGS --lock 2>/dev/null
zsh $HERE/route_nets.sh $OUT/m1.kicad_pcb $OUT/rb $REST 2>/dev/null | tail -1
$KP $HERE/../rmii/transplant_nets.py $OUT/rb/r1.kicad_pcb $OUT/m1.kicad_pcb $OUT/m2.kicad_pcb $REST --lock 2>/dev/null
(cd $OUT && kicad-cli pcb drc --severity-all --refill-zones --save-board --format json -o drc_m2.json m2.kicad_pcb >/dev/null 2>&1) || true
