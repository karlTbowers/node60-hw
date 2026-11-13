#!/usr/bin/env python3
"""place_test_points.py COPPER.json COURTYARDS.json PARKED.json OUT.json [--only REF,...] [--avoid X,Y,R ...]

Where each parked test point can go back (user, 2026-11-12: "then add back in test points"; 2026-11-05: test
points may go wherever routing is easier). COPPER.json from power/joins/export_copper.py and COURTYARDS.json
from export_courtyards.py, both of the routed board with the test points still parked. For each test point
(1 mm pad on B.Cu) the candidates are its pose before parking, points every 0.25 mm along its net's B.Cu
tracks, its net's vias, and a 0.5 mm grid inside its net's B.Cu pour; the nearest to the old pose wins that
- touches its own net's copper on B.Cu (so it needs no stub; looked for within 15 mm of the old pose, and
  failing that the nearest free spot is taken and marked "stub": the router joins it),
- keeps 0.2 mm from other nets' B.Cu tracks, pads and vias (0.8 mm from T1S-class copper), 0.2 mm from
  every other net's via hole (0.35 mm from a through-hole pad's), and its 2.1 mm courtyard clear of every bottom-side courtyard and placed test point,
- is 1.7 mm inside the board edge and outside UNDER_Y401/UNDER_Y501 (GND excepted).
OUT.json: {ref: {x, y, moved_mm, on}}; "failed" lists the ones with no spot. Run with a Python that has shapely."""
import json, math, sys
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree
a = sys.argv[1:]; only = None; avoid = []
pos = []
i = 0
while i < len(a):
    if a[i] == "--only": only = set(a[i + 1].split(",")); i += 2
    elif a[i] == "--avoid": avoid.append(tuple(float(v) for v in a[i + 1].split(","))); i += 2
    else: pos.append(a[i]); i += 1
C, CY, PARK = (json.load(open(p)) for p in pos[:3])
import os
R_PAD, R_CY, CLR, CLR_T1S, HCLR, EDGE, MAX_ON = 0.5, 1.05, 0.2, 0.8, 0.35, 1.7, float(os.environ.get('TP_MAX_ON', 15.0))   # TP_MAX_ON=200: on its own copper wherever that is, rather than a stub
P = lambda o: Polygon(o["outer"], o["holes"])
tpnet = {p["ref"]: p["net"] for p in C["pads"] if p["ref"].startswith("TP")}
# each test point's own size: the signal ones are 1 mm pads, the ground ones 2.5 x 2.8 mm pads (probe loops)
fpos = {f["ref"]: (f["x"], f["y"]) for f in CY}
RP, RC = {}, {}
for p in C["pads"]:
    if p["ref"].startswith("TP"):
        fx, fy = fpos[p["ref"]]
        RP[p["ref"]] = max(RP.get(p["ref"], 0), max(math.hypot(x - fx, y - fy) for l in p["layers"].values() for o in l for x, y in o["outer"]))
for f in CY:
    if f["ref"].startswith("TP"):
        RC[f["ref"]] = max([math.hypot(x - f["x"], y - f["y"]) for sd in ("F", "B") for o in f[sd] for x, y in o] or [R_CY]) + 0.05
# B.Cu copper by net
geo, net_of, t1s = [], [], []
own_tracks, own_vias, own_fill, own_cu = {}, {}, {}, {}
for p in C["pads"]:
    if p["ref"].startswith("TP") or "B.Cu" not in p["layers"]: continue
    g = unary_union([P(o) for o in p["layers"]["B.Cu"]])
    geo.append(g); net_of.append(p["net"]); t1s.append("T1S_100R" in p.get("cls", ""))
    own_cu.setdefault(p["net"], []).append(g)
for t in C["tracks"]:
    if t["layer"] != "B.Cu": continue
    g = LineString([t["a"], t["b"]]).buffer(t["w"] / 2) if t["a"] != t["b"] else Point(t["a"]).buffer(t["w"] / 2)
    geo.append(g); net_of.append(t["net"]); t1s.append("T1S_100R" in t.get("cls", ""))
    own_tracks.setdefault(t["net"], []).append(t); own_cu.setdefault(t["net"], []).append(g)
holes = []
for v in C["vias"]:
    g = Point(v["x"], v["y"]).buffer(v["size"] / 2)
    geo.append(g); net_of.append(v["net"]); t1s.append("T1S_100R" in v.get("cls", ""))
    own_vias.setdefault(v["net"], []).append(v); own_cu.setdefault(v["net"], []).append(g)
    holes.append((Point(v["x"], v["y"]).buffer(v["drill"] / 2), v["net"], 0.2))        # via holes: the board's 0.2 mm
for h in C["holes"]:
    holes.append((Point(h["x"], h["y"]).buffer(h["d"] / 2), h.get("net", ""), HCLR))   # through-hole pads: 0.35 mm
for z in C["zones"]:
    if z["layer"] == "B.Cu" and z["fill"]:
        own_fill.setdefault(z["net"], []).append(unary_union([P(o) for o in z["fill"]]))
tree = STRtree(geo); htree = STRtree([h[0] for h in holes])
cy = [Polygon(o) for f in CY if not f["ref"].startswith("TP") for o in f["B"] if len(o) > 2]
ctree = STRtree(cy)
under = unary_union([P(o) for ar in C["areas"] if ar["name"] in ("UNDER_Y401", "UNDER_Y501") for o in ar["outline"]])
e = C["edge"]; inside = box(e[0] + EDGE, e[1] + EDGE, e[2] - EDGE, e[3] - EDGE)
placed = [(x, y, r) for x, y, r in avoid]
def legal(x, y, net, R_PAD=R_PAD, R_CY=R_CY):
    pt = Point(x, y)
    if not inside.contains(pt): return False
    if net != "GND" and under.distance(pt) < R_PAD + CLR: return False
    if any(math.hypot(x - px, y - py) < R_CY + r for px, py, r in placed): return False
    for j in tree.query(pt.buffer(R_PAD + CLR_T1S)):
        if net_of[j] == net: continue
        if geo[j].distance(pt) < R_PAD + (CLR_T1S if t1s[j] else CLR): return False
    for j in htree.query(pt.buffer(R_PAD + HCLR)):
        if holes[j][1] != net and holes[j][0].distance(pt) < R_PAD + holes[j][2]: return False
    disc = pt.buffer(R_CY)
    return not any(cy[j].intersects(disc) for j in ctree.query(disc))
def touches(x, y, net, R_PAD=R_PAD):
    pt = Point(x, y)
    if any(g.distance(pt) < 0.3 for g in own_cu.get(net, []) if g.distance(pt) < 2):
        return "copper"
    if any(f.buffer(-(R_PAD - 0.15)).contains(pt) for f in own_fill.get(net, [])):
        return "pour"
    return None
out, failed = {}, []
for ref in sorted(PARK):
    if only and ref not in only: continue
    net = tpnet[ref]; ox, oy = PARK[ref]["x"], PARK[ref]["y"]; rp, rc = RP.get(ref, R_PAD), RC.get(ref, R_CY)
    cand = [(ox, oy)]
    for t in own_tracks.get(net, []):
        (x0, y0), (x1, y1) = t["a"], t["b"]; L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L / 0.25))
        cand += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n + 1)]
    cand += [(v["x"], v["y"]) for v in own_vias.get(net, [])]
    for f in own_fill.get(net, []):
        g = f.buffer(-(rp + 0.1))
        if g.is_empty: continue
        x0, y0, x1, y1 = g.bounds
        x0, y0, x1, y1 = max(x0, ox - max(30, MAX_ON)), max(y0, oy - max(30, MAX_ON)), min(x1, ox + max(30, MAX_ON)), min(y1, oy + max(30, MAX_ON))
        yy = y0
        while yy <= y1:
            xx = x0
            while xx <= x1:
                if g.contains(Point(xx, yy)): cand.append((xx, yy))
                xx += 0.5
            yy += 0.5
    cand.sort(key=lambda c: math.hypot(c[0] - ox, c[1] - oy))
    hit = None
    for x, y in cand:
        if math.hypot(x - ox, y - oy) > MAX_ON: break
        if not legal(x, y, net, rp, rc): continue
        on = touches(x, y, net, rp)
        if on: hit = (x, y, on); break
    if hit is None:                                   # no spot on its own copper nearby: the nearest free spot, joined by a stub
        ring = [(ox + i * 0.25, oy + j * 0.25) for i in range(-120, 121) for j in range(-120, 121)]
        ring.sort(key=lambda c: math.hypot(c[0] - ox, c[1] - oy))
        for x, y in ring:
            if legal(x, y, net, rp, rc): hit = (x, y, touches(x, y, net, rp) or "stub"); break
    if hit is None:
        failed.append(ref); continue
    x, y, on = hit
    out[ref] = {"x": round(x, 4), "y": round(y, 4), "moved_mm": round(math.hypot(x - ox, y - oy), 2), "on": on, "net": net}
    placed.append((x, y, rc))
json.dump({"place": out, "failed": failed}, open(pos[3], "w"), indent=1)
mv = sorted(v["moved_mm"] for v in out.values())
print("stubs:", sorted(r for r, v in out.items() if v["on"] == "stub"))
print(f"{len(out)} placed ({sum(1 for v in mv if v < 0.01)} at their old pose; median move {mv[len(mv)//2] if mv else 0} mm, max {mv[-1] if mv else 0} mm); failed: {failed}")
