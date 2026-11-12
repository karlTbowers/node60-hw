#!/usr/bin/env python3
"""lock_supply.py BOARD SPEC -- lock the board's tracks and vias that the power spec's points and stubs draw
(D32: the study drew them unlocked; draw_power.py replaces only locked copper). KiCad's Python."""
import json, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); S = json.load(open(sys.argv[2])); M = pcbnew.ToMM
pts = {(t[2], round(t[0], 3), round(t[1], 3)) for g in S['points'] for t in g['points']}
ends = {(t[4], round(t[2], 3), round(t[3], 3)) for g in S['stubs'] for t in g['stubs']} | \
       {(t[4], round(t[0], 3), round(t[1], 3)) for g in S['stubs'] for t in g['stubs']}
n = 0
for t in b.GetTracks():
    if t.IsLocked(): continue
    if t.Type() == pcbnew.PCB_VIA_T:
        hit = (t.GetNetname(), round(M(t.GetPosition().x), 3), round(M(t.GetPosition().y), 3)) in pts
    else:
        hit = (t.GetNetname(), round(M(t.GetStart().x), 3), round(M(t.GetStart().y), 3)) in ends and \
              (t.GetNetname(), round(M(t.GetEnd().x), 3), round(M(t.GetEnd().y), 3)) in ends
    if hit: t.SetLocked(True); n += 1
b.Save(sys.argv[1]); print("locked", n)
