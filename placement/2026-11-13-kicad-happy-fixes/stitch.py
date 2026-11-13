#!/usr/bin/env python3
"""stitch.py COPPER.json OUT_SPEC.json [--returns-only] -- N6: GND return vias and interior stitching (needs shapely;
COPPER.json from placement/2026-11-02-bars/power/joins/export_copper.py, zones filled).

Pass 1, return vias: for every via of a signal net with no GND via within 1.0 mm, the nearest legal site within
1.0 mm of it (0.45/0.25 mm, else 0.40/0.20 mm), else within 1.5 mm. Fast nets first (RMII, REF_CLK, oscillator, MDIO, SPI), then I2C/UART, then every other signal.
Pass 2, stitching: a 5 mm grid over the interior; where no GND via stands within 2.5 mm, the legal site nearest
the grid point (within 1.8 mm).

A legal site for a 0.45/0.25 mm GND via:
- 0.20 mm (stitching) or 0.16 mm (return vias) from every other net's track, via and pad on every layer (the
  rules ask 0.10 outer, 0.15 inner),
  and from every pad of any net (no via in a pad); 0.85 mm from T1S-class copper (rule: 0.75);
- hole 0.30 mm from other vias' holes (rule 0.25), via 0.40 mm from plated holes of parts (rule 0.35);
- on F.Cu, In2 and B.Cu not within 0.6 mm of any other net's pour; on In3 not within 1.0 mm of a VBAT_PROT or
  1V5_CORE pour (so never on the VBAT_PROT fingers to U301 and L201) and, on the In2 side, the VBAT_IN finger
  PWR_VBAT_IN_U201_In2 is such a pour; 3V3_MAIN on In3 is the one plane a via may pass through;
- stitching vias (pass 2) only where In3's 3V3 plane is whole for 0.75 mm round the site or absent, so the new
  antipad joins no other and no row of them cuts the plane;
- not in the T1S trunk corridor (x 133.4-176.6, y 44.8-47.2), not under Y401/Y501 (UNDER_* areas + 0.5 mm),
  not inside U401's body, 1.5 mm from the board edge, and outside the power band (y > 70.5 between x 72 and 238)
  where both outer layers are battery pour, and off the rule proofs' test ground (x 93.5-102.5, y 34.5-42.5).
KiCad's DRC is the judge afterwards; this only proposes."""
import json, math, sys
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely.strtree import STRtree

import fnmatch, os, subprocess
ROOT = subprocess.run(["git", "-C", os.path.dirname(os.path.abspath(__file__)), "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
PAT = json.load(open(os.path.join(ROOT, "node60.kicad_pro")))["net_settings"]["netclass_patterns"]
def cls_of(net):                         # the export of a board copy has no project beside it: classes from the project's patterns
    return next((p["netclass"] for p in PAT if fnmatch.fnmatchcase(net, p["pattern"])), "Default")
C = json.load(open(sys.argv[1])); RET_ONLY = "--returns-only" in sys.argv
R, HR = 0.225, 0.125
LAYERS = C["layers"]
U401 = box(192.9, 43.46, 208.95, 59.51)
CORRIDOR = box(133.4, 44.8, 176.6, 47.2)
BAND = box(72, 70.5, 238, 122)
PROOF = box(93.5, 34.5, 102.5, 42.5)     # prove_rules.py plants its test tracks on this copper-free ground (FREE)
E = C["edge"]; INSIDE = box(E[0] + 1.5, E[1] + 1.5, E[2] - 1.5, E[3] - 1.5)
UNDER = unary_union([Polygon(o["outer"]).buffer(0.5) for a in C["areas"] if a["name"].startswith("UNDER_") for o in a["outline"]])

for k in ("tracks", "vias", "pads"):
    for t in C[k]: t["cls"] = cls_of(t["net"]) if t["net"] else ""
def P(o): return Polygon(o["outer"], o["holes"])
obs = {l: [] for l in LAYERS}; t1s = {l: [] for l in LAYERS}
for t in C["tracks"]:
    if t["net"] == "GND": continue
    g = LineString([t["a"], t["b"]]).buffer(t["w"] / 2)
    (t1s if t["cls"] == "T1S_100R" else obs)[t["layer"]].append(g)
for v in C["vias"]:
    if v["net"] == "GND": continue
    g = Point(v["x"], v["y"]).buffer(v["size"] / 2)
    for l in LAYERS: (t1s if v["cls"] == "T1S_100R" else obs)[l].append(g)
for p in C["pads"]:
    for l, polys in p["layers"].items():
        for o in polys: (t1s if p["cls"] == "T1S_100R" else obs)[l].append(P(o))
tree = {l: STRtree(obs[l]) for l in LAYERS}; ttree = {l: STRtree(t1s[l]) if t1s[l] else None for l in LAYERS}
holes = [(h["x"], h["y"], h["d"], True) for h in C["holes"]] + [(v["x"], v["y"], v["drill"], False) for v in C["vias"]]
gnd = [(v["x"], v["y"]) for v in C["vias"] if v["net"] == "GND"] + [(h["x"], h["y"]) for h in C["holes"] if h["net"] == "GND" and h["plated"]]
def grid_of(pts, cell):
    g = {}
    for p in pts: g.setdefault((int(p[0] // cell), int(p[1] // cell)), []).append(p)
    return g
HG = grid_of(holes, 2.0)
def near(g, cell, x, y):
    cx, cy = int(x // cell), int(y // cell)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1): yield from g.get((cx + dx, cy + dy), [])
# pours
ban = {}
for l in LAYERS:
    polys = []
    for z in C["zones"]:
        if z["layer"] != l or z["net"] == "GND": continue
        if l == "In3.Cu" and z["net"] == "3V3_MAIN": continue
        polys += [P(o).buffer(1.0 if l == "In3.Cu" else 0.6) for o in z["fill"]]
    ban[l] = prep(unary_union(polys)) if polys else None
v33 = unary_union([P(o) for z in C["zones"] if z["layer"] == "In3.Cu" and z["net"] == "3V3_MAIN" for o in z["fill"]])
v33_whole, v33_any = prep(v33.buffer(-0.75)), prep(v33.buffer(0.45))
gndp = {l: prep(unary_union([P(o) for z in C["zones"] if z["layer"] == l and z["net"] == "GND" for o in z["fill"]]).buffer(-0.3)) for l in ("In1.Cu", "In4.Cu")}
new = []

why = {}
def legal(x, y, strict):
    r = legal_(x, y, strict)
    if r is not True: why[r] = why.get(r, 0) + 1
    return r is True
def legal_(x, y, strict):
    pt = Point(x, y); CL = 0.2 if strict else 0.16
    if not INSIDE.contains(pt) or U401.contains(pt) or CORRIDOR.contains(pt) or BAND.contains(pt) or PROOF.contains(pt) or UNDER.contains(pt): return 'area'
    for hx, hy, d, pth in near(HG, 2.0, x, y):
        if math.hypot(hx - x, hy - y) < (R + d / 2 + 0.4 if pth else HR + d / 2 + 0.3): return 'hole'
    for nx, ny in new:
        if math.hypot(nx - x, ny - y) < 0.8: return 'new'
    for l in LAYERS:
        for i in tree[l].query(pt.buffer(R + CL)):
            if obs[l][i].distance(pt) < R + CL: return 'copper ' + l
        if ttree[l] is not None:
            for i in ttree[l].query(pt.buffer(R + 0.85)):
                if t1s[l][i].distance(pt) < R + 0.85: return 't1s'
        if ban[l] is not None and ban[l].contains(pt): return 'pour ' + l
    if strict and not (gndp["In1.Cu"].contains(pt) and gndp["In4.Cu"].contains(pt)): return 'gnd plane'
    if strict and not (v33_whole.contains(pt) or not v33_any.contains(pt)): return '3v3 web'
    return True

SIG_SKIP = lambda v: v["net"] in ("GND", "") or v["cls"].startswith("PWR") or v["cls"] in ("T1S_100R", "SW_NODE") or \
    any(s in v["net"] for s in ("3V3", "1V5", "VDD", "VBAT", "V11", "V25", "VREF", "FXOSC")) or v["net"].endswith("_SW")
def rank(n):
    if any(s in n for s in ("RMII0_", "REFCLK", "OSC_OUT", "MDIO0_", "SPI")): return 0
    if any(s in n for s in ("I2C", "UART", "RESET", "SWD", "JTAG")): return 1
    return 2
sig = sorted([v for v in C["vias"] if not SIG_SKIP(v)], key=lambda v: (rank(v["net"]), v["net"], v["x"], v["y"]))
GG = grid_of(gnd, 2.0); out = []; stats = {}
def has_gnd(x, y, r):
    return any(math.hypot(gx - x, gy - y) <= r for gx, gy in near(GG, 2.0, x, y))
for v in sig:
    k = rank(v["net"]); s = stats.setdefault(k, {"vias": 0, "had": 0, "added": 0, "none": 0}); s["vias"] += 1
    if has_gnd(v["x"], v["y"], 1.0): s["had"] += 1; continue
    best = None
    # 0.45/0.25 within 1.0 mm, then 0.40/0.20 (0.10 mm ring as well) within 1.0 mm, then either out to 1.5 mm
    for (R, HR), radii in (((0.225, 0.125), (0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00)), ((0.2, 0.1), (0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00)),
                           ((0.225, 0.125), (1.1, 1.2, 1.3, 1.4, 1.5)), ((0.2, 0.1), (1.1, 1.2, 1.3, 1.4, 1.5))):
        for r in radii:
            for a in range(0, 360, 10):
                x, y = round(v["x"] + r * math.cos(math.radians(a)), 3), round(v["y"] + r * math.sin(math.radians(a)), 3)
                if legal(x, y, False): best = (x, y, r); break
            if best: break
        if best: break
    if best:
        far = best[2] > 1.0; best = best[:2]
        new.append(best); GG.setdefault((int(best[0] // 2.0), int(best[1] // 2.0)), []).append(best); s["added"] += 1; s["far"] = s.get("far", 0) + far
        out.append({"net": "GND", "x": best[0], "y": best[1], "d": 2 * R, "drill": 2 * HR, "why": f"return via for {v['net'].split('/')[-1]} via at ({v['x']:.3f}, {v['y']:.3f})" + (" (1.0 to 1.5 mm away)" if far else "")})
    else:
        s["none"] += 1; out.append({"skip": True, "why": f"no site within 1.5 mm of {v['net'].split('/')[-1]} via at ({v['x']:.3f}, {v['y']:.3f})", "rank": k})
R, HR = 0.225, 0.125
print("sites refused, by first reason:", dict(sorted(why.items(), key=lambda kv: -kv[1]))); why.clear()
print("return vias by rank (0 fast, 1 bus/reset, 2 other):", stats)
ns = 0
if not RET_ONLY:
    gx = E[0] + 5
    while gx < E[2] - 2:
        gy = E[1] + 5
        while gy < E[3] - 2:
            if not has_gnd(gx, gy, 2.5):
                best = None
                for r in [0] + [k * 0.2 for k in range(1, 10)]:
                    for a in ([0] if r == 0 else range(0, 360, 15)):
                        x, y = round(gx + r * math.cos(math.radians(a)), 3), round(gy + r * math.sin(math.radians(a)), 3)
                        if legal(x, y, True): best = (x, y); break
                    if best: break
                if best:
                    new.append(best); GG.setdefault((int(best[0] // 2.0), int(best[1] // 2.0)), []).append(best); ns += 1
                    out.append({"net": "GND", "x": best[0], "y": best[1], "d": 0.45, "drill": 0.25, "why": f"stitching, grid point ({gx:.0f}, {gy:.0f})"})
            gy += 5
        gx += 5
print("stitching vias:", ns)
json.dump({"_": "N6: GND return vias and interior stitching (stitch.py)", "vias": [o for o in out if not o.get("skip")],
           "no_site": [o for o in out if o.get("skip")]}, open(sys.argv[2], "w"), indent=1)
