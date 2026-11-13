#!/usr/bin/env python3
"""transplant_new.py ROUTED REAL OUT [--skip NET ...] [--only NET ...] -- copy onto REAL every track and via
of ROUTED that REAL does not have (same net, layer and ends), for all nets but --skip (or only --only).
Unlike rmii/transplant_nets.py it never doubles copper REAL already holds (fan-out stubs, hand tracks).
Unlocked; zones are not refilled here (kicad-cli drc --refill-zones --save-board does it). KiCad's Python."""
import sys, pcbnew
a = sys.argv[1:]; skip, only = set(), set(); cur = None; pos = []
for x in a:
    if x == "--skip": cur = skip
    elif x == "--only": cur = only
    elif cur is not None: cur.add(x)
    else: pos.append(x)
src, dst = pcbnew.LoadBoard(pos[0]), pcbnew.LoadBoard(pos[1])
r = lambda v: round(pcbnew.ToMM(v), 3)
def key(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        return (t.GetNetname(), "via", r(t.GetPosition().x), r(t.GetPosition().y))
    p, q = (r(t.GetStart().x), r(t.GetStart().y)), (r(t.GetEnd().x), r(t.GetEnd().y))
    return (t.GetNetname(), t.GetLayer(), min(p, q), max(p, q))
have = {key(t) for t in dst.GetTracks()}
n = nv = 0; nets = set()
for t in src.GetTracks():
    nm = t.GetNetname()
    if nm in skip or (only and nm not in only) or key(t) in have:
        continue
    net = dst.FindNet(nm)
    if net is None: sys.exit(f"no net {nm} on the real board")
    if t.Type() == pcbnew.PCB_VIA_T:
        o = pcbnew.PCB_VIA(dst); o.SetPosition(t.GetPosition()); o.SetWidth(pcbnew.F_Cu, t.GetWidth(pcbnew.F_Cu)); o.SetDrill(t.GetDrill()); nv += 1
    elif t.Type() == pcbnew.PCB_ARC_T:
        o = pcbnew.PCB_ARC(dst); o.SetStart(t.GetStart()); o.SetMid(t.GetMid()); o.SetEnd(t.GetEnd()); o.SetWidth(t.GetWidth()); o.SetLayer(t.GetLayer()); n += 1
    else:
        if t.GetStart() == t.GetEnd(): continue
        o = pcbnew.PCB_TRACK(dst); o.SetStart(t.GetStart()); o.SetEnd(t.GetEnd()); o.SetWidth(t.GetWidth()); o.SetLayer(t.GetLayer()); n += 1
    o.SetNet(net); dst.Add(o); have.add(key(t)); nets.add(nm)
dst.Save(pos[2]); print(f"{n} tracks, {nv} vias of {len(nets)} nets onto {pos[2]}")
