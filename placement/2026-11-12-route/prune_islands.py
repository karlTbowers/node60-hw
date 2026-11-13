#!/usr/bin/env python3
"""prune_islands.py BOARD OUT [NETPART ...] -- delete the unlocked tracks and vias that hang on no pad: pieces of
copper a rip left floating (signal nets only, or only the nets whose name contains a NETPART). Copper is joined
where ends meet (0.02 mm), a via joins every layer, a pad joins what ends inside it on its layers. KiCad's Python."""
import collections, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); parts = sys.argv[3:]; M = pcbnew.ToMM
SUP = ("GND", "VBAT", "3V3_MAIN", "1V5_CORE", "VDDAU", "/OUT")
tracks = list(b.GetTracks()); by = collections.defaultdict(list)
for k, t in enumerate(tracks):
    n = t.GetNetname()
    if any(s in n for s in SUP) or (parts and not any(p in n for p in parts)): continue
    by[n].append(k)
pads = collections.defaultdict(list)
for fp in b.GetFootprints():
    for p in fp.Pads(): pads[p.GetNetname()].append(p)
kill = []
for n, ks in by.items():
    par = {k: k for k in ks}
    def f(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    pts = collections.defaultdict(list)                       # (x, y rounded to 0.02) -> [(k, layer or None for a via)]
    for k in ks:
        t = tracks[k]
        if t.Type() == pcbnew.PCB_VIA_T: pts[(round(M(t.GetPosition().x) / 0.02), round(M(t.GetPosition().y) / 0.02))].append((k, None))
        else:
            for p in (t.GetStart(), t.GetEnd()): pts[(round(M(p.x) / 0.02), round(M(p.y) / 0.02))].append((k, t.GetLayer()))
    for key, items in pts.items():
        near = [it for dx in (-1, 0, 1) for dy in (-1, 0, 1) for it in pts.get((key[0] + dx, key[1] + dy), [])]
        for a, la in items:
            for c, lc in near:
                if a != c and (la is None or lc is None or la == lc): par[f(a)] = f(c)
    # a track end or via in the middle of another track of the same layer joins it too
    segs = [(k, tracks[k]) for k in ks if tracks[k].Type() != pcbnew.PCB_VIA_T]
    for key, items in pts.items():
        pt = pcbnew.VECTOR2I(int(key[0] * 0.02 * 1e6), int(key[1] * 0.02 * 1e6))
        for a, la in items:
            for k, t in segs:
                if k != a and (la is None or la == t.GetLayer()) and t.HitTest(pt, int(0.03e6)): par[f(a)] = f(k)
    has_pad = set()
    for k in ks:
        t = tracks[k]
        ends = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
        for p in pads.get(n, []):
            if any(p.HitTest(e, 0) for e in ends) and (t.Type() == pcbnew.PCB_VIA_T or p.IsOnLayer(t.GetLayer())): has_pad.add(f(k)); break
    dead = [k for k in ks if f(k) not in has_pad and not tracks[k].IsLocked()]
    if dead: print(f"{n}: {len(dead)} floating item(s)")
    kill += dead
for k in kill: b.Remove(tracks[k])
b.Save(sys.argv[2]); print(len(kill), "items pruned")
