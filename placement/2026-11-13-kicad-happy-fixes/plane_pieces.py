#!/usr/bin/env python3
"""plane_pieces.py BOARD [REF_BOARD] -- every pour's filled area and piece count per layer (zones must be filled);
with REF_BOARD only the pours that differ are listed, then the totals. Shows whether added vias cut a plane.
KiCad's Python."""
import sys, pcbnew
def load(p):
    b = pcbnew.LoadBoard(p); out = {}
    for z in b.Zones():
        if z.GetIsRuleArea(): continue
        for l in z.GetLayerSet().Seq():
            f = z.GetFilledPolysList(l); out[(b.GetLayerName(l).split(".PWR")[0].split(".GND")[0], z.GetZoneName() or z.GetNetname())] = (f.Area() / 1e12, f.OutlineCount())
    return out
a = load(sys.argv[1]); r = load(sys.argv[2]) if len(sys.argv) > 2 else None
for k in sorted(a):
    if r is None: print(f"{k[0]:7} {k[1]:28} {a[k][0]:9.1f} mm2 in {a[k][1]} piece(s)")
    elif k not in r: print(f"{k[0]:7} {k[1]:28} new: {a[k][0]:9.1f} mm2 in {a[k][1]}")
    elif a[k][1] != r[k][1] or abs(a[k][0] - r[k][0]) > 0.05:
        print(f"{k[0]:7} {k[1]:28} {r[k][0]:9.1f} -> {a[k][0]:9.1f} mm2 ({a[k][0] - r[k][0]:+.1f}), pieces {r[k][1]} -> {a[k][1]}")
if r: print("pieces in all:", sum(v[1] for v in r.values()), "->", sum(v[1] for v in a.values()))
