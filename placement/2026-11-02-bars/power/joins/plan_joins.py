#!/usr/bin/env python3
"""Plan the short power and ground joins a board still lacks (Node60, 2026-11-05).

    python plan_joins.py COPPER.json DRC.json OUT.json [--nets N1,N2,...] [--skip REF,...]

COPPER.json from export_copper.py, DRC.json from `kicad-cli pcb drc --format json` on the same board.
For every unconnected pair on the given nets (pairs with a test point left out: they are parked) it
tries, cheapest first:
- a track on a layer both ends share: straight, either L, or a 45-degree dog-leg;
- one new via between them, a track on each end's layer;
- for a net with a plane under that spot (GND: In1/In4; 3V3_MAIN and VBAT_PROT where their In2/In3
  pours lie), a via beside each end into the plane (an end that is already a via in the plane costs 0).
Every candidate keeps the board's clearances from other nets' copper (0.2 mm outer, 0.15 inside the
escape areas; 0.75 mm from T1S copper), plated holes 0.35 mm from other copper, holes 0.25 mm apart,
no other-net F.Cu tracks in the busbar areas, nothing in the T1S trunk corridor, no other-net vias or B.Cu
tracks under the crystals. Other nets' pours are not obstacles: they retreat round new copper.
OUT.json: {"stubs": [{layer, width, stubs: [[x1,y1,x2,y2,net]]}], "points": [{size, drill, points:
[[x,y,net]]}], "joins": [...report...], "failed": [...]} for power_shapes.json; KiCad's DRC judges.
"""
import argparse
import json
import math
import re

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

ap = argparse.ArgumentParser()
ap.add_argument("copper"); ap.add_argument("drc"); ap.add_argument("out")
ap.add_argument("--nets", default="")
ap.add_argument("--skip", default="", help="refs whose pairs are left alone")
ap.add_argument("--box", action="append", default=[], help="X0,Y0,X1,Y1: only pairs with both ends inside one of these")
ap.add_argument("--keep-clear", default="133.4,44.8,176.6,47.2", help="rect with no new copper on F.Cu and no vias")
a = ap.parse_args()
C = json.load(open(a.copper))
OUTER = ("F.Cu", "B.Cu")
WIDTH = {"VBAT_PROT": 0.4, "/VBAT_IN": 0.4, "/OUT1": 0.4, "/OUT2": 0.4, "/OUT3": 0.4, "/OUT4": 0.4, "/OUT5": 0.4,
         "/OUT6": 0.4, "/MCU and NVM/1V1_MCU_V11": 0.2}
CLR, CLR_ESC, CLR_T1S, HCLR, H2H = 0.2, 0.1, 0.75, 0.35, 0.25
VIAS = [(0.45, 0.25), (0.40, 0.20), (0.35, 0.20)]
KC = [float(v) for v in a.keep_clear.split(",")]
KEEP = Polygon([(KC[0], KC[1]), (KC[2], KC[1]), (KC[2], KC[3]), (KC[0], KC[3])])


def P(o):
    return Polygon(o["outer"], o["holes"])


areas = {}
for ar in C["areas"]:
    g = unary_union([P(o) for o in ar["outline"]])
    areas.setdefault(ar["name"], []).append((ar, g))
ESC = unary_union([g for n in ("ESCAPE_U401", "ESCAPE_U501") for _, g in areas.get(n, [])])
BAR = [(n.replace("BUSBAR_", ""), g) for n, lst in areas.items() if n.startswith("BUSBAR_") for _, g in lst]
UNDER = unary_union([g for n in ("UNDER_Y401", "UNDER_Y501") for _, g in areas.get(n, [])])

# obstacles per layer: (geometry, net, is_t1s)
obs = {l: [] for l in C["layers"]}
pad_geo = {}
for p in C["pads"]:
    for l, polys in p["layers"].items():
        g = unary_union([P(o) for o in polys])
        obs[l].append((g, p["net"], p["cls"] == "T1S_100R"))
        pad_geo[(p["ref"], p["num"], l)] = g
for t in C["tracks"]:
    g = LineString([t["a"], t["b"]]).buffer(t["w"] / 2) if t["a"] != t["b"] else Point(t["a"]).buffer(t["w"] / 2)
    obs[t["layer"]].append((g, t["net"], t["cls"] == "T1S_100R"))
for v in C["vias"]:
    g = Point(v["x"], v["y"]).buffer(v["size"] / 2)
    for l in C["layers"]:
        obs[l].append((g, v["net"], v["cls"] == "T1S_100R"))
holes = [(Point(h["x"], h["y"]).buffer(h["d"] / 2), h["net"], h["plated"]) for h in C["holes"]] + \
        [(Point(v["x"], v["y"]).buffer(v["drill"] / 2), v["net"], True) for v in C["vias"]]
trees = {l: STRtree([o[0] for o in obs[l]]) for l in C["layers"]}
htree = STRtree([h[0] for h in holes])
fills = {}
for z in C["zones"]:
    fills.setdefault((z["net"], z["layer"]), []).extend(P(o) for o in z["fill"])
fills = {k: unary_union(v) for k, v in fills.items()}
zfill = {}
for z in C["zones"]:
    zfill.setdefault(z["name"], []).append((z["layer"], unary_union([P(o) for o in z["fill"]])))
added = {l: [] for l in C["layers"]}      # new copper planned so far: (geometry, net)
added_holes = []


def clear(geo, net, layer, extra=0.0):
    """True if geo (copper of net on layer) keeps clearance to every other net's copper there."""
    c = CLR_ESC if geo.intersects(ESC) else CLR
    for i in trees[layer].query(geo.buffer(CLR_T1S + extra)):
        g, n, t1s = obs[layer][i]
        if n == net:
            continue
        if g.distance(geo) < (CLR_T1S if t1s else c) + extra:
            return False
    for g, n in added[layer]:
        if n != net and g.distance(geo) < c + extra:
            return False
    return True


def holes_clear(geo, net):
    """copper geo keeps 0.35 mm from other nets' plated holes (any layer)."""
    for i in htree.query(geo.buffer(HCLR)):
        g, n, pl = holes[i]
        if n != net and g.distance(geo) < HCLR:
            return False
    for g, n in added_holes:
        if n != net and g.distance(geo) < HCLR:
            return False
    return True


def track_ok(pts, net, layer, w):
    if len(pts) < 2 or all(p == pts[0] for p in pts):
        return True
    ln = LineString(pts)
    geo = ln.buffer(w / 2)
    if layer == "F.Cu":
        if geo.intersects(KEEP):
            return False
        for bn, bg in BAR:
            if bg.intersects(geo) and net not in (bn, "/" + bn):
                return False
    if layer == "B.Cu" and net != "GND" and geo.intersects(UNDER):
        return False
    return clear(geo, net, layer) and holes_clear(geo, net)


def via_ok(x, y, net, size, drill):
    pt = Point(x, y)
    if size < 0.4 and not pt.intersects(ESC):
        return False
    if pt.buffer(size / 2).intersects(KEEP) or (net != "GND" and pt.intersects(UNDER)):
        return False
    ring, hole = pt.buffer(size / 2), pt.buffer(drill / 2)
    for l in C["layers"]:
        if l in OUTER or True:
            # inner pours of other nets retreat; inner tracks and pads do not
            if not clear(ring, net, l):
                return False
            # the drill keeps HCLR from other copper on every layer
            for i in trees[l].query(hole.buffer(HCLR)):
                g, n, _ = obs[l][i]
                if n != net and g.distance(hole) < HCLR:
                    return False
    for i in htree.query(hole.buffer(H2H)):
        g, n, _ = holes[i]
        if g.distance(hole) < H2H:
            return False
    for g, n in added_holes:
        if g.distance(hole) < H2H:
            return False
    return True


def paths(p, q):
    (x0, y0), (x1, y1) = p, q
    out = [[p, q], [p, (x1, y0), q], [p, (x0, y1), q]]
    dx, dy = x1 - x0, y1 - y0
    m = min(abs(dx), abs(dy))
    sx, sy = math.copysign(1, dx), math.copysign(1, dy)
    out.append([p, (x0 + sx * m, y0 + sy * m), q])
    out.append([p, (x1 - sx * m, y1 - sy * m), q])
    return sorted(out, key=lambda ps: sum(math.dist(ps[i], ps[i + 1]) for i in range(len(ps) - 1)))


def plen(ps):
    return sum(math.dist(ps[i], ps[i + 1]) for i in range(len(ps) - 1))


pad_of = {(p["ref"], p["num"]): p for p in C["pads"]}


def endpoint(item):
    d, pos = item["description"], (item["pos"]["x"], item["pos"]["y"])
    net = re.search(r"\[([^\]]+)\]", d).group(1)
    m = re.match(r"Pad (\S+) \[[^\]]+\] of (\S+) on (\S+)", d)
    if m:
        p = pad_of[(m.group(2), m.group(1))]
        return {"kind": "pad", "net": net, "ref": m.group(2), "num": m.group(1), "at": (p["x"], p["y"]),
                "layers": [l for l in p["layers"] if l in OUTER], "label": f"{m.group(2)}.{m.group(1)}"}
    if d.startswith("Via"):
        return {"kind": "via", "net": net, "at": pos, "layers": list(OUTER), "label": f"via@{pos[0]:.2f},{pos[1]:.2f}"}
    if d.startswith("Track"):
        l = re.search(r" on (\S+?),", d).group(1)
        return {"kind": "track", "net": net, "at": pos, "layers": [l] if l in OUTER else [],
                "label": f"track@{pos[0]:.2f},{pos[1]:.2f}"}
    m = re.match(r"Zone '([^']+)'", d)
    if m:
        return {"kind": "zone", "net": net, "zone": m.group(1), "at": pos, "label": m.group(1),
                "layers": [l for l, _ in zfill.get(m.group(1), []) if l in OUTER]}
    return None


def target(e, layer, toward):
    """the point to end a track on endpoint e on layer, coming from toward"""
    if e["kind"] == "zone":
        g = unary_union([g for l, g in zfill[e["zone"]] if l == layer])
        if g.is_empty:
            return None
        from shapely.ops import nearest_points
        q = nearest_points(g.buffer(-0.2), Point(toward))[0] if not g.buffer(-0.2).is_empty else nearest_points(g, Point(toward))[0]
        return (round(q.x, 3), round(q.y, 3))
    return e["at"]


def plane_at(net, x, y, size):
    """a plane layer of net whose fill holds a via of this size at (x, y)"""
    disc = Point(x, y).buffer(size / 2 + 0.05)
    for (n, l), g in fills.items():
        if n == net and l not in OUTER and g.contains(disc):
            return l
    return None


def ring(cx, cy, rmax, step=0.1):
    pts = []
    k = int(rmax / step)
    for i in range(-k, k + 1):
        for j in range(-k, k + 1):
            r = math.hypot(i * step, j * step)
            if r <= rmax:
                pts.append((r, round(cx + i * step, 3), round(cy + j * step, 3)))
    return [(x, y) for r, x, y in sorted(pts)]


def to_plane(e, w):
    """cheapest via beside endpoint e into its net's plane: (cost, via, track points, layer) or None"""
    net = e["net"]
    if e["kind"] == "via" and plane_at(net, e["at"][0], e["at"][1], 0.3):
        return (0.0, None, None, None)
    if e["kind"] == "pad":
        for l in e["layers"]:
            g = pad_geo[(e["ref"], e["num"], l)]
            for v in C["vias"]:
                if v["net"] == net and g.contains(Point(v["x"], v["y"])) and plane_at(net, v["x"], v["y"], 0.3):
                    return (0.0, None, None, None)
    if e["kind"] == "zone" or not e["layers"]:
        return None
    for size, drill in VIAS:
        for (x, y) in ring(e["at"][0], e["at"][1], 1.6):
            if not plane_at(net, x, y, size):
                continue
            for l in e["layers"]:
                if e["kind"] == "pad" and pad_geo[(e["ref"], e["num"], l)].buffer(-0.05).contains(Point(x, y).buffer(size / 2)):
                    if via_ok(x, y, net, size, drill):
                        return (0.5, (x, y, size, drill), None, l)      # via in the pad
                    continue
                ps = [e["at"], (x, y)]
                if via_ok(x, y, net, size, drill) and track_ok(ps, net, l, w):
                    return (0.5 + math.dist(*ps), (x, y, size, drill), ps, l)
    return None


def astar(A, B, net, w, size=0.45, drill=0.25, margin=4.0, step=0.1):
    """grid search on F.Cu and B.Cu between endpoints A and B, one via move allowed anywhere legal"""
    import heapq
    import numpy as np
    from shapely import contains_xy
    from shapely.prepared import prep
    ls = [l for l in OUTER]
    pa = {l: target(A, l, B["at"]) for l in ls if l in A["layers"]}
    pb = {l: target(B, l, A["at"]) for l in ls if l in B["layers"]}
    pa = {l: p for l, p in pa.items() if p}; pb = {l: p for l, p in pb.items() if p}
    if not pa or not pb:
        return None
    xs = [p[0] for p in list(pa.values()) + list(pb.values())]; ys = [p[1] for p in list(pa.values()) + list(pb.values())]
    x0, y0, x1, y1 = min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin
    from shapely.geometry import box
    bx = box(x0 - 1, y0 - 1, x1 + 1, y1 + 1)
    nx, ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    gx, gy = np.meshgrid(np.arange(nx) * step + x0, np.arange(ny) * step + y0, indexing="ij")
    own = []
    for e, pts in ((A, pa), (B, pb)):
        if e["kind"] == "pad":
            for l in pts:
                own.append((l, pad_geo[(e["ref"], e["num"], l)]))
    blocked = {}
    pourc = {}
    for l in OUTER:
        gs = [g for (n, ll), g in fills.items() if ll == l and n != net]
        pourc[l] = contains_xy(unary_union(gs).intersection(bx), gx, gy) if gs else np.zeros((nx, ny), bool)
    vblock = np.zeros((nx, ny), bool)
    for l in C["layers"]:
        geos = []
        for i in trees[l].query(bx):
            g, n, t1s = obs[l][i]
            if n != net:
                c = CLR_T1S if t1s else CLR
                geos.append(g.buffer(c + w / 2))
                vgeo = g.buffer(max(size / 2 + (CLR_T1S if t1s else CLR), drill / 2 + HCLR))
                vblock |= contains_xy(vgeo, gx, gy)
        for g, n in added[l]:
            if n != net:
                geos.append(g.buffer(CLR + w / 2)); vblock |= contains_xy(g.buffer(max(size / 2 + CLR, drill / 2 + HCLR)), gx, gy)
        if l in OUTER:
            if l == "F.Cu":
                geos.append(KEEP.buffer(w / 2))
                for bn, bg in BAR:
                    if net not in (bn, "/" + bn):
                        geos.append(bg.buffer(w / 2))
            if l == "B.Cu" and net != "GND":
                geos.append(UNDER.buffer(w / 2))
            for i in htree.query(bx):
                g, n, _ = holes[i]
                if n != net:
                    geos.append(g.buffer(HCLR + w / 2))
            u = unary_union(geos) if geos else None
            blocked[l] = contains_xy(u, gx, gy) if u is not None else np.zeros((nx, ny), bool)
    for i in htree.query(bx):
        g, n, _ = holes[i]
        vblock |= contains_xy(g.buffer(H2H + drill / 2), gx, gy)
    vblock |= contains_xy(KEEP.buffer(size / 2), gx, gy)
    if net != "GND":
        vblock |= contains_xy(UNDER.buffer(size / 2), gx, gy)
    def cell(p):
        return (int(round((p[0] - x0) / step)), int(round((p[1] - y0) / step)))
    # the endpoints' own pads are free to start and end in
    for l, g in own:
        if l in blocked:
            inside = contains_xy(g, gx, gy)
            blocked[l] &= ~inside
    li = {l: k for k, l in enumerate(ls)}
    starts = [(li[l], *cell(p)) for l, p in pa.items()]
    goals = {(li[l], *cell(p)) for l, p in pb.items()}
    gp = list(pb.items())
    def h(c):
        return min(math.dist((c[1], c[2]), cell(p)) for _, p in gp) * step
    D = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
    openq, best, prev = [], {}, {}
    for s0 in starts:
        best[s0] = 0; heapq.heappush(openq, (h(s0), 0, s0, None))
    VIA_COST = 1.5
    found = None
    n_iter = 0
    while openq and n_iter < 400000:
        n_iter += 1
        f, g, c, d0 = heapq.heappop(openq)
        if g > best.get(c, 1e9) + 1e-9:
            continue
        if c in goals:
            found = c; break
        L, i, j = c
        for di, dj, cost in D:
            ni, nj = i + di, j + dj
            if not (0 <= ni < nx and 0 <= nj < ny) or blocked[ls[L]][ni, nj]:
                continue
            ng = g + cost * step * (6 if pourc[ls[L]][ni, nj] else 1) + (0.05 if d0 is not None and d0 != (di, dj) else 0)
            nc = (L, ni, nj)
            if ng < best.get(nc, 1e9):
                best[nc] = ng; prev[nc] = c; heapq.heappush(openq, (ng + h(nc), ng, nc, (di, dj)))
        if not vblock[i, j]:
            nc = (1 - L, i, j)
            if not blocked[ls[1 - L]][i, j]:
                ng = g + VIA_COST
                if ng < best.get(nc, 1e9):
                    best[nc] = ng; prev[nc] = c; heapq.heappush(openq, (ng + h(nc), ng, nc, None))
    if not found:
        return None
    path = [found]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    segs, vias_ = [], []
    cur = [path[0]]
    for c in path[1:]:
        if c[0] != cur[-1][0]:
            segs.append(cur); vias_.append((round(c[1] * step + x0, 3), round(c[2] * step + y0, 3), size, drill)); cur = [c]
        else:
            cur.append(c)
    segs.append(cur)
    trs = []
    for sg in segs:
        l = ls[sg[0][0]]
        pts = [(round(c[1] * step + x0, 3), round(c[2] * step + y0, 3)) for c in sg]
        # snap the ends onto the real targets, keep corners only
        if sg is segs[0] and l in pa: pts[0] = pa[l]
        if sg is segs[-1] and l in pb: pts[-1] = pb[l]
        simp = [pts[0]]
        for k in range(1, len(pts) - 1):
            ax, ay = pts[k][0] - simp[-1][0], pts[k][1] - simp[-1][1]
            bx_, by_ = pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]
            if abs(ax * by_ - ay * bx_) > 1e-9:
                simp.append(pts[k])
        simp.append(pts[-1])
        if len(simp) >= 2:
            trs.append((simp, l))
    cost = sum(plen(p) for p, _ in trs) + VIA_COST * len(vias_)
    # the snapped ends and every via must still be legal
    for p, l in trs:
        if not track_ok(p, net, l, w):
            return None
    for v in vias_:
        if not via_ok(v[0], v[1], net, v[2], v[3]):
            return None
    return (cost, "grid", w, trs, vias_)


def commit_track(ps, net, layer, w, res):
    if len(ps) >= 2 and plen(ps) > 1e-6:
        added[layer].append((LineString(ps).buffer(w / 2), net))
        for i in range(len(ps) - 1):
            res["stubs"].setdefault((layer, w), []).append([round(ps[i][0], 3), round(ps[i][1], 3),
                                                             round(ps[i + 1][0], 3), round(ps[i + 1][1], 3), net])


def commit_via(v, net, res):
    x, y, size, drill = v
    g = Point(x, y).buffer(size / 2)
    for l in C["layers"]:
        added[l].append((g, net))
    added_holes.append((Point(x, y).buffer(drill / 2), net))
    res["points"].setdefault((size, drill), []).append([x, y, net])


nets = set(n for n in a.nets.split(",") if n)
skip = set(r for r in a.skip.split(",") if r)
pairs = []
for v in json.load(open(a.drc))["unconnected_items"]:
    it = v["items"]
    if any("TP" in i["description"] for i in it):
        continue
    e = [endpoint(i) for i in it]
    if None in e or (nets and e[0]["net"] not in nets):
        continue
    if any(x.get("ref") in skip for x in e):
        continue
    if a.box:
        bxs = [[float(t) for t in b_.split(",")] for b_ in a.box]
        if not any(all(q[0] <= x["at"][0] <= q[2] and q[1] <= x["at"][1] <= q[3] for x in e) for q in bxs):
            continue
    pairs.append(e)
res = {"stubs": {}, "points": {}}
report, failed = [], []
planed = {}      # endpoint label -> already joined to its plane
for A, B in sorted(pairs, key=lambda e: math.dist(e[0]["at"], e[1]["at"])):
    net = A["net"]
    best = None
    for w in sorted({WIDTH.get(net, 0.3), 0.3, 0.25, 0.2}, reverse=True):
        if w > WIDTH.get(net, 0.3):
            continue
        # 1. a track on a shared layer
        for l in set(A["layers"]) & set(B["layers"]):
            p, q = target(A, l, B["at"]), target(B, l, A["at"])
            if p is None or q is None:
                continue
            for ps in paths(p, q):
                if track_ok(ps, net, l, w):
                    c = plen(ps)
                    if best is None or c < best[0]:
                        best = (c, "track", w, [(ps, l)], [])
                    break
        # 2. plane vias at both ends
        if net in ("GND", "3V3_MAIN", "VBAT_PROT"):
            ca = (0.0, None, None, None) if A["label"] in planed else to_plane(A, w)
            cb = (0.0, None, None, None) if B["label"] in planed else to_plane(B, w)
            if ca and cb and (best is None or ca[0] + cb[0] < best[0]):
                best = (ca[0] + cb[0], "plane", w, [(c[2], c[3]) for c in (ca, cb) if c[2]], [c[1] for c in (ca, cb) if c[1]],
                        [x["label"] for x in (A, B)])
        # 3. one via between, a track on each end's layer
        if best is None and A["layers"] and B["layers"]:
            mx, my = (A["at"][0] + B["at"][0]) / 2, (A["at"][1] + B["at"][1]) / 2
            R = math.dist(A["at"], B["at"]) / 2 + 1.0
            cand = []
            for (x, y) in ring(mx, my, R, step=0.2):
                cand.append((math.dist(A["at"], (x, y)) + math.dist((x, y), B["at"]), x, y))
            cand.sort()
            for c, x, y in cand[:4000]:
                ok = None
                for size, drill in VIAS:
                    if not via_ok(x, y, net, size, drill):
                        continue
                    for la in A["layers"]:
                        for lb in B["layers"]:
                            pa = next((ps for ps in paths(target(A, la, (x, y)), (x, y)) if track_ok(ps, net, la, w)), None)
                            pb = next((ps for ps in paths((x, y), target(B, lb, (x, y))) if track_ok(ps, net, lb, w)), None)
                            if pa and pb:
                                ok = (plen(pa) + plen(pb) + 1.0, "via", w, [(pa, la), (pb, lb)], [(x, y, size, drill)])
                                break
                        if ok:
                            break
                    if ok:
                        break
                if ok:
                    best = ok
                    break
        if best:
            break
    direct = math.dist(A["at"], B["at"])
    if (best is None or (best[1] != "plane" and best[0] > 2.5 * direct + 2)) and A["layers"] and B["layers"]:
        for w in sorted({WIDTH.get(net, 0.3), 0.25, 0.2}, reverse=True):
            if w > WIDTH.get(net, 0.3):
                continue
            g = None
            for size, drill in VIAS:
                g = astar(A, B, net, w, size, drill)
                if g:
                    break
            if g and (best is None or g[0] < best[0]):
                best = g
            if g:
                break
    if not best:
        failed.append({"net": net, "a": A["label"], "b": B["label"], "dist": round(math.dist(A["at"], B["at"]), 2)})
        continue
    c, kind, w, trs, vs = best[:5]
    for ps, l in trs:
        commit_track(ps, net, l, w, res)
    for v in vs:
        commit_via(v, net, res)
    if kind == "plane":
        planed.update({lab: True for lab in best[5]})
    report.append({"net": net, "a": A["label"], "b": B["label"], "how": kind, "width": w, "mm": round(c, 2),
                   "vias": [[round(v[0], 3), round(v[1], 3)] for v in vs],
                   "tracks": [{"layer": l, "width": w, "pts": [[round(x, 3), round(y, 3)] for x, y in ps]} for ps, l in trs if ps],
                   "via_sizes": [[round(v[0], 3), round(v[1], 3), v[2], v[3]] for v in vs]})
out = {"stubs": [{"name": f"Power joins (plan_joins.py), {l} {w} mm", "layer": l, "width": w, "stubs": s}
                 for (l, w), s in sorted(res["stubs"].items())],
       "points": [{"name": f"Power joins (plan_joins.py), {s}/{d} mm vias", "size": s, "drill": d, "points": p}
                  for (s, d), p in sorted(res["points"].items())],
       "joins": report, "failed": failed}
json.dump(out, open(a.out, "w"), indent=1)
for r in report:
    print(f"{r['net']:30s} {r['a']:>26s} -> {r['b']:<26s} {r['how']:5s} w{r['width']} {r['mm']:5.2f} mm vias {r['vias']}")
for f in failed:
    print(f"FAILED {f['net']:23s} {f['a']:>26s} -> {f['b']:<26s} {f['dist']} mm apart")
print(f"{len(report)} joined, {len(failed)} failed")
