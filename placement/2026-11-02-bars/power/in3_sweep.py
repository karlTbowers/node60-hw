#!/usr/bin/env python3
"""Variants of the In3 VBAT_PROT pour (PWR_VBAT_PROT_In3), one board each, for copper_r.py to solve
(2026-11-04: the user cut In3 to a band; find the shape that keeps the loss low on little copper).
Run with KiCad's Python from the repo root:

    $KPY placement/2026-11-02-bars/power/in3_sweep.py BOARD OUTDIR VARIANTS.json

VARIANTS.json: {"name": [[x0, y0, x1, y1], ...], ...} (a union of rectangles, or "board"). Each variant's
board is OUTDIR/<name>/node60.kicad_pcb with only that zone's outline changed and refilled; the filled
In3 area of the zone is printed (mm²).
"""
import json
import os
import sys

import pcbnew

F, M = pcbnew.FromMM, pcbnew.ToMM


def main():
    board, out, spec = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
    for name, rects in spec.items():
        b = pcbnew.LoadBoard(board)
        z = next(z for z in b.Zones() if z.GetZoneName() == "PWR_VBAT_PROT_In3")
        if rects == "board":
            e = b.GetBoardEdgesBoundingBox()
            rects = [[M(e.GetLeft()), M(e.GetTop()), M(e.GetRight()), M(e.GetBottom())]]
        o = z.Outline()
        o.RemoveAllContours()
        for x0, y0, x1, y1 in rects:
            o.NewOutline()
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                o.Append(F(x), F(y))
        o.Simplify()                       # union of overlapping rectangles
        pcbnew.ZONE_FILLER(b).Fill([z])
        L = b.GetLayerID("In3.Cu")
        area = z.GetFilledPolysList(L).Area() / 1e12
        d = os.path.join(out, name)
        os.makedirs(d, exist_ok=True)
        b.Save(os.path.join(d, "node60.kicad_pcb"))
        print(f"{name:14s} outline {o.Area() / 1e12:8.0f} mm2   filled {area:8.0f} mm2")


if __name__ == "__main__":
    main()
