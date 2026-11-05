#!/usr/bin/env python3
"""Copper in the T1S trunk's way (the pair between J912 and J903 on F.Cu, about y 46): F.Cu tracks
crossing y 46 between x 135.5 and 174.5, and vias (every via passes F.Cu) in the corridor x 133.4-176.6,
y 44.8-47.2 (the pair, 0.165/0.15 mm, plus the 0.75 mm the T1S rule keeps from other nets); the T1S
line's own copper (class T1S_100R) is not counted.
    $KPY trunk_check.py BOARD [--all]     (--all: every net's vias and top-side pads, not only RMII/clock)"""
import sys
import pcbnew
NETS = ("/RMII0_", "/MDIO0_", "/T1S/T1S_OSC_OUT", "/T1S/T1S_REFCLK")
b = pcbnew.LoadBoard(sys.argv[1]); n = 0
ALL = "--all" in sys.argv
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() != pcbnew.F_Cu or not t.GetNetname().startswith(NETS):
        continue
    (x0, y0), (x1, y1) = pcbnew.ToMM(t.GetStart()), pcbnew.ToMM(t.GetEnd())
    if (y0 - 46) * (y1 - 46) <= 0 and y0 != y1:
        x = x0 + (46 - y0) * (x1 - x0) / (y1 - y0)
        if 135.5 <= x <= 174.5:
            n += 1; print("crosses", t.GetNetname(), round(x, 2))
m = 0
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T and (ALL or t.GetNetname().startswith(NETS)) and t.GetNetClassName() != "T1S_100R":
        x, y = pcbnew.ToMM(t.GetPosition())
        if 133.4 <= x <= 176.6 and 44.8 <= y <= 47.2:
            m += 1; print("via on the trunk line", t.GetNetname(), round(x, 2), round(y, 2))
k = 0
if ALL:
    for f in b.GetFootprints():
        if f.GetReference() in ("J912", "J903"):
            continue
        for p in f.Pads():
            x, y = pcbnew.ToMM(p.GetPosition())
            if p.IsOnLayer(pcbnew.F_Cu) and 133.4 <= x <= 176.6 and 44.8 <= y <= 47.2 and p.GetNetClassName() != "T1S_100R":
                k += 1; print("top-side pad on the trunk line", f.GetReference(), p.GetNumber(), p.GetNetname())
print(f"{n} F.Cu crossings of the trunk line, {m} vias in its corridor" + (f", {k} top-side pads" if ALL else ""))
