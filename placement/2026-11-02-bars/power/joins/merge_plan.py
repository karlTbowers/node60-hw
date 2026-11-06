#!/usr/bin/env python3
"""Add chosen joins from plan_joins.py's OUT.json to a power_shapes spec (Node60 power joins, 2026-11-05).

    python3 merge_plan.py SPEC.json PLAN.json OUT_SPEC.json [--drop NET:A:B ...] [--max-mm N]

Each join becomes its own "stubs" and "points" entries named after its two ends, so the spec says
what every piece of copper joins. --drop leaves a join out (NET:A:B as plan_joins prints them),
--max-mm leaves out every join longer than N mm (drawn by hand instead).
"""
import json
import sys

args = sys.argv[1:]
spec, plan, out = json.load(open(args[0])), json.load(open(args[1])), args[2]
drops = {a for i, a in enumerate(args) if i and args[i - 1] == "--drop"}
mx = float(args[args.index("--max-mm") + 1]) if "--max-mm" in args else 1e9
n = 0
for j in plan["joins"]:
    tag = f"{j['net']}:{j['a']}:{j['b']}"
    if tag in drops or j["mm"] > mx:
        print("left out:", tag, j["mm"], "mm")
        continue
    name = f"Power join {j['net'].split('/')[-1]}: {j['a']} to {j['b']} ({j['how']}, plan_joins.py)"
    for t in j["tracks"]:
        pts = t["pts"]
        spec["stubs"].append({"name": name, "layer": t["layer"], "width": t["width"],
                              "stubs": [[*pts[i], *pts[i + 1], j["net"]] for i in range(len(pts) - 1)]})
    for x, y, s, d in j["via_sizes"]:
        spec["points"].append({"name": name, "size": s, "drill": d, "points": [[x, y, j["net"]]]})
    n += 1
json.dump(spec, open(out, "w"), indent=1)
print(f"{out}: {n} joins added")
