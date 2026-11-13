#!/usr/bin/env python3
"""missing_in_routed.py ROUTED REAL [OUT --drop NET ...] -- the tracks and vias REAL holds that the router's copy
ROUTED no longer does (the router ripped them to let another net through), by net. With OUT and --drop, those
items of the named nets are deleted from REAL and saved as OUT, so transplant_new.py's copper does not cross
them. KiCad's Python."""
import collections, sys, pcbnew
a = sys.argv[1:]; drop = set(a[a.index("--drop") + 1:]) if "--drop" in a else set()
pos = a[:a.index("--drop")] if "--drop" in a else a
src, dst = pcbnew.LoadBoard(pos[0]), pcbnew.LoadBoard(pos[1])
r = lambda v: round(pcbnew.ToMM(v), 3)
def key(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        return (t.GetNetname(), "via", r(t.GetPosition().x), r(t.GetPosition().y))
    p, q = (r(t.GetStart().x), r(t.GetStart().y)), (r(t.GetEnd().x), r(t.GetEnd().y))
    return (t.GetNetname(), t.GetLayer(), min(p, q), max(p, q))
have = {key(t) for t in src.GetTracks()}
gone = collections.defaultdict(list)
for t in list(dst.GetTracks()):
    if key(t) not in have:
        gone[t.GetNetname()].append(t)
for n, ts in sorted(gone.items()):
    print(f"{n}: {len(ts)} item(s) ripped by the router, {sum(t.IsLocked() for t in ts)} locked" + ("  -> dropped" if n in drop else ""))
if drop:
    for n in drop:
        for t in gone.get(n, []): dst.Remove(t)
    dst.Save(pos[2])
