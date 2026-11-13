#!/usr/bin/env python3
"""silk_apply.py BOARD PLACE.json OUT -- move each reference text to its place (centre-justified, 1.0 x 1.0 mm,
0.15 mm stroke, mirrored on the bottom side as KiCad keeps it). Footprints stay where they are. KiCad's Python."""
import json, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); P = json.load(open(sys.argv[2]))["place"]; F = pcbnew.FromMM
for f in b.GetFootprints():
    p = P.get(f.GetReference())
    if not p: continue
    r = f.Reference()
    r.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); r.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    r.SetTextSize(pcbnew.VECTOR2I(F(1.0), F(1.0))); r.SetTextThickness(F(0.15)); r.SetKeepUpright(False)
    r.SetTextAngle(pcbnew.EDA_ANGLE(p["angle"], pcbnew.DEGREES_T)); r.SetPosition(pcbnew.VECTOR2I(F(p["x"]), F(p["y"])))
b.Save(sys.argv[3]); print(len(P), "references placed")
