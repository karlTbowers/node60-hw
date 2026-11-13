#!/usr/bin/env python3
"""net_islands.py COPPER.json [NET] -- an independent count of a net's copper islands (default GND): its pours'
filled pieces, tracks, pads and vias per layer, joined where they touch, and across layers by vias and plated
holes. Prints the islands that hold pads. COPPER.json from export_copper.py (zones filled). Needs shapely."""
import json, sys
from shapely.geometry import Point, Polygon, LineString
from shapely.strtree import STRtree
C = json.load(open(sys.argv[1])); NET = sys.argv[2] if len(sys.argv) > 2 else "GND"
nodes = []          # (layer, geometry, label)
for z in C["zones"]:
    if z["net"] == NET:
        for o in z["fill"]: nodes.append((z["layer"], Polygon(o["outer"], o["holes"]), None))
for t in C["tracks"]:
    if t["net"] == NET: nodes.append((t["layer"], LineString([t["a"], t["b"]]).buffer(t["w"] / 2), None))
thru = []
for p in C["pads"]:
    if p["net"] != NET: continue
    ids = []
    for l, polys in p["layers"].items():
        for o in polys: ids.append(len(nodes)); nodes.append((l, Polygon(o["outer"]), f"{p['ref']}.{p['num']}"))
    thru.append(ids)
for v in C["vias"]:
    if v["net"] != NET: continue
    ids = []
    for l in C["layers"]: ids.append(len(nodes)); nodes.append((l, Point(v["x"], v["y"]).buffer(v["size"] / 2), None))
    thru.append(ids)
par = list(range(len(nodes)))
def find(a):
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
for ids in thru:
    for i in ids[1:]: par[find(i)] = find(ids[0])
for l in C["layers"]:
    idx = [i for i, n in enumerate(nodes) if n[0] == l]; gs = [nodes[i][1] for i in idx]; tree = STRtree(gs)
    for a, g in enumerate(gs):
        for b in tree.query(g):
            if b > a and g.distance(gs[b]) < 0.001: par[find(idx[a])] = find(idx[b])
isl = {}
for i, n in enumerate(nodes):
    if n[2]: isl.setdefault(find(i), set()).add(n[2])
print(f"{NET}: {len(isl)} island(s) holding pads:", sorted((len(v) for v in isl.values()), reverse=True))
for v in sorted(isl.values(), key=len)[:-1]: print("  apart:", sorted(v))
