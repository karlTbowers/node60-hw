#!/usr/bin/env python3
"""Export a board's copper, holes and rule areas as JSON for plan_joins.py (Node60 power joins, 2026-11-05).

    $KPY export_copper.py BOARD OUT.json

Pads as polygons per copper layer (with ref, number, net, centre), tracks (layer, ends, width, net,
net class), vias (centre, size, drill, net), plated and unplated holes, filled pours per layer with
their names and nets, and the rule areas (name, layers, outline, what they forbid).
"""
import json
import sys

import pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
CU = [l for l in b.GetEnabledLayers().CuStack()]
LN = {l: b.GetStandardLayerName(l) for l in CU}


def poly(ps):
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        out.append({"outer": [[o.CPoint(j).x / 1e6, o.CPoint(j).y / 1e6] for j in range(o.PointCount())],
                    "holes": [[[ps.Hole(i, h).CPoint(j).x / 1e6, ps.Hole(i, h).CPoint(j).y / 1e6]
                               for j in range(ps.Hole(i, h).PointCount())] for h in range(ps.HoleCount(i))]})
    return out


pads, holes = [], []
for fp in b.GetFootprints():
    for p in fp.Pads():
        c = p.GetPosition()
        e = {"ref": fp.GetReference(), "num": p.GetNumber(), "net": p.GetNetname(),
             "cls": p.GetNetClassName() if p.GetNetname() else "", "x": c.x / 1e6, "y": c.y / 1e6, "layers": {}}
        for l in CU:
            if p.IsOnLayer(l) and p.FlashLayer(l):
                ps = pcbnew.SHAPE_POLY_SET()
                p.TransformShapeToPolygon(ps, l, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
                e["layers"][LN[l]] = poly(ps)
        if p.GetDrillSize().x > 0:
            holes.append({"x": c.x / 1e6, "y": c.y / 1e6, "d": max(p.GetDrillSize().x, p.GetDrillSize().y) / 1e6,
                          "plated": p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH, "net": p.GetNetname()})
        pads.append(e)
tracks, vias = [], []
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        c = t.GetPosition()
        vias.append({"x": c.x / 1e6, "y": c.y / 1e6, "size": t.GetWidth(pcbnew.F_Cu) / 1e6, "drill": t.GetDrill() / 1e6,
                     "net": t.GetNetname(), "cls": t.GetNetClassName()})
    else:
        tracks.append({"layer": LN[t.GetLayer()], "a": [t.GetStart().x / 1e6, t.GetStart().y / 1e6],
                       "b": [t.GetEnd().x / 1e6, t.GetEnd().y / 1e6], "w": t.GetWidth() / 1e6,
                       "net": t.GetNetname(), "cls": t.GetNetClassName()})
zones, areas = [], []
for z in b.Zones():
    if z.GetIsRuleArea():
        o = z.Outline()
        areas.append({"name": z.GetZoneName(), "layers": [LN[l] for l in CU if z.IsOnLayer(l)],
                      "outline": poly(o), "no_tracks": z.GetDoNotAllowTracks(), "no_vias": z.GetDoNotAllowVias()})
        continue
    for l in CU:
        if z.IsOnLayer(l):
            zones.append({"name": z.GetZoneName(), "net": z.GetNetname(), "layer": LN[l],
                          "fill": poly(z.GetFilledPolysList(l))})
edge = b.GetBoardEdgesBoundingBox()
json.dump({"layers": [LN[l] for l in CU], "pads": pads, "holes": holes, "tracks": tracks, "vias": vias,
           "zones": zones, "areas": areas,
           "edge": [edge.GetLeft() / 1e6, edge.GetTop() / 1e6, edge.GetRight() / 1e6, edge.GetBottom() / 1e6]},
          open(sys.argv[2], "w"))
print(f"{sys.argv[2]}: {len(pads)} pads, {len(tracks)} tracks, {len(vias)} vias, {len(zones)} pour layers, {len(areas)} rule areas")
