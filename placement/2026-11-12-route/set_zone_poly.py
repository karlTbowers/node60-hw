#!/usr/bin/env python3
"""set_zone_poly.py BOARD OUT ZONE_NAME "x,y x,y ..." -- give a named zone a new outline (one contour, mm), as
power_shapes.json's "poly" for it. The fill is redone by kicad-cli drc --refill-zones. KiCad's Python."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); F = pcbnew.FromMM
z = next(z for z in b.Zones() if z.GetZoneName() == sys.argv[3])
o = z.Outline(); o.RemoveAllContours(); o.NewOutline()
for p in sys.argv[4].split():
    x, y = map(float, p.split(",")); o.Append(F(x), F(y))
z.UnFill(); b.Save(sys.argv[2]); print(sys.argv[3], o.Outline(0).PointCount(), "points")
