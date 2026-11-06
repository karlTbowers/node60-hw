#!/bin/zsh
# route_nets.sh BOARD OUTDIR NET [NET ...] -- route a few nets with KRT round the hand-routed T1S line
# (Node60, D28; generalised from route_txd0.sh for the relay termination, 2026-11-05).
# As rmii/route_clock.sh: the judge's preparation up to the crystal (no diff step: the T1S line is
# already drawn), UNDER_Y401/Y501 via-free and the trunk's F.Cu corridor closed for the router.
# TW, VIA, DRILL and FAB override the track width, via and fab file (power joins: 0.3 mm, 0.45/0.25).
set -e
IN=$1; OUT=$2; shift 2
HERE=${0:A:h}; RUN=${HERE:h}
KRT=~/Dev/KiCadRoutingTools
PY=${KRT_PY:-/Users/karl/.cache/dropout/krt-venv/bin/python}
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
mkdir -p $OUT
STOP_AFTER=crystal KRT_PY=$PY zsh $RUN/judge_route.sh $IN $OUT > $OUT/prep.log 2>&1
for x in pro dru; do cp $OUT/s3.kicad_$x $OUT/r0.kicad_$x; cp $OUT/s3.kicad_$x $OUT/r1.kicad_$x; done
python3 - $OUT/s3.kicad_pcb $OUT/r0.kicad_pcb <<'PY'
import re, sys
s = open(sys.argv[1]).read(); out = []; last = 0
for m in re.finditer(r'\n\t\(zone\n[\s\S]*?\n\t\)', s):
    z = m.group(0)
    if '(name "UNDER_Y501")' in z or '(name "UNDER_Y401")' in z:
        out += [s[last:m.start()], z.replace('(vias allowed)', '(vias not_allowed)')]; last = m.end()
out.append(s[last:]); open(sys.argv[2], 'w').write(''.join(out))
PY
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
b.Add(z)
# KRT keeps the T1S rule's 0.75 mm from tracks but not from vias: a keep-out round each T1S via
for t in list(b.GetTracks()):
    if t.Type() == pcbnew.PCB_VIA_T and t.GetNetClassName() == "T1S_100R":
        x, y = pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)
        k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetZoneName("T1S_VIA_KEEPOUT")
        k.SetLayerSet(pcbnew.LSET.AllCuMask())
        k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowPads(False)
        k.SetDoNotAllowZoneFills(False); k.SetDoNotAllowFootprints(False)
        o = k.Outline(); o.RemoveAllContours(); o.NewOutline()
        r = 1.05
        for dx, dy in ((-r, -r), (r, -r), (r, r), (-r, r)):
            o.Append(pcbnew.FromMM(x + dx), pcbnew.FromMM(y + dy))
        b.Add(k)
# and no other net's via within 1.0 mm of a T1S track (KRT keeps the rule track to track, not via to track)
for t in list(b.GetTracks()):
    if t.Type() != pcbnew.PCB_VIA_T and t.GetNetClassName() == "T1S_100R":
        (x0, y0), (x1, y1) = pcbnew.ToMM(t.GetStart()), pcbnew.ToMM(t.GetEnd())
        k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetZoneName("T1S_TRACK_VIA_KEEPOUT")
        k.SetLayerSet(pcbnew.LSET.AllCuMask())
        k.SetDoNotAllowTracks(False); k.SetDoNotAllowVias(True); k.SetDoNotAllowPads(False)
        k.SetDoNotAllowZoneFills(False); k.SetDoNotAllowFootprints(False)
        o = k.Outline(); o.RemoveAllContours(); o.NewOutline()
        r = 1.0
        for x, y in ((min(x0, x1) - r, min(y0, y1) - r), (max(x0, x1) + r, min(y0, y1) - r),
                     (max(x0, x1) + r, max(y0, y1) + r), (min(x0, x1) - r, max(y0, y1) + r)):
            o.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
        b.Add(k)
# T1S_TRACK_KEEPOUT=1: no other net's track within 0.85 mm of a T1S track either (KRT keeps the T1S rule's
# 0.75 mm only where it reads it; for a pass that routes no T1S-class net)
import os
if os.environ.get("T1S_TRACK_KEEPOUT"):
    for t in list(b.GetTracks()):
        if t.Type() != pcbnew.PCB_VIA_T and t.GetNetClassName() == "T1S_100R":
            (x0, y0), (x1, y1) = pcbnew.ToMM(t.GetStart()), pcbnew.ToMM(t.GetEnd())
            k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetZoneName("T1S_TRACK_KEEPOUT")
            ls = pcbnew.LSET(); ls.AddLayer(t.GetLayer()); k.SetLayerSet(ls)
            k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowPads(False)
            k.SetDoNotAllowZoneFills(False); k.SetDoNotAllowFootprints(False)
            o = k.Outline(); o.RemoveAllContours(); o.NewOutline()
            r = 0.85
            for x, y in ((min(x0, x1) - r, min(y0, y1) - r), (max(x0, x1) + r, min(y0, y1) - r),
                         (max(x0, x1) + r, max(y0, y1) + r), (min(x0, x1) - r, max(y0, y1) + r)):
                o.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
            b.Add(k)
b.Save(sys.argv[1])
PY
cd $KRT
$PY -X utf8 py_router/route.py $OUT/r0.kicad_pcb $OUT/r1.kicad_pcb --nets "$@" --no-bga-zones --clearance 0.15 --clearance-ceiling 0.15 \
    --track-width ${TW:-0.15} --via-size ${VIA:-0.35} --via-drill ${DRILL:-0.2} --fab-tier standard --escalation off --fab-overrides ${FAB:-$RUN/rmii/fab.txt} --max-ripup 5 \
    --layers F.Cu In1.Cu In2.Cu In3.Cu In4.Cu B.Cu --layer-costs 1.0 -1.0 1.0 -1.0 -1.0 1.0 > $OUT/r1.log 2>&1 || true
grep -h "Single-ended" $OUT/r1.log | tail -1
