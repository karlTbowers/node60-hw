#!/usr/bin/env python3
"""silk_export.py BOARD OUT.json -- what the reference text has to avoid, per board side (KiCad's Python):
each footprint's side, centre, reference text box at 0 degrees, courtyard, pads as solder-mask openings,
its silkscreen graphics as polygons; holes; the board outline's box."""
import json, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); M = pcbnew.ToMM
def poly(ps):
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i); out.append([[M(o.CPoint(j).x), M(o.CPoint(j).y)] for j in range(o.PointCount())])
    return out
fps = []
for f in b.GetFootprints():
    back = f.IsFlipped(); cu, silk, crt = (pcbnew.B_Cu, pcbnew.B_SilkS, pcbnew.B_CrtYd) if back else (pcbnew.F_Cu, pcbnew.F_SilkS, pcbnew.F_CrtYd)
    r = f.Reference(); a0 = r.GetTextAngle(); r.SetTextAngle(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T)); bb = r.GetEffectiveTextShape().BBox(); r.SetTextAngle(a0)   # the glyphs; GetBoundingBox adds the line spacing
    e = {"ref": f.GetReference(), "side": "B" if back else "F", "x": M(f.GetPosition().x), "y": M(f.GetPosition().y),
         "tw": M(bb.GetWidth()) + 0.05, "th": 1.3, "visible": r.IsVisible(), "on_silk": r.GetLayer() == silk,
         "tx": M(r.GetPosition().x), "ty": M(r.GetPosition().y), "tangle": r.GetTextAngleDegrees(),
         "courtyard": poly(f.GetCourtyard(crt)), "pads": {"F": [], "B": []}, "silk": {"F": [], "B": []}}
    for p in f.Pads():
        for side, l, ml in (("F", pcbnew.F_Cu, pcbnew.F_Mask), ("B", pcbnew.B_Cu, pcbnew.B_Mask)):
            if p.IsOnLayer(ml):
                ps = pcbnew.SHAPE_POLY_SET(); p.TransformShapeToPolygon(ps, l, p.GetSolderMaskExpansion(l), pcbnew.FromMM(0.005), pcbnew.ERROR_OUTSIDE)
                e["pads"][side] += poly(ps)
    for g in f.GraphicalItems():
        for side, l in (("F", pcbnew.F_SilkS), ("B", pcbnew.B_SilkS)):
            if g.GetLayer() == l:
                ps = pcbnew.SHAPE_POLY_SET(); g.TransformShapeToPolygon(ps, l, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_OUTSIDE)
                e["silk"][side] += poly(ps)
    fps.append(e)
ed = b.GetBoardEdgesBoundingBox()
json.dump({"fps": fps, "edge": [M(ed.GetLeft()) + 0.05, M(ed.GetTop()) + 0.05, M(ed.GetRight()) - 0.05, M(ed.GetBottom()) - 0.05]}, open(sys.argv[2], "w"))
print(len(fps), "footprints")
