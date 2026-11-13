#!/usr/bin/env python3
"""dedupe_tracks.py BOARD OUT -- delete exact duplicates: tracks of one net, layer, width and end points lying on
each other, and vias of one net on the same spot (the locked one stays; of two alike, the first). KiCad's Python."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); M = pcbnew.ToMM; seen = {}; kill = []
for t in sorted(b.GetTracks(), key=lambda t: not t.IsLocked()):
    if t.Type() == pcbnew.PCB_VIA_T:
        k = ("via", t.GetNetname(), t.GetPosition().x, t.GetPosition().y)
    else:
        a, e = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
        k = (t.GetNetname(), t.GetLayer(), t.GetWidth(), min(a, e), max(a, e))
    if k in seen:
        kill.append(t); print("duplicate", k[1] if k[0] == "via" else k[0], "via" if k[0] == "via" else b.GetLayerName(k[1]),
                              [round(M(v), 3) for v in (k[2:4] if k[0] == "via" else (*k[3], *k[4]))], "locked" if t.IsLocked() else "")
    else: seen[k] = t
for t in kill: b.Remove(t)
b.Save(sys.argv[2]); print(len(kill), "duplicates dropped")
