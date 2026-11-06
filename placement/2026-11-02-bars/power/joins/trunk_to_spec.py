#!/usr/bin/env python3
"""Add one option of trunk_options.py's result to a power_shapes spec (Node60, 2026-11-05).

    python3 trunk_to_spec.py SPEC.json RESULT.json OPTION OUT_SPEC.json [--feeds NAME,NAME]

Each feed becomes named "stubs" and "points" entries (3V3_MAIN, its width, 0.45/0.25 vias) for
draw_power.py; --feeds keeps only those feeds.
"""
import json
import sys

spec, res, opt, out = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3], sys.argv[4]
keep = set(sys.argv[sys.argv.index("--feeds") + 1].split(",")) if "--feeds" in sys.argv else None
n = 0
for f in res[opt]["feeds"]:
    if keep and f["name"] not in keep:
        continue
    net = f.get("net", "3V3_MAIN")
    name = f"{opt}: {f['name']}"
    for pc in f["pieces"]:
        for t in pc.get("tracks", []):
            p = t["pts"]
            spec["stubs"].append({"name": name, "layer": t["layer"], "width": f["width"],
                                  "stubs": [[*p[i], *p[i + 1], net] for i in range(len(p) - 1)]})
        for x, y in pc.get("vias", []):
            spec["points"].append({"name": name, "size": f.get("via", 0.45), "drill": f.get("drill", 0.25), "points": [[x, y, net]]})
    n += 1
json.dump(spec, open(out, "w"), indent=1)
print(f"{out}: {n} feeds of option {opt}")
