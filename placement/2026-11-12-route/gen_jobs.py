#!/usr/bin/env python3
"""gen_jobs.py DRC.json BOARD_DUMP.json OUT.jobs.json [--supply | --signal] [--pour-cost N] -- mini_route.py jobs from a DRC
report's unconnected items (those at a test point left out unless --tp).

--supply: for each pad, track end or via of a plane net that DRC lists as unconnected, a "to_plane" job to the
          nearest via into that net's plane (GND: In1/In4; VBAT_PROT: In2/In3; 3V3_MAIN, 1V5_CORE: In3;
          VBAT_IN, VBAT_D, VBAT_Q2D: In2/In3). Nets with no plane (VDDAU_AON, VBAT_FILT) become point-to-point jobs.
--signal: a point-to-point job per unconnected item pair, between the two items' positions.
BOARD_DUMP.json is dump_board.py's (pad layers)."""
import json, re, sys
d = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2])); mode = sys.argv[4] if len(sys.argv) > 4 else "--signal"
tp = "--tp" in sys.argv
MARGIN = float(sys.argv[sys.argv.index("--margin") + 1]) if "--margin" in sys.argv else 5
SKIP = sys.argv[sys.argv.index("--skip") + 1].split(",") if "--skip" in sys.argv else []
POUR = {"pour_cost": float(sys.argv[sys.argv.index("--pour-cost") + 1])} if "--pour-cost" in sys.argv else {}   # battery pours: dearer than any way round
ONLY = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
PLANES = {"GND": ["In1.Cu", "In4.Cu"], "VBAT_PROT": ["In2.Cu", "In3.Cu"], "3V3_MAIN": ["In3.Cu"], "1V5_CORE": ["In3.Cu"],
          "/VBAT_IN": ["In2.Cu"], "/Power entry/VBAT_D": ["In2.Cu", "In3.Cu"], "/Power entry/VBAT_Q2D": ["In2.Cu", "In3.Cu"]}
SUPPLY = set(PLANES) | {"VDDAU_AON", "VBAT_FILT", "/OUT1", "/OUT2", "/OUT3", "/OUT4", "/OUT5", "/OUT6"}
W = {"GND": 0.3, "VBAT_PROT": 0.4, "3V3_MAIN": 0.3, "1V5_CORE": 0.3, "/VBAT_IN": 0.4, "VDDAU_AON": 0.3, "VBAT_FILT": 0.3}
pads = {(f["ref"], p["num"]): (p, f) for f in b["footprints"] for p in f["pads"]}
def layer_of(desc):
    m = re.search(r" on (F|B|In2)\.Cu", desc); return (m.group(1) + ".Cu") if m else "B.Cu"
jobs, seen = [], set()
for u in d.get("unconnected_items", []):
    s = " | ".join(i["description"] for i in u["items"])
    if re.search(r"of TP\d+", s) and not tp: continue
    if "--tp-only" in sys.argv and not re.search(r"of TP\d+", s): continue
    net = re.findall(r"\[([^\]]+)\]", s)[0]
    if (net in SUPPLY) != (mode == "--supply") or any(k in net for k in SKIP) or (ONLY and not any(k in net for k in ONLY)): continue
    ends = []
    for i in u["items"]:
        m = re.match(r"Pad (\S+) \[.*\] of (\S+) on", i["description"])
        if m and (m.group(2), m.group(1)) in pads:
            p, f = pads[(m.group(2), m.group(1))]; ends.append((round(p["x"], 4), round(p["y"], 4), layer_of(i["description"]), f"{m.group(2)}.{m.group(1)}"))
        elif i["description"].startswith("Zone"):
            ends.append(None)
        else:
            ends.append((i["pos"]["x"], i["pos"]["y"], layer_of(i["description"]), i["description"].split(" [")[0]))
    if mode == "--supply" and net in PLANES:
        for e in ends:
            if e is None or (net, e[0], e[1]) in seen: continue
            seen.add((net, e[0], e[1]))
            jobs.append({"net": net, "name": f"{net} {e[3]} to its plane", "from": [e[0], e[1], e[2]], "to_plane": PLANES[net], "layers": [e[2]],
                         "w": W.get(net, 0.3), "via": [0.45, 0.25], "margin": 3, "rip": False})
    elif None not in ends and len(ends) == 2:
        a, c = ends
        lay = sorted({a[2], c[2]} | ({"B.Cu", "F.Cu", "In2.Cu"} if mode == "--signal" else {"B.Cu", "F.Cu"}))
        jobs.append({"net": net, "name": f"{net} {a[3]} to {c[3]}", "from": list(a[:3]), "to": list(c[:3]), "layers": lay,
                     "w": W.get(net, 0.15), "via": [0.35, 0.2] if mode == "--signal" else [0.45, 0.25], "margin": MARGIN, "rip": "--rip" in sys.argv, **POUR})
import math
if "--short-first" in sys.argv:                     # local joins before the long ones that would fence them in
    jobs.sort(key=lambda j: math.dist(j["from"][:2], j["to"][:2]) if "to" in j else 0)
if "--order" in sys.argv:                           # these nets first, in this order (a cell's lines before its local joins)
    order = sys.argv[sys.argv.index("--order") + 1].split(",")
    rank = lambda j: next((i for i, k in enumerate(order) if k in j["net"]), len(order))
    jobs.sort(key=rank)
json.dump(jobs, open(sys.argv[3], "w"), indent=1); print(len(jobs), "jobs")
