#!/usr/bin/env python3
"""Give every footprint pad the net the schematic gives it (Node60, 2026-11-06).

    $KPY scripts/apply_netlist.py BOARD NETLIST.net OUT_BOARD

NETLIST from `kicad-cli sch export netlist --format kicadsexpr node60.kicad_sch`. kicad-cli has no
"update PCB from schematic"; after a schematic edit that moves pins between nets this does the net part
of it (nets created if new, pads re-netted), and prints every pad it changed. Copper on the pads is not
touched: re-draw it from its spec. CI's --schematic-parity then confirms board and schematic agree.
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
from netlist_pads import parse  # noqa: E402

board, netlist, out = sys.argv[1:4]
want = parse(netlist)
b = pcbnew.LoadBoard(board)
n = 0
for f in b.GetFootprints():
    for p in f.Pads():
        k = f"{f.GetReference()}.{p.GetNumber()}"
        if k not in want or p.GetNetname() == want[k]:
            continue
        net = b.FindNet(want[k])
        if net is None:
            net = pcbnew.NETINFO_ITEM(b, want[k]); b.Add(net)
        print(f"{k:10s} {p.GetNetname()} -> {want[k]}")
        p.SetNet(net); n += 1
b.Save(out)
print(f"{n} pads re-netted onto {out}")
