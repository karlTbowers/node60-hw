#!/usr/bin/env python3
"""land_spec.py MAIN.json LAND.json SPEC_IN SPEC_OUT -- D32 (user: "I and H", 2026-11-12): bring power_shapes.json
in step with the landing board. Stubs and points whose copper the landing deleted leave the spec; the supply
copper the landing added (3V3_MAIN, GND) joins it as "D32" groups; the D201 pour is a zone; the moved 3V3 parts
north of y 70.8 are excepted from the automatic pad vias (each has its own via here). MAIN and LAND are
dump_board.py dumps of main's board and the landing board."""
import json, sys
m, l, S = (json.load(open(p)) for p in sys.argv[1:4])
r3 = lambda v: round(v, 3)
def tk(net, layer, x1, y1, x2, y2):
    a, b = (r3(x1), r3(y1)), (r3(x2), r3(y2)); return (net, layer, min(a, b), max(a, b))
lt = {tk(t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2']): t for t in l['tracks']}
mt = {tk(t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2']) for t in m['tracks']}
lv = {(v['net'], r3(v['x']), r3(v['y'])): v for v in l['vias']}
mv = {(v['net'], r3(v['x']), r3(v['y'])) for v in m['vias']}
STALE = {("GND", 186.205, 85.727)}                      # C215's old GND via and its F.Cu stub: C215 left
drop = 0
for g in S['stubs']:
    keep = [t for t in g['stubs'] if tk(t[4], g.get('layer', 'B.Cu'), *t[:4]) in lt and (t[4], t[2], t[3]) not in STALE]
    drop += len(g['stubs']) - len(keep); g['stubs'] = keep
for g in S['points']:
    keep = [t for t in g['points'] if (t[2], r3(t[0]), r3(t[1])) in lv and (t[2], t[0], t[1]) not in STALE]
    drop += len(g['points']) - len(keep); g['points'] = keep
S['stubs'] = [g for g in S['stubs'] if g['stubs']]; S['points'] = [g for g in S['points'] if g['points']]
SUP = ("3V3_MAIN", "GND")
newv = sorted(k for k in lv if k not in mv and k[0] in SUP)
newt = sorted(k for k in lt if k not in mt and k[0] in SUP)
S['points'].append({"name": "D32 (2026-11-12): vias of the parts moved onto the 3V3 plane, and C215's GND", "size": 0.45, "drill": 0.25,
                    "points": [[k[1], k[2], k[0]] for k in newv]})
S['stubs'].append({"name": "D32 (2026-11-12): moved parts' pads to their vias", "layer": "B.Cu", "width": 0.3,
                   "stubs": [[k[2][0], k[2][1], k[3][0], k[3][1], k[0]] for k in newt]})
assert all(k[1] == "B.Cu" and abs(lt[k]['w'] - 0.3) < 1e-6 for k in newt)
if not any(z['name'] == "PWR_VBAT_IN_D201_F" for z in S['zones']):
    i = next(i for i, z in enumerate(S['zones']) if z['name'] == "PWR_VBAT_IN_bar_F")
    S['zones'].insert(i + 1, {"name": "PWR_VBAT_IN_D201_F", "net": "/VBAT_IN", "layers": ["F.Cu"], "priority": 11,
                              "rects": [[76.1, 91.4, 92.7, 102.1]]})
pv = next(v for v in S['pad_vias'] if v['name'].startswith("3V3_MAIN pads north"))
for r in ("R211", "R406", "R407", "R508", "R607", "R707", "R807", "R701"):
    if r not in pv['except']: pv['except'].append(r)
S['about'] += (" D32 I and H (2026-11-12): the thin 3V3 tracks into the power band are gone but U202's and U203's: R601 and R801"
               " stand at the In3 margins' vias, R701 and the NTC pull-ups R607/R707/R807 on the plane south of U401, C215, R211,"
               " R406 and R407 at U203, R508 at U401 ball B3, each on its own via (points and stubs named D32; excepted from the"
               " automatic pad vias); a VBAT_IN pour on F.Cu joins the TVS D201's tab to the bar's pour.")
json.dump(S, open(sys.argv[4], "w"), indent=1)
print(f"dropped {drop} stub(s)/point(s); added {len(newv)} via(s), {len(newt)} stub(s)")
