"""Counts from a kicad-cli DRC JSON report; with a second report, what is new against it."""
import json, sys, collections
def load(p):
    d = json.load(open(p))
    c = collections.Counter((v["severity"], v["type"]) for v in d.get("violations", []))
    return d, c, len(d.get("unconnected_items", []))
d, c, u = load(sys.argv[1])
err = sum(n for (s, t), n in c.items() if s == "error")
print(f"errors {err}  warnings {sum(c.values()) - err}  unconnected {u}")
print("  errors:", {t: n for (s, t), n in sorted(c.items()) if s == "error"})
if len(sys.argv) > 2:
    d0, c0, u0 = load(sys.argv[2])
    diff = {f"{s}:{t}": n - c0.get((s, t), 0) for (s, t), n in c.items() if n != c0.get((s, t), 0)}
    diff.update({f"{s}:{t}": -n for (s, t), n in c0.items() if (s, t) not in c})
    print(f"  against base: unconnected {u - u0:+d}; changed counts {diff}")
    key = lambda v: (v["type"], v["description"], tuple(sorted((round(i["pos"]["x"], 2), round(i["pos"]["y"], 2)) for i in v.get("items", []))))
    old = {key(v) for v in d0.get("violations", [])}
    for v in d.get("violations", []):
        if key(v) not in old and v["severity"] == "error":
            print("   NEW", v["type"], "|", v["description"][:90], "|", "; ".join(i["description"][:70] for i in v.get("items", [])), "@", [(round(i["pos"]["x"], 2), round(i["pos"]["y"], 2)) for i in v.get("items", [])][:1])
