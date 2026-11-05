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
printf "step\twall_s\tuser_s\tsys_s\tmaxrss_mb\n" > $OUT/timing.tsv
RUN_T0=$(date +%s)
python3 - $IN $OUT/s0.kicad_pcb <<'PY'
import re, sys
s = open(sys.argv[1]).read()
for m in reversed(list(re.finditer(r'\n\t\(footprint "(?:DropOut_Busbar:)?Busbar_[^"]*"[\s\S]*?\n\t\)', s))):   # bar footprints out (KRT counts them as overlapping the REDCUBEs)
    s = s[:m.start()] + s[m.end():]
for m in reversed(list(re.finditer(r'\n\t\(zone\n[\s\S]*?\n\t\)', s))):                      # bar areas: no tracks
    z = m.group(0)
    if '(name "BUSBAR_' in z:
        s = s[:m.start()] + z.replace("(tracks allowed)", "(tracks not_allowed)") + s[m.end():]
# A custom pad whose only copper is one ring (gr_circle, fill no) -- the REDCUBE terminals' pad 1 --
# becomes a round pad of the ring's outer diameter at the ring's centre. KRT turns each ring into a
# ~190-vertex polygon and checks clearance to it edge by edge in Python, the route passes' hottest
# code (2026-11-03 profile); a round pad is one distance. Equivalent for routing: the ring encloses
# the terminal's own spigot hole and body, where nothing else can go. The real board is untouched
# and KiCad grades it. Set JUDGE_KEEP_RINGS=1 to route with the rings as drawn.
import math, os
def fp_angle(body):
    m = re.search(r'\n\t\t\(at [-\d.]+ [-\d.]+(?: ([-\d.]+))?\)', body)
    return float(m.group(1) or 0) if m else 0.0
def ring_to_circle(fp):
    def one(m):
        pad = m.group(0)
        prim = re.search(r'\(primitives\s*\(gr_circle\s*\(center ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)\s*\(width ([-\d.]+)\)\s*\(fill no\)\s*\)\s*\)', pad)
        at = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', pad)
        if not prim or not at:
            return pad
        cx, cy, ex, ey, w = map(float, prim.groups())
        x, y, a = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0)
        rel = math.radians(a - fp_angle(fp))          # the pad's turn within its footprint
        ox, oy = cx * math.cos(rel) + cy * math.sin(rel), -cx * math.sin(rel) + cy * math.cos(rel)
        d = 2 * (math.hypot(ex - cx, ey - cy) + w / 2)
        new = pad.replace(at.group(0), f"(at {x + ox:.4f} {y + oy:.4f}{' ' + at.group(3) if at.group(3) else ''})", 1)
        new = re.sub(r'\(size [-\d.]+ [-\d.]+\)', f"(size {d:.4f} {d:.4f})", new, count=1)
        new = new.replace(" smd custom", " smd circle", 1)
        new = re.sub(r'\s*\(options[\s\S]*?\n\t\t\t\)', "", new, count=1)
        new = re.sub(r'\s*\(primitives[\s\S]*?\n\t\t\t\)', "", new, count=1)
        return new
    return re.sub(r'\(pad "[^"]*" smd custom[\s\S]*?\n\t\t\)', one, fp)
if not os.environ.get("JUDGE_KEEP_RINGS"):
    n = 0
    out, last = [], 0
    for m in re.finditer(r'\n\t\(footprint "[^"]*"[\s\S]*?\n\t\)', s):
        fp = m.group(0)
        if "gr_circle" in fp and " smd custom" in fp:
            new = ring_to_circle(fp); n += new != fp
            out.append(s[last:m.start()]); out.append(new); last = m.end()
    out.append(s[last:]); s = "".join(out)
    print(f"ring pads drawn as round pads for the router: {n} footprint(s)", file=sys.stderr)
open(sys.argv[2], "w").write(s)
PY
# The router's copy of the project: the power classes (PWR_BATT, PWR_RAIL, SW_NODE) at the Default
# width. KiCad reads a class width as a default, not a floor, and they are for hand routing; KRT
# routes every net of a class at its width, so 0.4 mm on 3V3_MAIN into the BGA failed about 100 nets
# (2026-11-03, judge_v1cmp vs judge_v1old). Power widths here come from --power-nets below.
# grade_route.py grades against the real node60.kicad_pro and .kicad_dru.
python3 - $REPO/node60.kicad_pro $OUT/s0.kicad_pro <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
d = next(c for c in p["net_settings"]["classes"] if c["name"] == "Default")
for c in p["net_settings"]["classes"]:
    if c["name"] in ("PWR_BATT", "PWR_RAIL", "SW_NODE"):
        c["track_width"] = d["track_width"]
json.dump(p, open(sys.argv[2], "w"), indent=2)
PY
# The router's copy of the rules lacks two scoped clearance rules: KRT models 'T1S 0.75 mm from
# other nets' and 'Buck switch nodes 10 mm from the T1S line' by over-approximating per obstacle net,
# which walled off about 75 nets (2026-11-03: 113 failed with them, 35 without). KiCad still grades
# both against the real node60.kicad_dru; routing keeps them by hand-routing the T1S chain first.
python3 - $REPO/node60.kicad_dru $OUT/s0.kicad_dru <<'PY'
import re, sys
s = open(sys.argv[1]).read()
for n in ['Buck switch nodes 10 mm from the T1S line', 'T1S 0.75 mm from other nets']:
    s = re.sub(r'\(rule "' + re.escape(n) + r'"[\s\S]*?\)\)\n', '', s)
open(sys.argv[2], 'w').write(s)
PY
cd $KRT
# Layer roles. Defaults: D17 A (user, 2026-11-04): In1/In4 GND and In3 VBAT_PROT poured whole; In2
# open to tracks, which its rule areas on the board confine to the window north of y 70 mm (the
# VBAT_PROT pour south of it is left out here: tracks may not go there anyway). Override for
# variants, e.g. PLANE_NETS="GND VBAT_PROT VBAT_PROT GND" PLANE_LAYERS="In1.Cu In2.Cu In3.Cu In4.Cu"
# LAYER_COSTS="1.0 -1.0 -1.0 -1.0 -1.0 1.0" (D12-1 A; a negative cost = no tracks on that layer).
# Since D22 A (2026-11-04) In3 is split: VBAT_PROT in the power band, 3V3_MAIN north of y 70.8 and
# a 1V5_CORE island, drawn with their vias by scripts/draw_power.py from power_shapes.json. route_planes
# pours one net per layer, so In3 is left out of it and the board's own In3 zones and vias stay on
# the copy (judge a board that has them drawn). Not yet run in this form.
PLANE_NETS=${PLANE_NETS:-"GND GND"}
PLANE_LAYERS=${PLANE_LAYERS:-"In1.Cu In4.Cu"}
LAYER_COSTS=${LAYER_COSTS:-"1.0 -1.0 1.0 -1.0 -1.0 1.0"}
echo "layers: planes ${PLANE_NETS} on ${PLANE_LAYERS}; track costs F In1 In2 In3 In4 B = ${LAYER_COSTS}" >> $OUT/chain.log
L=(--layers F.Cu In1.Cu In2.Cu In3.Cu In4.Cu B.Cu --layer-costs ${=LAYER_COSTS})
SZ=(--clearance 0.15 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off $FAB)
# Every step is timed (user, 2026-11-03: find the design loop's bottlenecks): wall, user and system
# CPU seconds and peak resident memory per step, from /usr/bin/time -l, into $OUT/timing.tsv;
# rules/perf_report.py turns it into a table.
timed() {
  local n=$1; shift; local tf=$OUT/.time.$n rc=0
  /usr/bin/time -l -o $tf "$@" || rc=$?
  awk -v n="$n" '/ real /{w=$1;u=$3;s=$5} /maximum resident set size/{r=$1} END{printf "%s\t%.2f\t%.2f\t%.2f\t%.0f\n", n, w, u, s, r/1048576}' $tf >> $OUT/timing.tsv
  rm -f $tf; return $rc
}
# PROFILE=route,route_p2 (step names) runs those steps under cProfile into $OUT/<step>.prof.
step() {
  local n=$1; shift; echo "== $n: $*" >> $OUT/chain.log
  if [[ ",${PROFILE:-}," == *",$n,"* ]]; then
    timed $n $KRT_PY -X utf8 -m cProfile -o $OUT/$n.prof "$@" >> $OUT/chain.log 2>&1
  else
    timed $n $KRT_PY -X utf8 "$@" >> $OUT/chain.log 2>&1
  fi
}
# The board's own power zones (scripts/draw_power.py, 2026-11-04) replace this step once drawn.
if grep -q '(name "PWR_' $OUT/s0.kicad_pcb; then
  cp $OUT/s0.kicad_pcb $OUT/s1.kicad_pcb; echo "== planes: skipped, the board has its power zones" >> $OUT/chain.log
else
  step planes py_router/route_planes.py $OUT/s0.kicad_pcb $OUT/s1.kicad_pcb --nets ${=PLANE_NETS} --plane-layers ${=PLANE_LAYERS} --clearance 0.15 --escalation off $FAB
fi
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
# Power widths for the judge only (hand routing sets the real copper). Not 3V3_MAIN or 1V5_CORE:
# routed wide into U401's balls they block its escape (2026-11-03, about 110 nets failed at 0.4 mm).
PW=(--power-nets 'GN[D/]' 'VBAT_PRO[T/]' /VBAT_IN "/Power entry/VBAT_D" 'VBAT_FIL[T/]' "/Power entry/VBAT_Q2D" '/OUT?' 'VDDAU_AO[N/]' "/Outputs 1-2/SW_VDD" "/Outputs 5-6/SW_VDD" "/Outputs 3-4/SW_VDD" /Regulators/VDDAU_AON_REG --power-nets-widths 0.3 0.3 0.3 0.3 0.3 0.3 0.3 0.3 0.3 0.3 0.3 0.3)
step route py_router/route.py $OUT/s4.kicad_pcb $OUT/s5.kicad_pcb --nets "*" --no-bga-zones --clearance 0.15 --clearance-ceiling 0.15 --track-width 0.15 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off $FAB --max-ripup 5 $PW $L
step route_p2 py_router/route.py $OUT/s5.kicad_pcb $OUT/s6.kicad_pcb --nets "*" --no-bga-zones --clearance 0.15 --clearance-ceiling 0.15 --track-width 0.15 --via-size 0.45 --via-drill 0.25 --fab-tier standard --escalation off $FAB --max-ripup 5 $PW $L
cp $OUT/s6.kicad_pcb $OUT/s6_before_p3.kicad_pcb
cd $REPO
timed grade $KP .claude/skills/pcb-placement/scripts/grade_route.py $OUT/s6.kicad_pcb --project node60.kicad_pro --rules node60.kicad_dru --json $OUT/rules.json > $OUT/grade.txt 2>&1 || true
grep -v -E "wxApp|Fontconfig|Debug|assert" $OUT/grade.txt | tail -15
printf "TOTAL\t%d\t\t\t\n" $(( $(date +%s) - RUN_T0 )) >> $OUT/timing.tsv
