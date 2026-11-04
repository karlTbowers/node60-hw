#!/bin/zsh
# judge_route.sh PLACEMENT.kicad_pcb OUTDIR -- fast-route a placement at Node60's own rules and grade it
# (pcb-placement skill, stage 5). Sizes follow node60.kicad_dru's D12 rules (2026-11-03): 0.1/0.1 mm
# only in U401's and U501's fan-out (ESCAPE_* areas), 0.15 mm track and clearance everywhere else,
# 0.45/0.25 mm via; signals on F.Cu and B.Cu only, the inner layers planes (D12-1 A: In1 and In4
# GND, In2 and In3 VBAT_PROT); the T1S pair is never ripped by later passes, and no rip-anything
# pass (route_open.sh retired, D12-7). --fab-tier standard and --escalation off everywhere,
# so no step goes below the board's sizes: a net that can't route at them stays open and shows. The busbar areas get native track keep-outs (D01: tented vias allowed). J901 is on
# its own net, VBAT_IN_DOWNSTREAM, joined to VBAT_IN only by the busbar net tie BB901 (D02), so the
# router lays no copper in parallel with the bar. Graded by grade_route.py against node60.kicad_pro/.kicad_dru.
set -e
IN=$1; OUT=$2
HERE=${0:A:h}; REPO=${HERE:h:h}
KRT=~/Dev/KiCadRoutingTools
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3   # pcbnew: grading
KRT_PY=${KRT_PY:-$KP}   # a Python with numpy, scipy and shapely for the routing steps
FAB=(--fab-overrides $HERE/node60_fab.txt)
mkdir -p $OUT
python3 - $IN $OUT/s0.kicad_pcb <<'PY'
import re, sys
s = open(sys.argv[1]).read()
for m in reversed(list(re.finditer(r'\n\t\(footprint "(?:DropOut_Busbar:)?Busbar_[^"]*"[\s\S]*?\n\t\)', s))):   # bar footprints out (KRT counts them as overlapping the REDCUBEs)
    s = s[:m.start()] + s[m.end():]
for m in reversed(list(re.finditer(r'\n\t\(zone\n[\s\S]*?\n\t\)', s))):                      # bar areas: no tracks
    z = m.group(0)
    if '(name "BUSBAR_' in z:
        s = s[:m.start()] + z.replace("(tracks allowed)", "(tracks not_allowed)") + s[m.end():]
open(sys.argv[2], "w").write(s)
PY
cp $REPO/node60.kicad_pro $OUT/s0.kicad_pro; cp $REPO/node60.kicad_dru $OUT/s0.kicad_dru
cd $KRT
L=(--layers F.Cu In1.Cu In2.Cu In3.Cu In4.Cu B.Cu --layer-costs 1.0 -1.0 -1.0 -1.0 -1.0 1.0)
SZ=(--clearance 0.15 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off $FAB)
step() { local n=$1; shift; echo "== $n: $*" >> $OUT/chain.log; $KRT_PY -X utf8 "$@" >> $OUT/chain.log 2>&1; }
step planes py_router/route_planes.py $OUT/s0.kicad_pcb $OUT/s1.kicad_pcb --nets GND VBAT_PROT VBAT_PROT GND --plane-layers In1.Cu In2.Cu In3.Cu In4.Cu --clearance 0.15 --escalation off $FAB
cp $OUT/s0.kicad_pro $OUT/s1.kicad_pro; cp $OUT/s0.kicad_dru $OUT/s1.kicad_dru
ESC=(--clearance 0.1 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off $FAB)
step fanout_U401 py_router/bga_fanout.py $OUT/s1.kicad_pcb --component U401 --nets "*" "!GND" "!VBAT_PROT" "!*FXOSC*" --output $OUT/s2.kicad_pcb --track-width 0.1 $ESC $L
for i in U201 U302 U303; do
  step fanout_$i py_router/qfn_fanout.py $OUT/s2.kicad_pcb --component $i --output $OUT/s2.kicad_pcb --track-width 0.15 $SZ || true
done
step fanout_U501 py_router/qfn_fanout.py $OUT/s2.kicad_pcb --component U501 --output $OUT/s2.kicad_pcb --track-width 0.1 $ESC || true
step decap py_placer/place_fanout_clearance.py $OUT/s2.kicad_pcb $OUT/s3.kicad_pcb --clearance 0.15
# The MCU crystal's nets route on B.Cu only, with no via (NXP S32K3 HDG §3.2; node60.kicad_dru), before anything else claims the area
step crystal py_router/route.py $OUT/s3.kicad_pcb $OUT/s3.kicad_pcb --nets '*FXOSC*' --clearance 0.15 --clearance-ceiling 0.15 --track-width 0.15 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off $FAB --layers B.Cu
step diff py_router/route_diff.py $OUT/s3.kicad_pcb $OUT/s4.kicad_pcb --nets /T1S/T1S_CMC_P /T1S/T1S_CMC_N /T1S/T1S_PHY_P /T1S/T1S_PHY_N /T1S_P /T1S_N --track-width 0.165 --diff-pair-gap 0.15 --clearance 0.15 --clearance-ceiling 0.15 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off $FAB $L
# After the T1S pair (pins 30-31, same edge), which has priority.
# The PHY's south pins 26-29 (RBIAS, REFCLK, 3V3_MAIN) sit at 0.5 mm pitch; the bulk passes lose one of
# them each run though each reads PASSABLE. Route the two signals first, before anything crowds them
# (3V3_MAIN first as well was worse: 3 open, the T1S pair among them).
step phy_first py_router/route.py $OUT/s4.kicad_pcb $OUT/s4.kicad_pcb --nets /T1S/T1S_REFCLK /T1S/T1S_RBIAS --clearance 0.15 --clearance-ceiling 0.15 --track-width 0.15 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off $FAB $L
PW=(--power-nets 'GN[D/]' 'VBAT_PRO[T/]' /VBAT_IN "/Power entry/VBAT_D" 'VBAT_FIL[T/]' "/Power entry/VBAT_Q2D" '/OUT?' 'VDDAU_AO[N/]' '3V3_MAI[N/]' '1V5_COR[E/]' "/Outputs 1-2/SW_VDD" "/Outputs 5-6/SW_VDD" "/Outputs 3-4/SW_VDD" /Regulators/VDDAU_AON_REG '/Regulators/*_SW' --power-nets-widths 0.4 0.6 0.6 0.6 0.4 0.6 0.6 0.4 0.4 0.4 0.3 0.3 0.3 0.3 0.6)
step route py_router/route.py $OUT/s4.kicad_pcb $OUT/s5.kicad_pcb --nets "*" --no-bga-zones --clearance 0.15 --clearance-ceiling 0.15 --track-width 0.15 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off $FAB --max-ripup 5 $PW $L
step route_p2 py_router/route.py $OUT/s5.kicad_pcb $OUT/s6.kicad_pcb --nets "*" --no-bga-zones --clearance 0.15 --clearance-ceiling 0.15 --track-width 0.15 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off $FAB --max-ripup 5 $PW $L
cp $OUT/s6.kicad_pcb $OUT/s6_before_p3.kicad_pcb
cd $REPO
$KP .claude/skills/pcb-placement/scripts/grade_route.py $OUT/s6.kicad_pcb --project node60.kicad_pro --rules node60.kicad_dru --json $OUT/rules.json > $OUT/grade.txt 2>&1 || true
grep -v -E "wxApp|Fontconfig|Debug|assert" $OUT/grade.txt | tail -15
