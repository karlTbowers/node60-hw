#!/bin/zsh
# build_trial.sh BOARD OUTDIR -- the hand-routed T1S line on a copy of BOARD (D28): spec -> draw -> TXD0
# re-routed by KRT -> power vias by draw_power.py -> zones refilled and DRC by kicad-cli. OUTDIR/t4 is the result.
set -e
IN=${1:A}; OUT=${2:A}
HERE=${0:A:h}; ROOT=${HERE:h:h:h}
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
mkdir -p $OUT
# T1S_SWAP=noswap draws D28's route (FL501/K501 as before D31) into OUTDIR; the default is the board's
SPEC=$HERE/t1s_route.json; [[ -n "${T1S_SWAP:-}" ]] && SPEC=$OUT/t1s_route.json
python3 $HERE/spec_t1s.py $SPEC 149.0 270 ${T1S_SWAP:-swap}
$KP $HERE/draw_t1s.py $IN $SPEC $OUT/t2.kicad_pcb 2>/dev/null
cp ${IN:r}.kicad_pro $OUT/t2.kicad_pro
python3 $HERE/rules_t1s.py ${IN:r}.kicad_dru $OUT/t2.kicad_dru
rm -rf $OUT/rt; zsh $HERE/route_txd0.sh $OUT/t2.kicad_pcb $OUT/rt 2>/dev/null | tail -1
$KP $HERE/../rmii/transplant_nets.py $OUT/rt/r1.kicad_pcb $OUT/t2.kicad_pcb $OUT/t3.kicad_pcb /RMII0_T1S_TXD0 --lock 2>/dev/null
cp $OUT/t3.kicad_pcb $OUT/t4.kicad_pcb; for x in pro dru; do cp $OUT/t2.kicad_$x $OUT/t4.kicad_$x; done
$KP $ROOT/scripts/draw_power.py $OUT/t4.kicad_pcb $HERE/../power/power_shapes.json 2>/dev/null | grep -i "NO SITE\|SHORT\|via(s)" || true
(cd $OUT && kicad-cli pcb drc --severity-all --refill-zones --save-board --format json -o drc_t4.json t4.kicad_pcb >/dev/null 2>&1) || true
