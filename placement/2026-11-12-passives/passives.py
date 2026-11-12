"""Table of every two-pad passive: what it does, how far it sits from what it serves, and whether
its supply pad stands over that supply's plane.  usage: python3 passives.py data/main.json data/planes_main.json [--json out]"""
import sys, json, math, re, collections
d = json.load(open(sys.argv[1])); pl = json.load(open(sys.argv[2]))
POWER = {"GND", "3V3_MAIN", "1V5_CORE", "VBAT_PROT", "VBAT_FILT", "VDDAU_AON", "/VBAT_IN"}
def ispow(n): return n in POWER or n.startswith("/OUT") or "VBAT_" in n or "V11" in n or "V25" in n
fps = {f["ref"]: f for f in d["footprints"]}
parked = lambda f: f["y"] > 140.5
bynet = collections.defaultdict(list)
for f in d["footprints"]:
    if parked(f): continue
    for p in f["pads"]:
        if p["net"]: bynet[p["net"]].append((f["ref"], p))
layers = pl["layers"]
def grid_near(net, x, y):
    best = (1e9, None)
    for L, g in pl["grid"].items():
        if net not in g["nets"]: continue
        k = g["nets"].index(net)
        for j, row in enumerate(g["rows"]):
            yy = 30.5 + j
            if abs(yy - y) > best[0]: continue
            for i, v in enumerate(row):
                if v == k:
                    dd = math.hypot(40.5 + i - x, yy - y)
                    if dd < best[0]: best = (dd, L)
    return best
def has_copper(net, x, y):
    for t in d["tracks"]:
        if t["net"] == net and (math.hypot(t["x1"]-x, t["y1"]-y) < 0.6 or math.hypot(t["x2"]-x, t["y2"]-y) < 0.6): return True
    for v in d["vias"]:
        if v["net"] == net and math.hypot(v["x"]-x, v["y"]-y) < 0.8: return True
    return False
rows = []
for f in d["footprints"]:
    if not re.match(r"^(R|C|RT|L|D)\d", f["ref"]) or parked(f): continue
    pads = [p for p in f["pads"] if p["net"]]
    if len({p["num"] for p in pads}) != 2: continue
    r = {"ref": f["ref"], "value": f["value"], "side": f["side"], "x": round(f["x"], 2), "y": round(f["y"], 2), "rot": f["rot"], "fp": f["fp"], "pads": []}
    for p in pads[:2]:
        others = [(ref, q) for ref, q in bynet[p["net"]] if ref != f["ref"]]
        ics = [(ref, q) for ref, q in others if re.match(r"^(U|Q|J|K|Y|FL|BB)\d", ref)]
        e = {"num": p["num"], "net": p["net"], "pow": ispow(p["net"]), "n_other": len(others), "routed": has_copper(p["net"], p["x"], p["y"])}
        near = sorted(((math.hypot(q["x"]-p["x"], q["y"]-p["y"]), ref, q) for ref, q in (ics or others)), key=lambda t: t[0])
        e["near"] = [(round(dist, 1), ref + "." + q["num"], fps[ref]["side"] if q["layer"] != "*" else "*") for dist, ref, q in near[:3]]
        e["all"] = [(round(math.hypot(q["x"]-p["x"], q["y"]-p["y"]), 1), ref + "." + q["num"]) for ref, q in others]
        e["under"] = dict(zip(layers, pl["pads"][f["ref"] + "." + p["num"]]))
        if e["pow"]:
            on = [L for L, n in e["under"].items() if n == p["net"]]
            e["plane_here"] = on
            if not on: e["plane_near"] = grid_near(p["net"], p["x"], p["y"])
        r["pads"].append(e)
    a, b = r["pads"]
    if a["pow"] and b["pow"]:
        r["kind"] = "bypass" if "GND" in (a["net"], b["net"]) else "power-series"
    elif a["pow"] or b["pow"]:
        pw, sg = (a, b) if a["pow"] else (b, a)
        if f["ref"][0] == "C": r["kind"] = "filter-cap"
        elif pw["net"] == "GND": r["kind"] = "pull-down/set" 
        else: r["kind"] = "pull-up"
    else: r["kind"] = "series"
    rows.append(r)
if "--json" in sys.argv: json.dump(rows, open(sys.argv[sys.argv.index("--json")+1], "w"), indent=1)
for kind in ("pull-up", "pull-down/set", "series", "filter-cap", "bypass", "power-series"):
    print("\n==", kind)
    for r in sorted((r for r in rows if r["kind"] == kind), key=lambda r: r["ref"]):
        s = f'{r["ref"]:6} {r["value"][:10]:10} {r["side"]} ({r["x"]:6.1f},{r["y"]:6.1f})'
        for e in r["pads"]:
            nm = e["net"].split("/")[-1][:20]
            if e["pow"]:
                ph = ",".join(L.split(".")[0] for L in e["plane_here"]) if e["plane_here"] else "NONE→%.0fmm %s" % (e["plane_near"][0], (e["plane_near"][1] or "-").split(".")[0])
                s += f' | {nm}[{ph}]{"*" if e["routed"] else ""}'
                if e["net"] != "GND" and e["near"]: s += f' {e["near"][0][1]}@{e["near"][0][0]}'
            else:
                s += f' | {nm}{"*" if e["routed"] else ""} n={e["n_other"]}: ' + " ".join(f'{n[1]}{n[2]}@{n[0]}' for n in e["near"])
        print(s)
