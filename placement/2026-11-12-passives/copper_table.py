"""Copper each attempt board carries against main, from the board dumps (data/*.json).
3V3_MAIN is the rail every moved pull-up hangs on: its tracks, and how much of them lies in the power
band (y > 71 mm, where no layer carries 3V3 except the In3 margins), and its vias."""
import json, math, sys, glob, os
def stats(p):
    d = json.load(open(p))
    L = lambda t: math.hypot(t["x2"] - t["x1"], t["y2"] - t["y1"])
    t3 = [t for t in d["tracks"] if t["net"] == "3V3_MAIN"]
    band = lambda t: min(t["y1"], t["y2"]) > 71
    v3 = [v for v in d["vias"] if v["net"] == "3V3_MAIN"]
    return {"tracks_mm": sum(L(t) for t in d["tracks"]), "vias": len(d["vias"]),
            "3v3_mm": sum(L(t) for t in t3), "3v3_band_mm": sum(L(t) for t in t3 if band(t)),
            "3v3_F_mm": sum(L(t) for t in t3 if t["layer"] == "F.Cu"),
            "3v3_vias": len(v3), "3v3_band_vias": sum(1 for v in v3 if v["y"] > 71)}
base = stats("data/00-main.json"); out = {"00-main": base}
print(f"{'board':24} {'tracks mm':>10} {'vias':>6} {'3V3 mm':>8} {'3V3 in band':>12} {'3V3 on F':>9} {'3V3 vias':>9} {'in band':>8}")
for p in sorted(glob.glob("data/[01][0-9]*-*.json")):
    n = os.path.basename(p)[:-5]; s = stats(p); out[n] = s
    f = lambda k, w: (f"{s[k]:{w}.1f}" if n == "00-main" else f"{s[k]:{w}.1f}") 
    d = lambda k: "" if n == "00-main" else f" ({s[k] - base[k]:+.0f})"
    print(f"{n:24} {s['tracks_mm']:>10.1f} {s['vias']:>6} {s['3v3_mm']:>8.1f} {s['3v3_band_mm']:>7.1f}{d('3v3_band_mm'):>6} {s['3v3_F_mm']:>9.1f} {s['3v3_vias']:>5}{d('3v3_vias'):>5} {s['3v3_band_vias']:>4}{d('3v3_band_vias'):>5}")
json.dump(out, open("data/copper_table.json", "w"), indent=1)
