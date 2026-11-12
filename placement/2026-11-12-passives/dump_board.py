"""Dump a board to JSON for the passive-placement study (read-only).
usage: $KPY dump_board.py board.kicad_pcb out.json"""
import sys, json, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM
out = {"footprints": [], "tracks": [], "vias": [], "zones": []}
for f in b.GetFootprints():
    p = f.GetPosition()
    cy = f.GetCourtyard(f.GetLayer() if f.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd) else (pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd))
    bb = cy.BBox() if cy.OutlineCount() else None
    out["footprints"].append({
        "ref": f.GetReference(), "value": f.GetValue(), "fp": str(f.GetFPID().GetLibItemName()),
        "side": "B" if f.IsFlipped() else "F", "x": mm(p.x), "y": mm(p.y), "rot": f.GetOrientationDegrees(),
        "locked": f.IsLocked(), "sheet": f.GetSheetname(),
        "cy": [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())] if bb else None,
        "pads": [{"num": pd.GetNumber(), "net": pd.GetNetname(), "x": mm(pd.GetPosition().x), "y": mm(pd.GetPosition().y),
                  "w": mm(pd.GetSize(pcbnew.B_Cu if pd.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu).x), "h": mm(pd.GetSize(pcbnew.B_Cu if pd.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu).y),
                  "th": pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH,
                  "layer": "B" if (pd.IsOnLayer(pcbnew.B_Cu) and not pd.IsOnLayer(pcbnew.F_Cu)) else ("F" if not pd.IsOnLayer(pcbnew.B_Cu) else "*")}
                 for pd in f.Pads()]})
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        out["vias"].append({"net": t.GetNetname(), "x": mm(t.GetPosition().x), "y": mm(t.GetPosition().y),
                            "d": mm(t.GetWidth(pcbnew.F_Cu)), "drill": mm(t.GetDrill()), "locked": t.IsLocked()})
    else:
        out["tracks"].append({"net": t.GetNetname(), "layer": t.GetLayerName(), "x1": mm(t.GetStart().x), "y1": mm(t.GetStart().y),
                              "x2": mm(t.GetEnd().x), "y2": mm(t.GetEnd().y), "w": mm(t.GetWidth()), "locked": t.IsLocked()})
for z in b.Zones():
    bb = z.GetBoundingBox()
    ol = z.Outline()
    pts = [[mm(ol.CVertex(i).x), mm(ol.CVertex(i).y)] for i in range(ol.TotalVertices())]
    out["zones"].append({"name": z.GetZoneName(), "net": z.GetNetname(), "layers": [b.GetLayerName(l) for l in z.GetLayerSet().Seq()],
                         "rule_area": z.GetIsRuleArea(), "prio": z.GetAssignedPriority(),
                         "bbox": [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())], "pts": pts,
                         "filled_mm2": {b.GetLayerName(l): z.GetFilledPolysList(l).Area() / 1e12 for l in z.GetLayerSet().Seq()} if not z.GetIsRuleArea() else {}})
json.dump(out, open(sys.argv[2], "w"))
print(len(out["footprints"]), "footprints", len(out["tracks"]), "tracks", len(out["vias"]), "vias", len(out["zones"]), "zones")
