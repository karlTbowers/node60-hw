#!/usr/bin/env python3
"""Resistance of one net's copper between two sets of pads, measured from the board's filled zones,
its pads and its vias (D12-7's last step: the outputs' DCR from the copper; 2026-11-04).

Run with KiCad's Python (needs numpy and scipy; it imports them from the KRT environment if KiCad's
Python lacks them):

    $KPY copper_r.py BOARD NET FROM_REF:PADS TO_REF:PADS [--layers F.Cu,B.Cu] [--cell 0.2] [--temp 85]

e.g. copper_r.py node60.kicad_pcb /OUT1 U601:6,7,8 J904:1

Each layer's copper of the net (filled zone polygons and pads on that layer) is rasterised on a grid
of --cell mm; neighbouring cells join through the sheet resistance of that layer's copper (from the
board's stackup), and a via joins the cells under it on each layer it reaches through its barrel
(18 um plating, as JLCPCB plates). The FROM pads are held at one potential and 1 A is drawn at the
TO pads; the result is the mean potential difference. Tracks are ignored (none on the power nets).
"""
import argparse
import math
import sys

import pcbnew

try:
    import numpy as np
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import spsolve
except ImportError:
    import glob, os
    sys.path += glob.glob(os.path.expanduser("~/.cache/dropout/krt-venv/lib/python3*/site-packages"))
    import numpy as np
    from scipy.sparse import lil_matrix
    from scipy.sparse.linalg import spsolve

F, M = pcbnew.FromMM, pcbnew.ToMM
RHO20 = 1.72e-8


def copper_thickness(path):
    """{layer name: metres}: the copper layers' thickness from the board file's stackup"""
    import re
    s = open(path).read()
    st = s[s.index("(stackup"):]
    out = {}
    for m in re.finditer(r'\(layer "([^"]+)"\s*\(type "copper"\)\s*\(thickness ([\d.]+)\)', st):
        out.setdefault(m.group(1), float(m.group(2)) / 1e3)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board"); ap.add_argument("net"); ap.add_argument("src"); ap.add_argument("snk")
    ap.add_argument("--layers", default="F.Cu,B.Cu"); ap.add_argument("--cell", type=float, default=0.2)
    ap.add_argument("--temp", type=float, default=85.0)
    a = ap.parse_args()
    b = pcbnew.LoadBoard(a.board)
    layers = a.layers.split(",")
    lid = {L: b.GetLayerID(L) for L in layers}
    tk = copper_thickness(a.board)
    tk = {L: tk.get(L, tk.get(b.GetLayerName(lid[L]), 35e-6)) for L in layers}
    rho = RHO20 * (1 + 0.00393 * (a.temp - 20))
    netcode = b.FindNet(a.net).GetNetCode()

    def pads(spec):
        ref, nums = spec.split(":")
        nums = nums.split(",")
        fp = b.FindFootprintByReference(ref)
        return [p for p in fp.Pads() if p.GetNumber() in nums]
    src, snk = pads(a.src), pads(a.snk)

    # copper of the net per layer: filled zone polygons and pads
    polys = {L: [] for L in layers}
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetCode() != netcode:
            continue
        for L in layers:
            if z.IsOnLayer(lid[L]) and z.GetFilledPolysList(lid[L]):
                polys[L].append(z.GetFilledPolysList(lid[L]))
    npads = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetCode() == netcode]
    vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetCode() == netcode]
    # grid over everything of the net
    boxes = [ps.BBox() for L in layers for ps in polys[L]] + [p.GetBoundingBox() for p in npads]
    x0, y0 = min(M(r.GetLeft()) for r in boxes), min(M(r.GetTop()) for r in boxes)
    x1, y1 = max(M(r.GetRight()) for r in boxes), max(M(r.GetBottom()) for r in boxes)
    h = a.cell
    nx, ny = int((x1 - x0) / h) + 1, int((y1 - y0) / h) + 1
    idx = {}
    for li, L in enumerate(layers):
        for i in range(nx):
            for j in range(ny):
                pt = pcbnew.VECTOR2I(F(x0 + (i + .5) * h), F(y0 + (j + .5) * h))
                on = any(ps.Contains(pt) for ps in polys[L]) or any(p.IsOnLayer(lid[L]) and p.HitTest(pt) for p in npads
                                                                     if abs(M(p.GetPosition().x) - M(pt.x)) < 8 and abs(M(p.GetPosition().y) - M(pt.y)) < 8)
                if on:
                    idx[(li, i, j)] = len(idx)
    n = len(idx)
    G = lil_matrix((n, n)); I = np.zeros(n)

    def link(k, m, g):
        G[k, k] += g; G[m, m] += g; G[k, m] -= g; G[m, k] -= g
    for (li, i, j), k in idx.items():
        g = tk[layers[li]] / rho                   # siemens per square
        for di, dj in ((1, 0), (0, 1)):
            m = idx.get((li, i + di, j + dj))
            if m is not None:
                link(k, m, g)
    gvia = (math.pi * 0.25e-3 * 18e-6) / (rho * 2.0e-3)   # one 0.25 mm barrel over the board's 2.0 mm
    nv = 0
    for v in vias:
        i, j = int((M(v.GetPosition().x) - x0) / h), int((M(v.GetPosition().y) - y0) / h)
        ks = [idx.get((li, i, j)) for li in range(len(layers))]
        ks = [k for k in ks if k is not None]
        for k, m in zip(ks, ks[1:]):
            link(k, m, gvia * (len(layers) - 1))
        nv += len(ks) > 1
    # THT pads join their layers directly
    for p in npads:
        if p.HasHole():
            i, j = int((M(p.GetPosition().x) - x0) / h), int((M(p.GetPosition().y) - y0) / h)
            ks = [idx.get((li, i, j)) for li in range(len(layers))]
            ks = [k for k in ks if k is not None]
            for k, m in zip(ks, ks[1:]):
                link(k, m, 1e3)

    def cells(ps):
        out = set()
        for p in ps:
            for (li, i, j), k in idx.items():
                if p.IsOnLayer(lid[layers[li]]) and p.HitTest(pcbnew.VECTOR2I(F(x0 + (i + .5) * h), F(y0 + (j + .5) * h))):
                    out.add(k)
        return sorted(out)
    cs, ck = cells(src), cells(snk)
    if not cs or not ck:
        sys.exit(f"pads not on the copper grid: {len(cs)} source cells, {len(ck)} sink cells; grid x {x0:.1f}..{x1:.1f} y {y0:.1f}..{y1:.1f}")
    for k in cs:                                   # source held at 0 V
        G[k, :] = 0; G[k, k] = 1; I[k] = 0
    for k in ck:
        I[k] -= 1.0 / len(ck)
    V = spsolve(G.tocsr(), I)
    R = -float(np.mean([V[k] for k in ck]))
    print(f"{a.net:8s} {a.src:>14s} -> {a.snk:<8s} {R * 1e3:6.3f} mohm  {R * 100:5.2f} W at 10 A  "
          f"({nv} vias joining layers, {len(idx)} cells, {a.temp:g} C)")


if __name__ == "__main__":
    main()
