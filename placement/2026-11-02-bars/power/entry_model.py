#!/usr/bin/env python3
"""Resistance of the 60 A power-entry path (VBAT_IN, VBAT_D, VBAT_Q2D) for a given set of copper
layers (D18 estimate, 2026-11-04). Finite-difference grid like plane_model.py: each segment is a
rectangle of copper with its source and sink pads held as equipotential cells; every layer present
in a cell adds its sheet conductance (layers assumed joined by enough vias: optimistic for the
inner layers). Pads of other nets are not cut out (optimistic too); use it to compare options.

    python3 entry_model.py [--layers B,In2,In3,F] [--temp 85] [--cell 0.5]
"""
import argparse

import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

OZ = {"B": 1.0, "F": 1.0, "In2": 2.0, "In3": 2.0}
F_BAND = (80.6, 89.6)          # F.Cu between the two busbar areas

SEGMENTS = {
    # name: (region x0, y0, x1, y1), source rectangles, sink rectangles
    "VBAT_IN  J910 ring -> Q201/Q202 sources": ((93.5, 72.5, 112.6, 107.5),
        [(95.5, 93.1, 108.5, 106.1)], [(109.35, 75.4, 111.85, 82.2), (109.35, 88.4, 111.85, 95.2)]),
    "VBAT_D   Q201/Q202 tabs -> R201 F1": ((113.4, 73.0, 133.6, 99.5),
        [(114.65, 74.95, 122.65, 85.05), (114.65, 87.95, 122.65, 98.05)], [(130.7, 84.55, 133.25, 90.15)]),
    "VBAT_Q2D R201 F2 -> Q203/Q204 tabs": ((138.4, 73.0, 158.0, 99.5),
        [(138.75, 84.55, 141.3, 90.15)], [(149.35, 74.95, 157.35, 85.05), (149.35, 87.95, 157.35, 98.05)]),
}


def solve(region, src, snk, layers, temp, h, f_x=None):
    x0, y0, x1, y1 = region
    nx, ny = int((x1 - x0) / h), int((y1 - y0) / h)
    rho = 1.72e-8 * (1 + 0.00393 * (temp - 20))
    g = np.zeros((nx, ny))
    for i in range(nx):
        for j in range(ny):
            y = y0 + (j + 0.5) * h
            for L in layers:
                if L == "F" and not (F_BAND[0] <= y <= F_BAND[1]):
                    continue
                g[i, j] += 35e-6 * OZ[L] / rho          # siemens per square
    inside = lambda r, i, j: r[0] <= x0 + (i + .5) * h <= r[2] and r[1] <= y0 + (j + .5) * h <= r[3]
    idx = -np.ones((nx, ny), int); n = 0
    for i in range(nx):
        for j in range(ny):
            if g[i, j] > 0: idx[i, j] = n; n += 1
    G = lil_matrix((n, n)); I = np.zeros(n)
    for i in range(nx):
        for j in range(ny):
            if idx[i, j] < 0: continue
            k = idx[i, j]
            for di, dj in ((1, 0), (0, 1)):
                ii, jj = i + di, j + dj
                if ii < nx and jj < ny and idx[ii, jj] >= 0:
                    c = 2 / (1 / g[i, j] + 1 / g[ii, jj]); m = idx[ii, jj]
                    G[k, k] += c; G[m, m] += c; G[k, m] -= c; G[m, k] -= c
    sinks = [idx[i, j] for i in range(nx) for j in range(ny) if idx[i, j] >= 0 and any(inside(r, i, j) for r in snk)]
    srcs = [idx[i, j] for i in range(nx) for j in range(ny) if idx[i, j] >= 0 and any(inside(r, i, j) for r in src)]
    for k in sinks:
        G[k, :] = 0; G[k, k] = 1; I[k] = 0
    for k in srcs:
        I[k] += 1.0 / len(srcs)
    V = spsolve(G.tocsr(), I)
    return float(np.mean([V[k] for k in srcs]))       # ohms for 1 A


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", default="B,In2,In3,F")
    ap.add_argument("--temp", type=float, default=85.0)
    ap.add_argument("--cell", type=float, default=0.5)
    a = ap.parse_args()
    layers = a.layers.split(",")
    tot = 0.0
    for name, (region, src, snk) in SEGMENTS.items():
        r = solve(region, src, snk, layers, a.temp, a.cell)
        tot += r
        print(f"  {name:40s} {r * 1e3:6.3f} mohm  {r * 3600:5.2f} W at 60 A")
    print(f"  {'60 A path, three segments':40s} {tot * 1e3:6.3f} mohm  {tot * 3600:5.2f} W at 60 A  (layers {a.layers}, {a.temp:g} C)")


if __name__ == "__main__":
    main()
