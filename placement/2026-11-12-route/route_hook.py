#!/usr/bin/env python3
"""route_hook.py BOARD -- keep-outs on the router's copy that make KiCadRoutingTools keep Node60's rules it
does not model (judge_route.sh's S0_HOOK; from t1s/route_nets.sh, 2026-11-12). KiCad's Python.

- the T1S trunk's F.Cu corridor (x 133.4-176.6, y 44.8-47.2): no tracks, no vias;
- round every T1S-class via, 1.05 mm: no tracks or vias on any layer;
- along every T1S-class track, 1.0 mm: no vias; 0.85 mm on its own layer: no tracks (the 0.75 mm rule);
- over the In3 VBAT_PROT finger to U301 (x 162.8-164.8, y 49.6-71.4): no vias;
- under the crystals (UNDER_Y401, UNDER_Y501): no vias; with HOOK_REPAIR=1 (a pass after the crystal is
  routed) no tracks either: node60.kicad_dru allows only the crystal's nets and GND there;
- round the buck switch-node copper on B.Cu, 1.15 mm: no tracks (1V5_CORE_FB 1 mm from the switch nodes; this
  keeps every signal off them, which costs nothing there).
The real board is untouched; KiCad's DRC with node60.kicad_dru judges the result."""
import math, os, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); F, M = pcbnew.FromMM, pcbnew.ToMM
def area(name, pts, layers=None, tracks=True, vias=True):
    z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName(name)
    if layers is None: z.SetLayerSet(pcbnew.LSET.AllCuMask())
    else:
        ls = pcbnew.LSET()
        for l in layers: ls.AddLayer(l)
        z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(tracks); z.SetDoNotAllowVias(vias); z.SetDoNotAllowPads(False)
    z.SetDoNotAllowZoneFills(False); z.SetDoNotAllowFootprints(False)
    o = z.Outline(); o.RemoveAllContours(); o.NewOutline()
    for x, y in pts: o.Append(F(x), F(y))
    b.Add(z)
def along(p, q, r):
    """a rectangle r round the segment p-q, turned with it"""
    (x0, y0), (x1, y1) = p, q; L = math.hypot(x1 - x0, y1 - y0)
    ux, uy = ((x1 - x0) / L, (y1 - y0) / L) if L > 1e-6 else (1.0, 0.0)
    nx, ny = -uy, ux
    return [(x0 - ux * r + nx * r, y0 - uy * r + ny * r), (x1 + ux * r + nx * r, y1 + uy * r + ny * r),
            (x1 + ux * r - nx * r, y1 + uy * r - ny * r), (x0 - ux * r - nx * r, y0 - uy * r - ny * r)]
area("TRUNK_KEEPOUT_F", [(133.4, 44.8), (176.6, 44.8), (176.6, 47.2), (133.4, 47.2)], [pcbnew.F_Cu])
# the In3 VBAT_PROT finger to U301 and C301 (x 163.2-164.4, y 47-71) is 1.2 mm wide: a few signal vias cut it
# (2026-11-12). No vias within 0.4 mm of it; tracks may cross on the other layers.
area("U301_FINGER_NO_VIA", [(162.8, 49.6), (164.8, 49.6), (164.8, 71.4), (162.8, 71.4)], tracks=False)
n = 0
for t in list(b.GetTracks()):
    cls = t.GetNetClassName()
    if "T1S_100R" in cls:
        if t.Type() == pcbnew.PCB_VIA_T:
            x, y = M(t.GetPosition().x), M(t.GetPosition().y); r = 1.05
            area("T1S_VIA_KEEPOUT", [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)])
        else:
            p, q = (M(t.GetStart().x), M(t.GetStart().y)), (M(t.GetEnd().x), M(t.GetEnd().y))
            area("T1S_TRACK_VIA_KEEPOUT", along(p, q, 1.0), tracks=False)
            area("T1S_TRACK_KEEPOUT", along(p, q, 0.85), [t.GetLayer()], vias=False)
        n += 1
    elif cls == "SW_NODE" and t.Type() != pcbnew.PCB_VIA_T and not os.environ.get("HOOK_REPAIR"):
        p, q = (M(t.GetStart().x), M(t.GetStart().y)), (M(t.GetEnd().x), M(t.GetEnd().y))
        area("SW_NODE_KEEPOUT", along(p, q, 1.15 + M(t.GetWidth()) / 2), [t.GetLayer()], vias=False); n += 1
for z in b.Zones():
    if z.GetIsRuleArea() and z.GetZoneName() in ("UNDER_Y401", "UNDER_Y501"):
        z.SetDoNotAllowVias(True)
        if os.environ.get("HOOK_REPAIR"):            # a later pass (the crystal is routed): no other net's track under it either
            z.SetDoNotAllowTracks(True)
b.Save(sys.argv[1]); print("keep-outs round", n, "items")
