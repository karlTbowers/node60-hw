#!/usr/bin/env python3
"""mini_route.py COPPER.json JOBS.json OUT.json -- a small local router for the joins the big router leaves
(Node60 routing run, 2026-11-12). Run with a Python that has shapely 2 and numpy.

COPPER.json: power/joins/export_copper.py of the board as it is. JOBS.json: a list of
  {"net": "/NTC_RSENSE", "from": [x, y, "B.Cu"], "to": [x, y, "B.Cu"], "layers": ["B.Cu", "F.Cu", "In2.Cu"],
   "w": 0.15, "via": [0.45, 0.25], "margin": 4, "avoid": [[x0, y0, x1, y1, ["B.Cu"]]]}
routed in order, each one's copper an obstacle for the next. A* on a 0.05 mm grid over the two ends' box plus
the margin, 45-degree moves, a via where it is legal on every layer. It keeps the board's own rules:
- 0.15 mm from other nets' tracks, pads and vias (0.1 mm track and clearance inside ESCAPE_U401/U501 on the
  outer layers), 0.75 mm from T1S-class copper except inside T1S_PINS_U501 on B.Cu;
- 0.2 mm from every other net's via hole and 0.35 mm from through-hole pads' holes (node60.kicad_dru), 0.25 mm
  hole to hole, 0.5 mm from the board edge;
- F.Cu under the VBAT_IN busbar only for VBAT_IN, under the GND busbar for any net but a battery one (D33 B,
  2026-11-12: VBAT*, OUT*, RS_SENSE*); nothing on F.Cu and no via in the T1S trunk corridor
  (x 133.4-176.6, y 44.8-47.2); under the crystals no via and no B.Cu track; In2.Cu only north of y 69.5
  (the signal window); no via of another net on the In3 VBAT_PROT finger to U301 (NOVIA). Supply pours retreat round new copper but cost extra per cell (an output's pour
  most), so they are crossed only where the way round is much longer, and by the shortest cut.
A job with "to_plane": ["In1.Cu", "In4.Cu"] in place of "to" ends at the nearest legal via inside the net's own
pour on one of those layers (a supply pad's join to its plane); "to_pour": true ends where the track reaches the
net's own pour on its layer, with no via. A job that finds no way is tried again through other signal nets' tracks ("rip": false turns this off): the
tracks its path crosses are deleted and each ripped net is re-joined between its loose ends, to four levels.
T1S, RMII, clock and supply copper, pads and vias are never ripped.
OUT.json is an apply_attempt.py spec ("delete", "tracks", "vias") plus "failed"; KiCad's DRC judges the result."""
import heapq, json, math, sys
import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

C = json.load(open(sys.argv[1])); JOBS = json.load(open(sys.argv[2]))
G, SAFE = 0.05, 0.02
LAYERS = C["layers"]
P = lambda o: Polygon(o["outer"], o["holes"])
area = {}
for ar in C["areas"]:
    area[ar["name"]] = unary_union([area.get(ar["name"], Polygon())] + [P(o) for o in ar["outline"]])
ESC = unary_union([area.get("ESCAPE_U401", Polygon()), area.get("ESCAPE_U501", Polygon())])
T1SPINS = area.get("T1S_PINS_U501", Polygon())
UNDER = unary_union([area.get("UNDER_Y401", Polygon()), area.get("UNDER_Y501", Polygon())])
CORRIDOR = box(133.4, 44.8, 176.6, 47.2)
BARS = [(n.replace("BUSBAR_", ""), g) for n, g in area.items() if n.startswith("BUSBAR_")]
# Narrow fingers of a supply plane that a row of signal vias would cut (2026-11-12: seven vias cut the 1.2 mm In3
# VBAT_PROT finger to U301 and C301, x 163.2-164.4, y 47-71; the keep-outs of D17 A let vias pass). No via of
# another net within 0.4 mm of it.
NOVIA = [[162.8, 46.6, 164.8, 71.4, "VBAT_PROT"]]
BATT = lambda n: "VBAT" in n or n.startswith("/OUT") or "RS_SENSE" in n      # node60.kicad_dru: no battery-net track on F.Cu under the GND bar
e = C["edge"]; EDGE = box(e[0] + 0.5, e[1] + 0.5, e[2] - 0.5, e[3] - 0.5)

# copper per layer: (geometry, net, is_t1s); holes: (geometry, net)
cu = {l: [] for l in LAYERS}; holes = []
for p in C["pads"]:
    for l, polys in p["layers"].items():
        if l in cu: cu[l].append((unary_union([P(o) for o in polys]), p["net"], "T1S_100R" in p.get("cls", ""), None))
for t in C["tracks"]:
    g = LineString([t["a"], t["b"]]).buffer(t["w"] / 2) if t["a"] != t["b"] else Point(t["a"]).buffer(t["w"] / 2)
    if t["layer"] in cu: cu[t["layer"]].append((g, t["net"], "T1S_100R" in t.get("cls", ""), (tuple(t["a"]), tuple(t["b"]))))
for v in C["vias"]:
    g = Point(v["x"], v["y"]).buffer(v["size"] / 2)
    for l in LAYERS: cu[l].append((g, v["net"], "T1S_100R" in v.get("cls", ""), None))
    holes.append((Point(v["x"], v["y"]).buffer(v["drill"] / 2), v["net"], 0.2))
for h in C["holes"]:
    holes.append((Point(h["x"], h["y"]).buffer(h["d"] / 2), h.get("net", "") if h.get("plated") else "\0npth", 0.35))


fills = {}
for z in C["zones"]:
    if z["fill"]: fills.setdefault((z["net"], z["layer"]), []).extend(P(o) for o in z["fill"])
fills = {k: unary_union(v) for k, v in fills.items()}


def mask(geoms, xs, ys, grow):
    """cells whose centre is within grow of any geometry"""
    if not geoms: return np.zeros(xs.shape, bool)
    u = unary_union([g.buffer(grow) for g in geoms])
    return shapely.contains_xy(u, xs, ys)


NO_RIP = ("T1S", "RMII", "REFCLK", "MDIO", "FXOSC", "GND", "VBAT", "3V3_MAIN", "1V5_CORE", "VDDAU", "/OUT", "_SW", "_REG", "V11", "V25")
fresh = set()                                        # nets routed in this run: never ripped again
rippable = lambda n, seg: seg is not None and n not in fresh and not any(k in n for k in NO_RIP)
deletes = []


def route(job, soft=False):
    net, w, (vd, vdr) = job["net"], job.get("w", 0.15), job.get("via", [0.45, 0.25])
    lay = job.get("layers", ["B.Cu"]); m = job.get("margin", 4.0)
    pour = job.get("to_pour")                        # true: end where the track reaches the net's own pour on its layer (no via)
    plane = job.get("to_plane") or (job["layers"][:1] if pour else None)   # e.g. ["In1.Cu", "In4.Cu"]: end at the nearest via into the net's own plane
    if plane:
        job = dict(job, to=[job["from"][0], job["from"][1], job["from"][2]])
    (x0, y0, l0), (x1, y1, l1) = job["from"], job["to"]
    bx0, by0, bx1, by1 = min(x0, x1) - m, min(y0, y1) - m, max(x0, x1) + m, max(y0, y1) + m
    nx, ny = int((bx1 - bx0) / G) + 1, int((by1 - by0) / G) + 1
    xs, ys = np.meshgrid(bx0 + np.arange(nx) * G, by0 + np.arange(ny) * G, indexing="ij")
    win = box(bx0 - 2, by0 - 2, bx1 + 2, by1 + 2)
    inside = shapely.contains_xy(EDGE, xs, ys)
    in_esc = shapely.contains_xy(ESC.buffer(-0.12), xs, ys) if not ESC.is_empty else np.zeros(xs.shape, bool)
    in_pins = shapely.contains_xy(T1SPINS, xs, ys) if not T1SPINS.is_empty else np.zeros(xs.shape, bool)
    blocked = {}
    near = {l: [(g, n, t) for g, n, t, sg in cu[l] if n != net and g.intersects(win) and not (soft and rippable(n, sg))] for l in LAYERS}
    softs = {l: [(g, n, sg) for g, n, t, sg in cu[l] if n != net and g.intersects(win) and soft and rippable(n, sg)] for l in LAYERS}
    hl = [(g, n) for g, n, c in holes if g.intersects(win)]
    hole_via = [g for g, n, c in holes if n != net and c < 0.3 and g.intersects(win)]      # other nets' via holes: 0.2 mm
    hole_pad = [g for g, n, c in holes if n != net and c > 0.3 and g.intersects(win)]      # through-hole pads' and unplated holes: 0.35 mm
    for l in lay:
        other = [g for g, n, t in near[l] if not t]; t1 = [g for g, n, t in near[l] if t]
        b15 = mask(other, xs, ys, 0.15 + w / 2 + SAFE) | mask(hole_via, xs, ys, 0.2 + w / 2 + SAFE) | mask(hole_pad, xs, ys, 0.35 + w / 2 + SAFE)
        if l in ("F.Cu", "B.Cu"):
            we = 0.05 if w <= 0.15 else w / 2        # a signal necks to 0.1 mm in the escape areas; a supply stub keeps its width
            b10 = mask(other, xs, ys, 0.10 + we + SAFE) | mask(hole_via, xs, ys, 0.2 + we + SAFE) | mask(hole_pad, xs, ys, 0.35 + we + SAFE)
            b = np.where(in_esc, b10, b15)
        else:
            b = b15
        bt = mask(t1, xs, ys, 0.75 + w / 2 + SAFE)
        if l == "B.Cu":
            bt = np.where(in_pins, mask(t1, xs, ys, 0.15 + w / 2 + SAFE), bt)
            b |= shapely.contains_xy(UNDER.buffer(w / 2 + SAFE), xs, ys)
        if l == "F.Cu":
            b |= shapely.contains_xy(CORRIDOR.buffer(w / 2 + SAFE), xs, ys)
            for bn, bg in BARS:                      # the VBAT_IN bar: its own net only. The GND bar (D33 B): any net but a battery one
                if (bn not in net) if bn != "GND" else BATT(net): b |= shapely.contains_xy(bg.buffer(w / 2 + SAFE), xs, ys)
        if l == "In2.Cu":
            b |= ys > 69.5
        for av in job.get("avoid", []):              # [x0, y0, x1, y1, [layers]]: no copper of this job here
            if len(av) < 5 or l in av[4]: b |= (xs >= av[0]) & (xs <= av[2]) & (ys >= av[1]) & (ys <= av[3])
        blocked[l] = b | bt | ~inside
    softm = {l: mask([g for g, n, sg in softs[l]], xs, ys, 0.15 + w / 2 + SAFE) for l in lay} if soft else None
    # other nets' pours cost extra per cell (an output's pour most), so a path crosses one only where the way
    # round is much longer, and by the shortest cut (user, 2026-11-12:
    # power shapes may be trimmed slightly where a signal has no other way)
    pourc = {}; POUR_COST = job.get("pour_cost", 3.0); OUT_COST = job.get("out_cost", 10.0)
    for l in lay:
        hard = [g for (n, zl), g in fills.items() if zl == l and n != net and n.startswith("/OUT") and g.intersects(win)]
        softp = [g for (n, zl), g in fills.items() if zl == l and n != net and n != "GND" and not n.startswith("/OUT") and g.intersects(win)]
        pc = np.zeros(xs.shape)
        if softp: pc += POUR_COST * mask(softp, xs, ys, 0.0)
        if hard: pc += OUT_COST * mask(hard, xs, ys, 0.0)
        pourc[l] = pc
    # via sites: clear on every copper layer
    vr = max(vd / 2 + 0.15, vdr / 2 + 0.2) + SAFE
    vb = ~inside | shapely.contains_xy(UNDER.buffer(vd / 2), xs, ys) | shapely.contains_xy(CORRIDOR.buffer(vd / 2), xs, ys)
    for l in LAYERS:
        vb |= mask([g for g, n, t in near[l] if n != net and not t], xs, ys, vr)
        vb |= mask([g for g, n, t in near[l] if t], xs, ys, vd / 2 + 0.75 + SAFE)
    vb |= mask([g for g, n in hl], xs, ys, vdr / 2 + 0.25 + SAFE) & ~mask([g for g, n in hl if n == net], xs, ys, 0.0)
    for nv in NOVIA + job.get("no_via", []):         # [x0, y0, x1, y1]: no via of another net here (a narrow plane finger)
        if net not in nv[4:]: vb |= (xs >= nv[0] - vd / 2) & (xs <= nv[2] + vd / 2) & (ys >= nv[1] - vd / 2) & (ys <= nv[3] + vd / 2)
    if soft:                                         # a via may not land on copper that would have to be ripped
        for l in LAYERS: vb |= mask([g for g, n, sg in softs[l]], xs, ys, vr)
    if plane:                                        # goal cells: a legal via site inside the net's own fill on a plane layer
        pg = unary_union([fills[(net, l)].buffer(-(vd / 2 + 0.2)) for l in plane if (net, l) in fills] or [Polygon()])
        goal = ~vb & (shapely.contains_xy(pg, xs, ys) if not pg.is_empty else np.zeros(xs.shape, bool))
        if pour:
            pg = unary_union([fills[(net, l)].buffer(-(w / 2 + 0.1)) for l in plane if (net, l) in fills] or [Polygon()])
            goal = shapely.contains_xy(pg, xs, ys) if not pg.is_empty else np.zeros(xs.shape, bool)
    cell = lambda x, y: (int(round((x - bx0) / G)), int(round((y - by0) / G)))
    s = (lay.index(l0),) + cell(x0, y0); t = (lay.index(l1),) + cell(x1, y1)
    for k, i, j in (s, t):
        blocked[lay[k]][max(0, i - 1):i + 2, max(0, j - 1):j + 2] = False     # the ends sit on the net's own copper
    if job.get("debug"):
        b = blocked[lay[0]]; print("window", nx, ny, "blocked", round(float(b.mean()), 3), "start", s, "goal", t)
        for j in range(0, ny, 2):
            print("".join("S" if (i, j) == s[1:] or (i + 1, j) == s[1:] else "T" if abs(i - t[1]) < 2 and abs(j - t[2]) < 2 else ("#" if b[i, j] else ".") for i in range(0, nx, 2)))
    for k, i, j in (s, t):
        blocked[lay[k]][max(0, i - 1):i + 2, max(0, j - 1):j + 2] = False
    VIA_COST = job.get("via_cost", 40)
    h = (lambda n: 0.0) if plane else (lambda n: math.hypot(n[1] - t[1], n[2] - t[2]) + (0 if n[0] == t[0] else VIA_COST))
    found = None
    best = {s: 0.0}; came = {}; pq = [(h(s), 0.0, s)]
    moves = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
    while pq:
        f, g, n = heapq.heappop(pq)
        if (plane and goal[n[1], n[2]] and (g > 6 or job.get("in_pad"))) or (not plane and n == t): found = n; break
        if g > best.get(n, 1e18): continue
        k, i, j = n; b = blocked[lay[k]]
        for di, dj, c in moves:
            a, bb = i + di, j + dj
            if 0 <= a < nx and 0 <= bb < ny and not b[a, bb]:
                if di and dj and (b[i + di, j] or b[i, j + dj]): continue
                # a turn costs a little, so paths run straight
                prev = came.get(n); turn = 0.0 if prev is None or (prev[0] == k and (i - prev[1], j - prev[2]) == (di, dj)) else 0.3
                q = (k, a, bb); ng = g + c + turn + (25.0 if soft and softm[lay[k]][a, bb] else 0.0) + pourc[lay[k]][a, bb]
                if ng < best.get(q, 1e18): best[q] = ng; came[q] = n; heapq.heappush(pq, (ng + h(q), ng, q))
        if not vb[i, j]:
            for k2 in range(len(lay)):
                if k2 != k and not blocked[lay[k2]][i, j]:
                    q = (k2, i, j); ng = g + VIA_COST
                    if ng < best.get(q, 1e18): best[q] = ng; came[q] = n; heapq.heappush(pq, (ng + h(q), ng, q))
    else:
        if not soft:                                 # say which end is walled in: cells reachable from each end
            def flood(a):
                seen = {a}; st = [a]
                while st and len(seen) < 60000:
                    k, i, j = st.pop()
                    for di, dj, _ in moves[:4]:
                        q = (k, i + di, j + dj)
                        if 0 <= q[1] < nx and 0 <= q[2] < ny and q not in seen and not blocked[lay[k]][q[1], q[2]]: seen.add(q); st.append(q)
                    if not vb[i, j]:
                        for k2 in range(len(lay)):
                            q = (k2, i, j)
                            if q not in seen and not blocked[lay[k2]][i, j]: seen.add(q); st.append(q)
                return len(seen)
            print(f"        cells reachable from the start {flood(s)}, from the end {flood(t)} (60000 = open)")
        return None
    if plane: t = found; x1, y1 = bx0 + t[1] * G, by0 + t[2] * G
    path = [t]
    while path[-1] != s: path.append(came[path[-1]])
    path.reverse()
    xy = lambda n: (round(bx0 + n[1] * G, 4), round(by0 + n[2] * G, 4))
    tracks, vias, run = [], [], [(round(x0, 4), round(y0, 4)), xy(path[0])]
    for a, b_ in zip(path, path[1:]):
        if a[0] != b_[0]:
            tracks.append((lay[a[0]], run)); vias.append(xy(a)); run = [xy(a)]
        else:
            if len(run) >= 2 and abs((run[-1][0] - run[-2][0]) * (xy(b_)[1] - run[-1][1]) - (run[-1][1] - run[-2][1]) * (xy(b_)[0] - run[-1][0])) < 1e-6 and run[-1] != run[-2]:
                run[-1] = xy(b_)
            else:
                run.append(xy(b_))
    run.append((round(x1, 4), round(y1, 4))); tracks.append((lay[path[-1][0]], run))
    if plane and not pour: vias.append((round(x1, 4), round(y1, 4)))
    out_t = []
    for l, pts in tracks:
        pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
        if len(pts) < 2: continue
        # 0.1 mm inside the escape areas (both ends of a segment inside), else w
        seg = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        for a, b_ in seg:
            narrow = l in ("F.Cu", "B.Cu") and ESC.buffer(-0.07).contains(LineString([a, b_]))
            ww = 0.1 if narrow and w <= 0.15 else w
            if out_t and out_t[-1]["layer"] == l and out_t[-1]["w"] == ww and out_t[-1]["pts"][-1] == list(a):
                out_t[-1]["pts"].append(list(b_))
            else:
                out_t.append({"net": net, "layer": l, "w": ww, "pts": [list(a), list(b_)]})
    out_v = [{"net": net, "x": x, "y": y, "d": vd, "drill": vdr} for x, y in vias]
    ripped = {}
    if soft:
        for tr in out_t:
            line = LineString(tr["pts"]).buffer(tr["w"] / 2 + 0.15 + SAFE)
            for g, n, sg in softs[tr["layer"]]:
                if g.intersects(line): ripped.setdefault(n, set()).add((tr["layer"], sg))
        for n, segs in ripped.items():
            for l, sg in segs:
                cu[l][:] = [c for c in cu[l] if not (c[1] == n and c[3] == sg)]
                deletes.append({"seg": [*sg[0], *sg[1]], "layer": l, "net": n})
    # the new copper is an obstacle for later jobs
    for tr in out_t:
        for a, b_ in zip(tr["pts"], tr["pts"][1:]):
            if a != b_: cu[tr["layer"]].append((LineString([a, b_]).buffer(tr["w"] / 2), net, False, (tuple(a), tuple(b_))))
    for v in out_v:
        for l in LAYERS: cu[l].append((Point(v["x"], v["y"]).buffer(vd / 2), net, False, None))
        holes.append((Point(v["x"], v["y"]).buffer(vdr / 2), net, 0.2))
    fresh.add(net)
    mm = sum(math.dist(a, b_) for tr in out_t for a, b_ in zip(tr["pts"], tr["pts"][1:]))
    return out_t, out_v, mm, ripped


spec = {"id": JOBS[0].get("id", "mini") if JOBS else "mini", "title": "mini_route.py", "why": "local joins", "delete": [], "tracks": [], "vias": [], "failed": []}
queue = [(j, 0) for j in JOBS]
while queue:
    job, depth = queue.pop(0)
    tag = job.get("name", job["net"])
    r = route(job)
    if r is None and job.get("rip", True) and depth < 4:
        r = route(job, soft=True)                    # through other nets' tracks, which are then ripped and re-joined
    if r is None:
        spec["failed"].append(tag); print(f"FAILED  {tag}"); continue
    spec["tracks"] += r[0]; spec["vias"] += r[1]
    print(f"routed  {tag}: {r[2]:.1f} mm, {len(r[1])} via(s), layers {sorted({t['layer'] for t in r[0]})}" + (f"; ripped {sorted(r[3])}" if r[3] else ""))
    for n, segs in r[3].items():                     # re-join each ripped chain between its two loose ends
        for l in {l for l, sg in segs}:
            ends = {}
            for _, sg in [x for x in segs if x[0] == l]:
                for p_ in sg: ends[p_] = ends.get(p_, 0) + 1
            loose = [p_ for p_, k in ends.items() if k == 1]
            while len(loose) >= 2:
                a = loose.pop(0); b_ = min(loose, key=lambda q: math.dist(a, q)); loose.remove(b_)
                queue.insert(0, ({"net": n, "name": n + " (re-joined)", "from": [a[0], a[1], l], "to": [b_[0], b_[1], l],
                                  "layers": job.get("layers", ["B.Cu"]) if l in job.get("layers", ["B.Cu"]) else [l], "via": job.get("via", [0.35, 0.2]),
                                  "margin": job.get("margin", 4)}, depth + 1))
spec["delete"] = [{"seg": d["seg"]} for d in deletes]
json.dump(spec, open(sys.argv[3], "w"), indent=1)
