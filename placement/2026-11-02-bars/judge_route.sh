#!/bin/zsh
# judge_route.sh PLACEMENT.kicad_pcb OUTDIR -- fast-route a placement at Node60's own rules and grade it
# (pcb-placement skill, stage 5). Sizes are the board's: 0.1 mm track (board minimum), 0.15 mm
# clearance (Default class), 0.45/0.25 mm via; --fab-tier standard and --escalation off everywhere,
# so no step goes below the board's sizes: a net that can't route at them stays open and shows. The busbar areas get native track keep-outs (D01: tented vias allowed), and J901's
# pad is moved to a stand-in net so the router lays no VBAT_IN copper beside the bar (the bar is
# that join; decision D02 pending). Graded by grade_route.py against node60.kicad_pro/.kicad_dru.
set -e
IN=$1; OUT=$2
HERE=${0:A:h}; REPO=${HERE:h:h}
KRT=~/Dev/KiCadRoutingTools
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
mkdir -p $OUT
python3 - $IN $OUT/s0.kicad_pcb <<'PY'
import re, sys
s = open(sys.argv[1]).read()
for m in reversed(list(re.finditer(r'\n\t\(footprint "Busbar_[^"]*"[\s\S]*?\n\t\)', s))):   # bar footprints out
    s = s[:m.start()] + s[m.end():]
for m in reversed(list(re.finditer(r'\n\t\(zone\n[\s\S]*?\n\t\)', s))):                      # bar areas: no tracks
    z = m.group(0)
    if '(name "BUSBAR_' in z:
        s = s[:m.start()] + z.replace("(tracks allowed)", "(tracks not_allowed)") + s[m.end():]
# J901's pad onto a stand-in net (declared after the last net), so nothing routes VBAT_IN to it
blk = re.search(r'\n\t\(footprint "[^"]+"(?:(?!\n\t\(footprint)[\s\S])*?\(property "Reference" "J901"[\s\S]*?\n\t\)', s)
j = blk.group(0).replace('(net "/VBAT_IN")', '(net "JUDGE_J901_BAR")')
s = s[:blk.start()] + j + s[blk.end():]
open(sys.argv[2], "w").write(s)
PY
cp $REPO/node60.kicad_pro $OUT/s0.kicad_pro; cp $REPO/node60.kicad_dru $OUT/s0.kicad_dru
cd $KRT
L=(--layers F.Cu In1.Cu In2.Cu In3.Cu In4.Cu B.Cu --layer-costs 1.0 -1.0 1.0 1.0 -1.0 1.0)
SZ=(--clearance 0.15 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off)
step() { local n=$1; shift; echo "== $n: $*" >> $OUT/chain.log; $KP -X utf8 "$@" >> $OUT/chain.log 2>&1; }
step planes py_router/route_planes.py $OUT/s0.kicad_pcb $OUT/s1.kicad_pcb --nets GND VBAT_PROT --plane-layers In1.Cu In4.Cu --clearance 0.15 --escalation off
cp $OUT/s0.kicad_pro $OUT/s1.kicad_pro; cp $OUT/s0.kicad_dru $OUT/s1.kicad_dru
step fanout_U401 py_router/bga_fanout.py $OUT/s1.kicad_pcb --component U401 --nets "*" "!GND" "!VBAT_PROT" --output $OUT/s2.kicad_pcb --track-width 0.1 $SZ $L
for i in U201 U302 U303 U501; do
  step fanout_$i py_router/qfn_fanout.py $OUT/s2.kicad_pcb --component $i --output $OUT/s2.kicad_pcb $SZ || true
done
step decap py_placer/place_fanout_clearance.py $OUT/s2.kicad_pcb $OUT/s3.kicad_pcb --clearance 0.15
step diff py_router/route_diff.py $OUT/s3.kicad_pcb $OUT/s4.kicad_pcb --nets /T1S/T1S_CMC_P /T1S/T1S_CMC_N /T1S/T1S_PHY_P /T1S/T1S_PHY_N /T1S_P /T1S_N --track-width 0.165 --diff-pair-gap 0.15 --clearance 0.15 --clearance-ceiling 0.15 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off $L
PW=(--power-nets 'GN[D/]' 'VBAT_PRO[T/]' /VBAT_IN "/Power entry/VBAT_D" 'VBAT_FIL[T/]' "/Power entry/VBAT_Q2D" 'VDDAU_AO[N/]' "/Outputs 1-2/SW_VDD" "/Outputs 5-6/SW_VDD" "/Outputs 3-4/SW_VDD" /Regulators/VDDAU_AON_REG --power-nets-widths 0.3 0.3 0.3 0.3 0.3 0.3 0.3 0.3 0.3 0.3 0.3)
step route py_router/route.py $OUT/s4.kicad_pcb $OUT/s5.kicad_pcb --nets "*" --no-bga-zones --clearance 0.15 --clearance-ceiling 0.15 --track-width 0.1 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off --max-ripup 5 --rip-existing-nets /T1S_N /T1S_P $PW $L
step route_p2 py_router/route.py $OUT/s5.kicad_pcb $OUT/s6.kicad_pcb --nets "*" --no-bga-zones --clearance 0.15 --clearance-ceiling 0.15 --track-width 0.1 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off --max-ripup 5 $PW $L
cd $REPO
$KP .claude/skills/pcb-placement/scripts/grade_route.py $OUT/s6.kicad_pcb --project node60.kicad_pro --rules node60.kicad_dru --json $OUT/rules.json > $OUT/grade.txt 2>&1 || true
grep -v -E "wxApp|Fontconfig|Debug|assert" $OUT/grade.txt | tail -15
