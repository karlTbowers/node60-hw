#!/usr/bin/env python3
"""apply_test_points.py BOARD PLACE.json OUT -- move each test point of PLACE.json's "place" to its spot
(bottom side, as it is). KiCad's Python."""
import json, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); P = json.load(open(sys.argv[2]))["place"]; n = 0
for ref, p in P.items():
    fp = b.FindFootprintByReference(ref)
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(p["x"]), pcbnew.FromMM(p["y"]))); n += 1
b.Save(sys.argv[3]); print("placed", n, "test points")
