#!/usr/bin/env python3
"""pour_crossings.py BOARD [REF_BOARD] -- signal copper inside the battery nets' pour outlines on the outer layers:
for each PWR_* zone of VBAT_IN, VBAT_D, VBAT_Q2D, VBAT_PROT and OUT1-6 on F.Cu or B.Cu, the other nets' tracks
whose midpoint lies inside its outline (length per net), and the zone's filled area and piece count (against
REF_BOARD's when given). KiCad's Python; the board's zones must be filled."""
import collections, sys, pcbnew
M = pcbnew.ToMM
def load(p):
    b = pcbnew.LoadBoard(p); out = {}
    for z in b.Zones():
        n = z.GetNetname()
        if z.GetIsRuleArea() or not ("VBAT" in n or n.startswith("/OUT")): continue
        for l in z.GetLayerSet().Seq():
            if l not in (pcbnew.F_Cu, pcbnew.B_Cu): continue
            f = z.GetFilledPolysList(l)
            out[(z.GetZoneName(), b.GetLayerName(l))] = (z, l, f.Area() / 1e12, f.OutlineCount())
    return b, out
b, zs = load(sys.argv[1]); ref = load(sys.argv[2])[1] if len(sys.argv) > 2 else {}
for (name, ln), (z, l, area, n) in sorted(zs.items()):
    hit = collections.Counter(); xs = collections.defaultdict(list)
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() != l or t.GetNetname() == z.GetNetname(): continue
        mid = pcbnew.VECTOR2I((t.GetStart().x + t.GetEnd().x) // 2, (t.GetStart().y + t.GetEnd().y) // 2)
        if z.Outline().Contains(mid):
            hit[t.GetNetname().split("/")[-1]] += M(t.GetLength()); xs[t.GetNetname().split("/")[-1]].append((round(M(mid.x), 1), round(M(mid.y), 1)))
    r = ref.get((name, ln))
    print(f"{name} {ln}: {area:.0f} mm2 in {n} piece(s)" + (f"  (ref {r[2]:.0f} mm2 in {r[3]})" if r else "") +
          ("  crossed by: " + ", ".join(f"{k} {v:.1f} mm near {xs[k][0]}" for k, v in hit.most_common()) if hit else ""))
