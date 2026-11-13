#!/usr/bin/env python3
"""sync_spec_sizes.py LAND.json SPEC_IN SPEC_OUT -- N2 resized vias that power_shapes.json lists as points: move
each such point into a group of the board's size (same name + ", enlarged 2026-11-13"). LAND.json is a
dump_board.py dump of the landed board."""
import json, sys
l, S = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])); r3 = lambda v: round(v, 3)
lv = {(v['net'], r3(v['x']), r3(v['y'])): (round(v['d'], 3), round(v['drill'], 3)) for v in l['vias']}
new = {}; n = 0
for g in S['points']:
    keep = []
    for p in g['points']:
        sz = lv.get((p[2], r3(p[0]), r3(p[1])))
        if sz and sz != (g.get('size'), g.get('drill')):
            new.setdefault((g['name'], sz), []).append(p); n += 1
        else: keep.append(p)
    g['points'] = keep
S['points'] = [g for g in S['points'] if g['points']] + [{"name": k[0] + ", enlarged 2026-11-13", "size": k[1][0], "drill": k[1][1], "points": v} for k, v in new.items()]
json.dump(S, open(sys.argv[3], "w"), indent=1); print("moved", n, "point(s) to groups of their new size")
