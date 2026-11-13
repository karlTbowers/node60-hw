#!/usr/bin/env python3
"""rip_box.py BOARD OUT X0,Y0,X1,Y1 [--keep NETPART,...] -- delete the unlocked signal tracks and vias that lie
wholly inside a box (supply nets, T1S and RMII copper and locked copper stay), so a congested corner can be
routed again in a better order. KiCad's Python."""
import sys, pcbnew
a = sys.argv[1:]; b = pcbnew.LoadBoard(a[0]); x0, y0, x1, y1 = map(float, a[2].split(",")); M = pcbnew.ToMM
KEEP = ("GND", "VBAT", "3V3_MAIN", "1V5_CORE", "VDDAU", "/OUT", "T1S_", "RMII", "MDIO", "FXOSC", "_SW", "_REG")
if "--keep" in a: KEEP += tuple(a[a.index("--keep") + 1].split(","))
ins = lambda p: x0 <= M(p.x) <= x1 and y0 <= M(p.y) <= y1
kill = []
for t in b.GetTracks():
    n = t.GetNetname()
    if t.IsLocked() or any(k in n for k in KEEP) and "SW_VDD" not in n: continue
    if t.Type() == pcbnew.PCB_VIA_T:
        if ins(t.GetPosition()): kill.append(t)
    elif ins(t.GetStart()) and ins(t.GetEnd()): kill.append(t)
nets = sorted({t.GetNetname() for t in kill})
for t in kill: b.Delete(t)
b.Save(a[1]); print(f"ripped {len(kill)} items of {len(nets)} nets in the box: {', '.join(n.split('/')[-1] for n in nets)}")
