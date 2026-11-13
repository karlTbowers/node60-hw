#!/usr/bin/env python3
"""land_spec.py MAIN.json LAND.json SPEC_IN SPEC_OUT TAG NET [NET ...] -- bring power_shapes.json in step with a
routed board (routing run 2026-11-12; the general form of the passives study's land_spec.py). MAIN and LAND are
dump_board.py dumps of the board before and after. Stubs and points of the spec that the landed board no longer
has leave it; the tracks and vias the landed board gained on the named nets join it as groups named TAG, one per
layer and width (vias: per size). Other nets' new copper is the router's and stays out of the spec."""
import json, sys, collections
m, l, S = (json.load(open(p)) for p in sys.argv[1:4]); TAG = sys.argv[5]; NETS = set(sys.argv[6:])
r3 = lambda v: round(v, 3)
def tk(net, layer, x1, y1, x2, y2):
    a, b = (r3(x1), r3(y1)), (r3(x2), r3(y2)); return (net, layer.replace(".PWR", "").replace(".GND", ""), min(a, b), max(a, b))
lt = {tk(t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2']): t for t in l['tracks']}
mt = {tk(t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2']) for t in m['tracks']}
lv = {(v['net'], r3(v['x']), r3(v['y'])): v for v in l['vias']}
mv = {(v['net'], r3(v['x']), r3(v['y'])) for v in m['vias']}
drop = 0
for g in S['stubs']:
    keep = [t for t in g['stubs'] if tk(t[4], g.get('layer', 'B.Cu'), *t[:4]) in lt]
    drop += len(g['stubs']) - len(keep); g['stubs'] = keep
for g in S['points']:
    keep = [t for t in g['points'] if (t[2], r3(t[0]), r3(t[1])) in lv]
    drop += len(g['points']) - len(keep); g['points'] = keep
S['stubs'] = [g for g in S['stubs'] if g['stubs']]; S['points'] = [g for g in S['points'] if g['points']]
byv, byt = collections.defaultdict(list), collections.defaultdict(list)
for k, v in sorted(lv.items()):
    if k not in mv and k[0] in NETS: byv[(v['d'], v['drill'])].append([k[1], k[2], k[0]])
for k, t in sorted(lt.items()):
    if k not in mt and k[0] in NETS: byt[(k[1], round(t['w'], 3))].append([k[2][0], k[2][1], k[3][0], k[3][1], k[0]])
for (d, dr), pts in sorted(byv.items()):
    S['points'].append({"name": f"{TAG}: vias", "size": d, "drill": dr, "points": pts})
for (layer, w), st in sorted(byt.items()):
    S['stubs'].append({"name": f"{TAG}: stubs", "layer": layer, "width": w, "stubs": st})
json.dump(S, open(sys.argv[4], "w"), indent=1)
print(f"dropped {drop} stub(s)/point(s); added {sum(map(len, byv.values()))} via(s), {sum(map(len, byt.values()))} stub(s)")
