#!/usr/bin/env python3
"""gen_island_jobs.py COPPER.json OUT.jobs.json [NET] -- a "to_plane" job for every piece of a net's outer-layer
pour (default GND) that holds a pad of the net but no via or through-hole pad of it: signal tracks cut the
pour into pieces, and a piece with only surface pads hangs off the planes. The job starts at a pad in the
piece and ends at the nearest legal via into In1/In4. Needs shapely."""
import json, sys
from shapely.geometry import Point, Polygon
C = json.load(open(sys.argv[1])); NET = sys.argv[3] if len(sys.argv) > 3 else "GND"
PLANES = {"GND": ["In1.Cu", "In4.Cu"]}.get(NET, ["In2.Cu", "In3.Cu"])
thru = [(v["x"], v["y"]) for v in C["vias"] if v["net"] == NET] + \
       [(p["x"], p["y"]) for p in C["pads"] if p["net"] == NET and len(p["layers"]) > 2]
jobs = []
for z in C["zones"]:
    if z["net"] != NET or z["layer"] not in ("F.Cu", "B.Cu"): continue
    for o in z["fill"]:
        g = Polygon(o["outer"], o["holes"]); gb = g.buffer(0.05)
        bx = g.bounds
        if any(bx[0] <= x <= bx[2] and bx[1] <= y <= bx[3] and gb.contains(Point(x, y)) for x, y in thru): continue
        pads = [p for p in C["pads"] if p["net"] == NET and z["layer"] in p["layers"] and not p["ref"].startswith("TP")
                and bx[0] - 1 <= p["x"] <= bx[2] + 1 and bx[1] - 1 <= p["y"] <= bx[3] + 1 and gb.intersects(Polygon(p["layers"][z["layer"]][0]["outer"]))]
        if not pads: continue
        p = pads[0]
        jobs.append({"net": NET, "name": f"{NET} pour piece at {p['ref']}.{p['num']} ({g.area:.1f} mm2, {z['layer']}) to its plane",
                     "from": [round(p["x"], 4), round(p["y"], 4), z["layer"]], "to_plane": PLANES, "layers": [z["layer"]],
                     "w": 0.3, "via": [0.45, 0.25], "margin": 3, "rip": False, "in_pad": True})
json.dump(jobs, open(sys.argv[2], "w"), indent=1); print(len(jobs), "pour pieces without a via")
