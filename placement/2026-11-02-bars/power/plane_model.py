#!/usr/bin/env python3
"""Resistance of Node60's power planes from each load to its source (finite-difference grid).

Reads power_geom.json (pads and holes from the board). Sheet resistance from copper weight
(1 oz = 35 um, rho_Cu = 1.72e-8 ohm m at 20 C, +0.393 %/K). Each pad set is one equipotential
node tied to the plane (as through a via farm); holes of other nets are removed with 0.3 mm
clearance. Prints, per load: resistance from the source alone and with every load on.
    python3 plane_model.py power_geom.json [--oz 1] [--temp 20] [--cell 0.5]
"""
import argparse, json, math
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

ap = argparse.ArgumentParser()
ap.add_argument('geom'); ap.add_argument('--oz', type=float, default=1.0)
ap.add_argument('--temp', type=float, default=20.0); ap.add_argument('--cell', type=float, default=0.5)
a = ap.parse_args()
g = json.load(open(a.geom))
x0, y0, x1, y1 = g['outline']; h = a.cell
nx, ny = int((x1 - x0) / h), int((y1 - y0) / h)
rho = 1.72e-8 * (1 + 0.00393 * (a.temp - 20)); t = 35e-6 * a.oz
Rs = rho / t                                   # ohm per square
print(f"sheet resistance {Rs*1e3:.3f} mohm/sq ({a.oz} oz, {a.temp} C), grid {nx} x {ny} at {h} mm")
cx = lambda i: x0 + (i + 0.5) * h; cy = lambda j: y0 + (j + 0.5) * h


def cells_in(box):
    bx0, by0, bx1, by1 = box
    return [(i, j) for i in range(max(0, int((bx0 - x0) / h)), min(nx, int((bx1 - x0) / h) + 1))
            for j in range(max(0, int((by0 - y0) / h)), min(ny, int((by1 - y0) / h) + 1))]


def solve(net, source, loads):
    """source: list of (ref, pins); loads: {name: ([(ref, pins)], amps)} -> {name: volts}"""
    ok = np.ones((nx, ny), bool)
    for hx, hy, d, hn in g['holes']:
        if hn == net: continue
        r = d / 2 + 0.3
        for i, j in cells_in((hx - r, hy - r, hx + r, hy + r)):
            if math.hypot(cx(i) - hx, cy(j) - hy) <= r: ok[i, j] = False
    def pads(spec):
        out = []
        for ref, pins in spec:
            for r_, num, bx0, by0, bx1, by1, side, hole in g['pads'][net]:
                if r_ == ref and (pins is None or num in pins):
                    out += [c for c in cells_in((bx0, by0, bx1, by1)) if ok[c]]
        return out
    idx = -np.ones((nx, ny), int); n = 0
    for i in range(nx):
        for j in range(ny):
            if ok[i, j]: idx[i, j] = n; n += 1
    src = set(pads(source))
    G = lil_matrix((n, n)); I = np.zeros(n)
    for i in range(nx):
        for j in range(ny):
            if not ok[i, j]: continue
            k = idx[i, j]
            for di, dj in ((1, 0), (0, 1)):
                ii, jj = i + di, j + dj
                if ii < nx and jj < ny and ok[ii, jj]:
                    m = idx[ii, jj]; c = 1 / Rs
                    G[k, k] += c; G[m, m] += c; G[k, m] -= c; G[m, k] -= c
    for c in src:                               # source pads held at 0 V
        k = idx[c]; G[k, :] = 0; G[k, k] = 1; I[k] = 0
    res = {}
    for name, (spec, amps) in loads.items():
        cl = pads(spec)
        for c in cl: I[idx[c]] += amps / len(cl)
        res[name] = cl
    V = spsolve(G.tocsr(), I)
    return {name: float(np.mean([V[idx[c]] for c in cl])) for name, cl in res.items()}


def report(title, net, source, loads):
    print(f"\n{title}")
    each = {}
    for name, (spec, amps) in loads.items():
        v = solve(net, source, {name: (spec, amps)})[name]
        each[name] = v / amps
    allv = solve(net, source, loads)
    for name, (spec, amps) in loads.items():
        print(f"  {name:28} alone {each[name]*1e3:6.3f} mohm   all on: {allv[name]*1e3:6.2f} mV at {amps:g} A "
              f"-> {allv[name]/amps*1e3:6.3f} mohm effective, {allv[name]*amps:5.2f} W share")
    return each, allv


# VBAT_PROT (In4): from Q203/Q204's drain pads to each switch's VBB pad (pin 17), 20 A per switch (2 x 10 A)
vb = {f"{u} VBB (2 x 10 A)": ([(u, ['17'])], 20.0) for u in ('U601', 'U701', 'U801')}
report("VBAT_PROT plane: Q203/Q204 drains -> switch VBB", 'VBAT_PROT', [('Q203', None), ('Q204', None)], vb)
# GND (In1): from each output header's pin 2 back to the GND terminals J911/J902 (joined by the busbar)
gl = {f"{j} GND pin (10 A)": ([(j, ['2'])], 10.0) for j in ('J904', 'J905', 'J906', 'J907', 'J908', 'J909')}
report("GND plane: header pin 2 -> J911/J902", 'GND', [('J911', None), ('J902', None)], gl)
