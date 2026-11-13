#!/usr/bin/env python3
"""rip_nets_box.py BOARD OUT RIPS.json -- delete unlocked tracks and vias by net and box: RIPS.json is a list of
{"nets": ["/NTC_SW2", ...], "box": [x0, y0, x1, y1]}; an item goes when its net's name is in the list (exact, or
its last part) and it lies wholly inside the box. Locked copper stays. KiCad's Python."""
import json, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); M = pcbnew.ToMM
tracks = list(b.GetTracks()); kill = set()           # looked up once: pcbnew's list goes stale after a Remove
for r in json.load(open(sys.argv[3])):
    x0, y0, x1, y1 = r["box"]; ins = lambda p: x0 <= M(p.x) <= x1 and y0 <= M(p.y) <= y1
    for k, t in enumerate(tracks):
        nm = t.GetNetname()
        if t.IsLocked() or not (nm in r["nets"] or nm.split("/")[-1] in r["nets"]): continue
        if (ins(t.GetPosition()) if t.Type() == pcbnew.PCB_VIA_T else ins(t.GetStart()) and ins(t.GetEnd())):
            kill.add(k)
for k in kill: b.Remove(tracks[k])
b.Save(sys.argv[2]); print(len(kill), "items ripped")
