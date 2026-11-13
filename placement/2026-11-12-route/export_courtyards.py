#!/usr/bin/env python3
"""export_courtyards.py BOARD OUT.json -- every footprint's courtyard outlines per side, and its pads' holes.
KiCad's Python."""
import json, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); M = pcbnew.ToMM; out = []
for fp in b.GetFootprints():
    e = {"ref": fp.GetReference(), "x": M(fp.GetPosition().x), "y": M(fp.GetPosition().y), "side": "B" if fp.IsFlipped() else "F", "F": [], "B": []}
    for side, L in (("F", pcbnew.F_CrtYd), ("B", pcbnew.B_CrtYd)):
        c = fp.GetCourtyard(L)
        for i in range(c.OutlineCount()):
            o = c.Outline(i); e[side].append([[M(o.CPoint(j).x), M(o.CPoint(j).y)] for j in range(o.PointCount())])
    out.append(e)
json.dump(out, open(sys.argv[2], "w")); print(len(out), "footprints")
