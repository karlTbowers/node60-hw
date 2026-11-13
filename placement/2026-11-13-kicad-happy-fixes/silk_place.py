#!/usr/bin/env python3
"""silk_place.py SILK.json OUT.json [RMAX] -- N4: a place for every reference designator (needs numpy and PIL).

Per board side a 0.05 mm bitmap of what a reference may not touch: solder-mask openings (pads) + 0.15 mm,
footprint silkscreen graphics + 0.15 mm, every courtyard (text under a part can't be read after assembly:
handbook chapter 05), a 0.5 mm margin inside the board edge, and the references placed so far + 0.15 mm.
Each reference takes the free spot (text flat or turned 90 degrees) with the lowest cost: gap from its own
courtyard, then distance from the part's centre. The parts with the fewest free spots go first. A reference with
no free spot within RMAX (default 6 mm) of its courtyard looks out to twice RMAX; with none there either it is
reported and left where it is."""
import json, sys, math
import numpy as np
from PIL import Image, ImageDraw
D = json.load(open(sys.argv[1])); RMAX = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
PX = 0.05; X0, Y0, X1, Y1 = D["edge"]; W, H = int((X1 - X0) / PX) + 1, int((Y1 - Y0) / PX) + 1
px = lambda x, y: ((x - X0) / PX, (y - Y0) / PX)
def grow(img, r):                       # dilate a bitmap by r mm (square element, good enough at these sizes)
    from scipy.ndimage import binary_dilation
    k = int(round(r / PX)); return binary_dilation(img, structure=np.ones((2 * k + 1, 2 * k + 1), bool)) if k else img
occ = {}
for side in "FB":
    hard = Image.new("1", (W, H), 0); dh = ImageDraw.Draw(hard); cy = Image.new("1", (W, H), 0); dc = ImageDraw.Draw(cy)
    for f in D["fps"]:
        for pl in f["pads"][side] + f["silk"][side]:
            if len(pl) >= 3: dh.polygon([px(*p) for p in pl], fill=1)
        if f["side"] == side:
            for pl in f["courtyard"]:
                if len(pl) >= 3: dc.polygon([px(*p) for p in pl], fill=1)
    o = grow(np.array(hard, bool), 0.15) | np.array(cy, bool)
    m = int(0.5 / PX); o[:m, :] = o[-m:, :] = True; o[:, :m] = o[:, -m:] = True
    occ[side] = o
def integral(o): return np.pad(o.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
def cands(f, I):
    global RMAX
    c = cands_(f, I)
    if c is None or not len(c[0]):          # no room near the part: look twice as far before giving up
        RMAX *= 2; c = cands_(f, I); RMAX /= 2
    return c
def cands_(f, I):
    """All free centre positions for f's text, both angles: (cost, x, y, angle)."""
    cps = [p for pl in f["courtyard"] for p in pl] or [p for pl in f["pads"][f["side"]] for p in pl] or [[f["x"], f["y"]]]
    cx0, cy0 = min(p[0] for p in cps), min(p[1] for p in cps); cx1, cy1 = max(p[0] for p in cps), max(p[1] for p in cps)
    best = []
    for ang, (tw, th) in ((0, (f["tw"], f["th"])), (90, (f["th"], f["tw"]))):
        hw, hh = int(math.ceil(tw / 2 / PX)), int(math.ceil(th / 2 / PX))
        ax0, ay0 = max(int((cx0 - RMAX - X0) / PX), hw + 1), max(int((cy0 - RMAX - Y0) / PX), hh + 1)
        ax1, ay1 = min(int((cx1 + RMAX - X0) / PX), W - hw - 2), min(int((cy1 + RMAX - Y0) / PX), H - hh - 2)
        if ax1 <= ax0 or ay1 <= ay0: continue
        ys, xs = np.mgrid[ay0:ay1:2, ax0:ax1:2]
        s = I[ys + hh + 1, xs + hw + 1] - I[ys - hh, xs + hw + 1] - I[ys + hh + 1, xs - hw] + I[ys - hh, xs - hw]
        free = s == 0
        if not free.any(): continue
        X, Y = xs[free] * PX + X0, ys[free] * PX + Y0
        gx = np.maximum(np.maximum(cx0 - (X + tw / 2), (X - tw / 2) - cx1), 0); gy = np.maximum(np.maximum(cy0 - (Y + th / 2), (Y - th / 2) - cy1), 0)
        gap = np.hypot(gx, gy); ok = gap <= RMAX
        cost = gap + 0.25 * np.hypot(X - f["x"], Y - f["y"]) + (0.3 if ang else 0)
        best.append((cost[ok], X[ok], Y[ok], np.full(ok.sum(), ang), gap[ok]))
    if not best: return None
    return [np.concatenate([b[i] for b in best]) for i in range(5)]
out, fail = {}, []
for side in "FB":
    fl = [f for f in D["fps"] if f["side"] == side and f["visible"]]
    I = integral(occ[side]); n = {}
    for f in fl:
        c = cands(f, I); n[f["ref"]] = 0 if c is None else len(c[0])
    for f in sorted(fl, key=lambda f: n[f["ref"]]):
        c = cands(f, I)
        if c is None or not len(c[0]): fail.append(f["ref"]); continue
        i = int(np.argmin(c[0])); x, y, ang = float(c[1][i]), float(c[2][i]), int(c[3][i])
        out[f["ref"]] = {"x": round(x, 3), "y": round(y, 3), "angle": ang, "gap": round(float(c[4][i]), 2)}
        tw, th = (f["tw"], f["th"]) if ang == 0 else (f["th"], f["tw"])
        a = [int((x - tw / 2 - 0.15 - X0) / PX), int((y - th / 2 - 0.15 - Y0) / PX), int((x + tw / 2 + 0.15 - X0) / PX) + 1, int((y + th / 2 + 0.15 - Y0) / PX) + 1]
        occ[side][a[1]:a[3], a[0]:a[2]] = True; I = integral(occ[side])
json.dump({"place": out, "no_room": sorted(fail)}, open(sys.argv[2], "w"), indent=1)
g = sorted(v["gap"] for v in out.values())
print(len(out), "placed; gap from own courtyard: median", g[len(g) // 2], "max", g[-1], "over 3 mm:", sum(v > 3 for v in g), "; no room:", len(fail), fail)
