#!/usr/bin/env python3
"""Route the 3V3 feeds into the power band for a decision (Node60, 2026-11-05).

    python trunk_options.py COPPER.json DRC.json OPTIONS.json OUT.json

The power band has no 3V3 plane (In3 is VBAT_PROT there, In2 VBAT_PROT south of y 70) and the busbars'
F.Cu areas take every other net's track (the GND bar x 67-243, y 61-80, right across the plane's edge;
the VBAT_IN bar x 92-218, y 90-109). Each feed in OPTIONS.json is searched on a grid over F.Cu and B.Cu:
it starts at any legal via into the In3 3V3 plane (or at given copper), ends on its loads' pads in turn
(each next load from the copper laid so far), and pays for crossing other nets' pours on the outer layers,
VBAT pours most (a thin track slits a 60 A pour), GND least (In1/In4 carry ground). Layers and boxes
per feed narrow the search, so an option can force a corridor. OUT.json: per option and feed the tracks,
vias, length, and the pour area each crosses; plan_joins.py's clearances throughout.
"""
import heapq
import json
import math
import sys

import numpy as np
from shapely import contains_xy
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

copper, drc, opts_path, out_path = sys.argv[1:5]
sys.argv = ["plan_joins.py", copper, drc, "/dev/null", "--nets", "__none__"]
import plan_joins as pj  # noqa: E402  (runs its loads; no pairs match __none__)

STEP = 0.2
VIA_COST = 1.5
POUR_COST = {"GND": 0.5}          # extra cost per mm inside another net's pour; default below
POUR_DEFAULT = 6.0


def grid_for(bx, net, w, size, drill, layers, pour_default=None, block_pours=()):
    x0, y0, x1, y1 = bx
    nx, ny = int((x1 - x0) / STEP) + 1, int((y1 - y0) / STEP) + 1
    gx, gy = np.meshgrid(np.arange(nx) * STEP + x0, np.arange(ny) * STEP + y0, indexing="ij")
    B = box(x0 - 1, y0 - 1, x1 + 1, y1 + 1)
    blocked, extra = {}, {}
    vblock = np.zeros((nx, ny), bool)
    for l in pj.C["layers"]:
        geos, vgeos = [], []
        for i in pj.trees[l].query(B):
            g, n, t1s = pj.obs[l][i]
            if n != net:
                c = pj.CLR_T1S if t1s else pj.CLR
                geos.append(g.buffer(c + w / 2))
                vgeos.append(g.buffer(max(size / 2 + c, drill / 2 + pj.HCLR)))
        for g, n in pj.added[l]:
            if n != net:
                geos.append(g.buffer(pj.CLR + w / 2)); vgeos.append(g.buffer(max(size / 2 + pj.CLR, drill / 2 + pj.HCLR)))
        if vgeos:
            vblock |= contains_xy(unary_union(vgeos), gx, gy)
        if l in layers:
            if l == "F.Cu":
                geos.append(pj.KEEP.buffer(w / 2))
                for bn, bg in pj.BAR:
                    if net not in (bn, "/" + bn):
                        geos.append(bg.buffer(w / 2))
            if l == "B.Cu":
                geos.append(pj.UNDER.buffer(w / 2))
            for i in pj.htree.query(B):
                g, n, _ = pj.holes[i]
                if n != net:
                    geos.append(g.buffer(pj.HCLR + w / 2))
            for (n, ll), g in pj.fills.items():
                if ll == l and n in block_pours:
                    geos.append(g.intersection(B).buffer(pj.CLR + w / 2))
            blocked[l] = contains_xy(unary_union(geos), gx, gy) if geos else np.zeros((nx, ny), bool)
            cost = np.zeros((nx, ny))
            for (n, ll), g in pj.fills.items():
                if ll == l and n != net:
                    inside = contains_xy(g.intersection(B), gx, gy)
                    cost = np.maximum(cost, inside * POUR_COST.get(n, pour_default if pour_default is not None else POUR_DEFAULT))
            extra[l] = cost
    for i in pj.htree.query(B):
        g, n, _ = pj.holes[i]
        vblock |= contains_xy(g.buffer(pj.H2H + drill / 2), gx, gy)
    vblock |= contains_xy(pj.KEEP.buffer(size / 2), gx, gy)
    vblock |= contains_xy(pj.UNDER.buffer(size / 2), gx, gy)
    plane = pj.fills.get((net, "In3.Cu"))
    vplane = contains_xy(plane.buffer(-(size / 2 + 0.05)), gx, gy) if plane is not None else np.zeros((nx, ny), bool)
    return (x0, y0, nx, ny, gx, gy), blocked, extra, vblock, vplane


def search(bx, net, w, size, drill, layers, starts_from_plane, start_geo, goal_geo, pour_default=None, block_pours=(), plane_ymin=None):
    G, blocked, extra, vblock, vplane = grid_for(bx, net, w, size, drill, layers, pour_default, block_pours)
    x0, y0, nx, ny, gx, gy = G
    if plane_ymin is not None:
        vplane = vplane & (gy >= plane_ymin)
    ls = list(layers)
    goal = {}
    for k, l in enumerate(ls):
        if l in goal_geo:
            m = contains_xy(goal_geo[l], gx, gy)
            blocked[l] &= ~m
            goal[k] = m
    openq, best, prev = [], {}, {}
    for k, l in enumerate(ls):
        s = np.zeros((nx, ny), bool)
        if starts_from_plane:
            s |= vplane & ~vblock & ~blocked[l]
        if l in start_geo:
            m = contains_xy(start_geo[l], gx, gy)
            blocked[l] &= ~m
            s |= m
        for i, j in zip(*np.nonzero(s)):
            c0 = VIA_COST if starts_from_plane and not (l in start_geo and contains_xy(start_geo[l], gx[i, j], gy[i, j])) else 0.0
            best[(k, i, j)] = c0
            heapq.heappush(openq, (c0, c0, (k, i, j), None))
    D = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
    gc = [(gx[i, j], gy[i, j]) for k in goal for i, j in zip(*np.nonzero(goal[k]))]
    gpts = np.array(gc) if gc else np.zeros((1, 2))

    def h(i, j):
        return float(np.min(np.hypot(gpts[:, 0] - gx[i, j], gpts[:, 1] - gy[i, j]))) * 0.999

    found = None
    it = 0
    while openq and it < 3_000_000:
        it += 1
        f, g, c, d0 = heapq.heappop(openq)
        if g > best.get(c, 1e18) + 1e-9:
            continue
        k, i, j = c
        if k in goal and goal[k][i, j]:
            found = c
            break
        for di, dj, cost in D:
            ni, nj = i + di, j + dj
            if not (0 <= ni < nx and 0 <= nj < ny) or blocked[ls[k]][ni, nj]:
                continue
            ng = g + cost * STEP * (1 + extra[ls[k]][ni, nj]) + (0.1 if d0 is not None and d0 != (di, dj) else 0)
            nc = (k, ni, nj)
            if ng < best.get(nc, 1e18):
                best[nc] = ng; prev[nc] = c; heapq.heappush(openq, (ng + h(ni, nj), ng, nc, (di, dj)))
        if len(ls) == 2 and not vblock[i, j] and not blocked[ls[1 - k]][i, j]:
            nc = (1 - k, i, j)
            ng = g + VIA_COST
            if ng < best.get(nc, 1e18):
                best[nc] = ng; prev[nc] = c; heapq.heappush(openq, (ng + h(i, j), ng, nc, None))
    if not found:
        return None
    path = [found]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    first = path[0]
    plane_via = starts_from_plane and not any(ls[first[0]] in start_geo and contains_xy(start_geo[ls[first[0]]], gx[first[1], first[2]], gy[first[1], first[2]]) for _ in [0])
    vias, segs, cur = [], [], [path[0]]
    if plane_via:
        vias.append((round(float(gx[first[1], first[2]]), 3), round(float(gy[first[1], first[2]]), 3)))
    for c in path[1:]:
        if c[0] != cur[-1][0]:
            segs.append(cur); vias.append((round(float(gx[c[1], c[2]]), 3), round(float(gy[c[1], c[2]]), 3))); cur = [c]
        else:
            cur.append(c)
    segs.append(cur)
    tracks = []
    for sg in segs:
        pts = [(round(float(gx[c[1], c[2]]), 3), round(float(gy[c[1], c[2]]), 3)) for c in sg]
        simp = [pts[0]]
        for q in range(1, len(pts) - 1):
            ax, ay = pts[q][0] - simp[-1][0], pts[q][1] - simp[-1][1]
            bx_, by_ = pts[q + 1][0] - pts[q][0], pts[q + 1][1] - pts[q][1]
            if abs(ax * by_ - ay * bx_) > 1e-9:
                simp.append(pts[q])
        simp.append(pts[-1])
        if len(simp) >= 2 and simp[0] != simp[-1]:
            tracks.append({"layer": ls[sg[0][0]], "pts": simp})
    return {"tracks": tracks, "vias": vias, "cost": round(best[found], 2)}


def pad_geo(ref, num):
    return {l: g for (r, n, l), g in pj.pad_geo.items() if r == ref and n == num}


def crossings(tracks, net, w):
    """mm of track inside other nets' pours, per net"""
    out = {}
    for t in tracks:
        ln = LineString(t["pts"])
        for (n, l), g in pj.fills.items():
            if l == t["layer"] and n != net:
                L = ln.intersection(g).length
                if L > 0.05:
                    out[n] = round(out.get(n, 0) + L, 1)
    return out


opts = json.load(open(opts_path))
res = {}
for oname, o in opts.items():
    res[oname] = {"about": o.get("about", ""), "feeds": []}
    for f in o["feeds"]:
        net, w = f.get("net", "3V3_MAIN"), f.get("width", 0.3)
        layers = tuple(f.get("layers", ["F.Cu", "B.Cu"]))
        laid = {}
        pieces = []
        total = {"mm": 0.0, "vias": 0, "cross": {}}
        ok = True
        for k, load in enumerate(f["loads"]):
            ref, num = load.split(".")
            goal = pad_geo(ref, num)
            if k == 0:
                start_geo = {}
                if f.get("from_box"):
                    from shapely.geometry import box as _box
                    for l in layers:
                        start_geo[l] = _box(*f["from_box"])
                for s in f.get("from", []):
                    r2, n2 = s.split(".")
                    for l, g in pad_geo(r2, n2).items():
                        start_geo[l] = start_geo[l].union(g) if l in start_geo else g
                from_plane = f.get("from_plane", True)
            else:
                start_geo = {l: unary_union(gs) for l, gs in laid.items()}
                from_plane = False
            pts = [g.centroid for g in goal.values()] + [g.centroid for g in start_geo.values()]
            bx = f.get("box")
            if not bx:
                xs = [p.x for p in pts]; ys = [p.y for p in pts]
                bx = [min(xs) - 12, min(ys + [62]) - 4, max(xs) + 12, max(ys) + 6]
            r = search(bx, net, w, f.get("via", 0.45), f.get("drill", 0.25), layers, from_plane, start_geo, goal, f.get("pour_cost"), tuple(f.get("block_pours", [])), f.get("plane_ymin"))
            if not r:
                ok = False
                pieces.append({"load": load, "failed": True})
                break
            for t in r["tracks"]:
                g = LineString(t["pts"]).buffer(w / 2)
                laid.setdefault(t["layer"], []).append(g)
                pj.added[t["layer"]].append((g, net))
            for (x, y) in r["vias"]:
                g = Point(x, y).buffer(f.get("via", 0.45) / 2)
                for l in pj.C["layers"]:
                    pj.added[l].append((g, net))
                    if l in layers:
                        laid.setdefault(l, []).append(g)
                pj.added_holes.append((Point(x, y).buffer(0.125), net))
            L = sum(LineString(t["pts"]).length for t in r["tracks"])
            cr = crossings(r["tracks"], net, w)
            total["mm"] += L; total["vias"] += len(r["vias"])
            for n, v in cr.items():
                total["cross"][n] = round(total["cross"].get(n, 0) + v, 1)
            pieces.append({"load": load, "tracks": r["tracks"], "vias": r["vias"], "mm": round(L, 1), "cross": cr})
        total["mm"] = round(total["mm"], 1)
        res[oname]["feeds"].append({"name": f["name"], "net": net, "ok": ok, "width": w, "via": f.get("via", 0.45), "drill": f.get("drill", 0.25), "total": total, "pieces": pieces})
        print(f"{oname:10s} {f['name']:28s} {'ok ' if ok else 'FAIL'} {total['mm']:6.1f} mm {total['vias']} vias cross {total['cross']}")
    # each option starts from the board as it is
    for l in pj.added:
        pj.added[l] = []
    pj.added_holes.clear()
json.dump(res, open(out_path, "w"), indent=1)
