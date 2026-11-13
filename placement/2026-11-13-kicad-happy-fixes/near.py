#!/usr/bin/env python3
"""near.py BOARD X0 Y0 X1 Y1 -- list pads, tracks, vias and zones touching a box (KiCad's Python)."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); M = pcbnew.ToMM
x0, y0, x1, y1 = map(float, sys.argv[2:6])
ins = lambda p: x0 <= M(p.x) <= x1 and y0 <= M(p.y) <= y1
for fp in b.GetFootprints():
    for p in fp.Pads():
        if ins(p.GetPosition()):
            print("PAD", fp.GetReference(), p.GetNumber(), p.GetNetname(), round(M(p.GetPosition().x), 3), round(M(p.GetPosition().y), 3),
                  round(M(p.GetSizeX()), 3), round(M(p.GetSizeY()), 3), p.GetOrientationDegrees(), "TH" if p.HasHole() else b.GetLayerName(p.GetLayer()))
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        if ins(t.GetPosition()):
            print("VIA", t.GetNetname(), round(M(t.GetPosition().x), 3), round(M(t.GetPosition().y), 3), M(t.GetWidth(pcbnew.F_Cu)), M(t.GetDrill()), "L" if t.IsLocked() else "")
    elif t.GetBoundingBox().Intersects(pcbnew.BOX2I(pcbnew.VECTOR2I(pcbnew.FromMM(x0), pcbnew.FromMM(y0)), pcbnew.VECTOR2I(pcbnew.FromMM(x1 - x0), pcbnew.FromMM(y1 - y0)))):
        print("TRK", t.GetNetname(), b.GetLayerName(t.GetLayer()), round(M(t.GetStart().x), 3), round(M(t.GetStart().y), 3), round(M(t.GetEnd().x), 3), round(M(t.GetEnd().y), 3), M(t.GetWidth()), "L" if t.IsLocked() else "")
for z in b.Zones():
    bb = z.GetBoundingBox()
    if M(bb.GetLeft()) <= x1 and M(bb.GetRight()) >= x0 and M(bb.GetTop()) <= y1 and M(bb.GetBottom()) >= y0:
        print("ZONE", z.GetZoneName(), z.GetNetname(), [b.GetLayerName(l) for l in z.GetLayerSet().Seq()], "RULE" if z.GetIsRuleArea() else "", [round(M(v), 2) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())])
