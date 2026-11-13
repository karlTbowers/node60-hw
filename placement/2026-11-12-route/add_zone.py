#!/usr/bin/env python3
"""add_zone.py BOARD OUT NAME LIKE LAYER PRIORITY "x,y x,y ..." -- add a copper zone NAME on one layer with the
net and settings of zone LIKE and the given outline (one contour, mm): a power shape that power_shapes.json
records as a zone. Filled by kicad-cli drc --refill-zones. KiCad's Python."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); F = pcbnew.FromMM
name, like, layer, prio, pts = sys.argv[3], sys.argv[4], sys.argv[5], int(sys.argv[6]), sys.argv[7]
src = next(z for z in b.Zones() if z.GetZoneName() == like)
for z in list(b.Zones()):
    if z.GetZoneName() == name: b.Remove(z)
z = pcbnew.ZONE(src); z.SetZoneName(name); z.ResetUuid(); z.SetAssignedPriority(prio)
ls = pcbnew.LSET(); ls.AddLayer(b.GetLayerID(layer)); z.SetLayerSet(ls)
o = z.Outline(); o.RemoveAllContours(); o.NewOutline()
for p in pts.split():
    x, y = map(float, p.split(",")); o.Append(F(x), F(y))
z.UnFill(); b.Add(z); b.Save(sys.argv[2])
print(name, layer, z.GetNetname(), "clearance", pcbnew.ToMM(z.GetLocalClearance().value() if hasattr(z.GetLocalClearance(), "value") and z.GetLocalClearance().has_value() else 0), "min width", pcbnew.ToMM(z.GetMinThickness()))
