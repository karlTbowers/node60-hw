#!/usr/bin/env python3
"""drop_dangling.py BOARD DRC.json OUT [--keep NETPART,...] -- delete the unlocked tracks and vias KiCad's DRC
reports as dangling (track_dangling, via_dangling): stubs a re-route left behind. Run DRC again after: a
stub of several segments goes one segment a pass. KiCad's Python."""
import json, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); d = json.load(open(sys.argv[2])); M = pcbnew.ToMM
keep = sys.argv[sys.argv.index("--keep") + 1].split(",") if "--keep" in sys.argv else []
tracks = list(b.GetTracks()); kill = set()
for v in d["violations"]:
    if v["type"] not in ("track_dangling", "via_dangling"): continue
    it = v["items"][0]; x, y = it["pos"]["x"], it["pos"]["y"]; isvia = v["type"] == "via_dangling"
    for k, t in enumerate(tracks):
        if t.IsLocked() or (t.Type() == pcbnew.PCB_VIA_T) != isvia or f"[{t.GetNetname()}]" not in it["description"]: continue
        if any(p in t.GetNetname() for p in keep): continue
        pts = [t.GetPosition()] if isvia else [t.GetStart(), t.GetEnd()]
        if any(abs(M(p.x) - x) < 0.006 and abs(M(p.y) - y) < 0.006 for p in pts):
            if isvia or abs(M(t.GetLength()) - float(it["description"].split("length ")[1].split(" mm")[0])) < 0.002:
                kill.add(k); print("drop", it["description"][:70], (x, y)); break
for k in kill: b.Remove(tracks[k])
b.Save(sys.argv[3]); print(len(kill), "dropped")
