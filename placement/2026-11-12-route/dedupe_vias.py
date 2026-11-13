#!/usr/bin/env python3
"""dedupe_vias.py BOARD OUT [--main MAIN] -- where two vias of one net stand closer than hole to hole allows
(0.25 mm between holes) or on the same spot, delete one: the unlocked one, and of two unlocked ones the one
MAIN does not have (else the second). Rounds of repair jobs each add a via for a pour piece that still looks
cut off. KiCad's Python."""
import math, sys, pcbnew
a = sys.argv[1:]; main = None
if "--main" in a: main = a[a.index("--main") + 1]; a = a[:a.index("--main")]
b = pcbnew.LoadBoard(a[0]); M = pcbnew.ToMM
old = set()
if main:
    mb = pcbnew.LoadBoard(main)
    old = {(t.GetNetname(), round(M(t.GetPosition().x), 3), round(M(t.GetPosition().y), 3)) for t in mb.GetTracks() if t.Type() == pcbnew.PCB_VIA_T}
tracks = list(b.GetTracks()); vias = [k for k, t in enumerate(tracks) if t.Type() == pcbnew.PCB_VIA_T]
P = lambda k: (M(tracks[k].GetPosition().x), M(tracks[k].GetPosition().y))
key = lambda k: (tracks[k].GetNetname(), round(P(k)[0], 3), round(P(k)[1], 3))
cells = {}
for k in vias: cells.setdefault((tracks[k].GetNetname(), int(P(k)[0]), int(P(k)[1])), []).append(k)
kill = set()
for k in vias:
    if k in kill: continue
    n, cx, cy = tracks[k].GetNetname(), int(P(k)[0]), int(P(k)[1])
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for j in cells.get((n, cx + dx, cy + dy), []):
                if j <= k or j in kill or k in kill: continue
                gap = math.dist(P(k), P(j)) - M(tracks[k].GetDrill()) / 2 - M(tracks[j].GetDrill()) / 2
                if gap >= 0.25 - 1e-6: continue
                score = lambda v: (tracks[v].IsLocked(), key(v) in old)      # keep the locked one, then the one main has
                lose = j if score(j) <= score(k) else k
                if tracks[lose].IsLocked(): continue
                kill.add(lose); print("drop via", key(lose), "beside", key(k if lose == j else j))
for k in kill: b.Remove(tracks[k])
b.Save(a[1]); print(len(kill), "vias dropped")
