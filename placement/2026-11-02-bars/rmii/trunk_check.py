#!/usr/bin/env python3
"""F.Cu copper of the RMII/MDIO/clock nets that crosses the T1S trunk's line (y 46, x 135.5-174.5)."""
import sys
import pcbnew
NETS = ("/RMII0_", "/MDIO0_", "/T1S/T1S_OSC_OUT", "/T1S/T1S_REFCLK")
b = pcbnew.LoadBoard(sys.argv[1]); n = 0
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() != pcbnew.F_Cu or not t.GetNetname().startswith(NETS):
        continue
    (x0, y0), (x1, y1) = pcbnew.ToMM(t.GetStart()), pcbnew.ToMM(t.GetEnd())
    if (y0 - 46) * (y1 - 46) <= 0 and y0 != y1:
        x = x0 + (46 - y0) * (x1 - x0) / (y1 - y0)
        if 135.5 <= x <= 174.5:
            n += 1; print("crosses", t.GetNetname(), round(x, 2))
print(f"{n} F.Cu crossings of the trunk line")
