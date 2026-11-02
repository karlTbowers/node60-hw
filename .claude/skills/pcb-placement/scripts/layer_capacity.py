#!/usr/bin/env python3
"""Layer capacity at placement, read-only (pcb-placement skill). Run with KiCad's Python.

Before any copper: do the signal layers of the layer plan have room for the connections
this placement makes? Each net that is not a plane net is joined by its rectilinear
minimum spanning tree over its pads (the wiring humans approximate). Straight cut lines
every `--step` mm across the board, in both directions, are split into windows of
`--window` mm; a window's demand is the MST edges that must cross it (an edge spread
evenly over the span of its two pads along the cut), and its capacity is the tracks that
fit through it on every signal layer, less the length a rule area or keep-out takes from
a layer (Node60's busbar areas take F.Cu from every net but the bar's own).

    $KPY layer_capacity.py BOARD.kicad_pcb --signal-layers F.Cu,In2.Cu,In3.Cu,B.Cu \
        --plane-nets 'GND,VBAT_PROT' --track 0.1 --space 0.1 [--window 10 --step 2] [--json OUT]

Fill = demand / capacity. Over 60 % in a window is a WARN (routing gets hard and the
router detours), over 100 % an ERROR: the placement or the layer plan must change.
Exit 1 on any ERROR. The estimate ignores pads and vias in the way, so a WARN near a
fine-pitch part is worth a look even below 60 %.
"""
import argparse
import fnmatch
import json
import os
import re
import sys

import pcbnew


def mm(v):
    return pcbnew.ToMM(v)


def mst_edges(points):
    n = len(points)
    if n < 2:
        return []
    inside, best, parent = [False] * n, [float("inf")] * n, [-1] * n
    best[0] = 0
    edges = []
    for _ in range(n):
        u = min((i for i in range(n) if not inside[i]), key=lambda i: best[i])
        inside[u] = True
        if parent[u] >= 0:
            edges.append((points[parent[u]], points[u]))
        for v in range(n):
            if not inside[v]:
                d = abs(points[u][0] - points[v][0]) + abs(points[u][1] - points[v][1])
                if d < best[v]:
                    best[v], parent[v] = d, u
    return edges


def blocked_spans(board, rules_text):
    """(layer, bbox) for every area that keeps other nets' tracks off a layer."""
    spans = []
    text = "\n".join(l for l in rules_text.splitlines() if not l.lstrip().startswith("#"))
    starts = [m.start() for m in re.finditer(r"\(rule\b", text)] + [len(text)]
    dru = {}
    for rule in (text[s:e] for s, e in zip(starts, starts[1:])):
        dis = re.search(r"\(constraint disallow ([^)]*)\)", rule)
        if dis and "track" in dis.group(1).split():
            lay = re.search(r'\(layer "([^"]+)"\)', rule)
            for name in re.findall(r"intersectsArea\('([^']+)'\)", rule):
                dru.setdefault(name, []).append(lay.group(1) if lay else None)
    for z in board.Zones():
        if not z.GetIsRuleArea():
            continue
        bb = z.Outline().BBox()
        box = (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))
        layers = [board.GetStandardLayerName(l) for l in z.GetLayerSet().Seq()]
        if z.GetDoNotAllowTracks():
            spans += [(l, box, z.GetZoneName()) for l in layers]
        for l in dru.get(z.GetZoneName(), []):
            spans += [(x, box, z.GetZoneName()) for x in ([l] if l else layers)]
    return spans


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--signal-layers", required=True, help="comma-separated signal layers of the layer plan")
    ap.add_argument("--plane-nets", default="GND", help="comma-separated globs of nets served by planes")
    ap.add_argument("--track", type=float, default=0.2)
    ap.add_argument("--space", type=float, default=0.2)
    ap.add_argument("--window", type=float, default=10.0)
    ap.add_argument("--step", type=float, default=2.0)
    ap.add_argument("--rules", help="the board's .kicad_dru (default: sibling)")
    ap.add_argument("--top", type=int, default=8, help="windows to list")
    ap.add_argument("--json")
    a = ap.parse_args()

    board = pcbnew.LoadBoard(a.board)
    rules_path = a.rules or os.path.splitext(a.board)[0] + ".kicad_dru"
    rules_text = open(rules_path).read() if os.path.exists(rules_path) else ""
    layers = a.signal_layers.split(",")
    planes = [g.strip() for g in a.plane_nets.split(",") if g.strip()]
    pitch = a.track + a.space

    by_net = {}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            net = p.GetNetname()
            if not net or net.startswith("unconnected-"):
                continue
            if any(fnmatch.fnmatchcase(net, g) or fnmatch.fnmatchcase(net.lstrip("/"), g) for g in planes):
                continue
            by_net.setdefault(net, set()).add((round(mm(p.GetPosition().x), 3), round(mm(p.GetPosition().y), 3)))
    edges = [(net, e) for net, pts in by_net.items() for e in mst_edges(sorted(pts))]

    ebb = board.GetBoardEdgesBoundingBox()
    x0, y0, x1, y1 = mm(ebb.GetLeft()), mm(ebb.GetTop()), mm(ebb.GetRight()), mm(ebb.GetBottom())
    spans = [s for s in blocked_spans(board, rules_text) if s[0] in layers]

    def window_rows(vertical):
        lo, hi = (x0, x1) if vertical else (y0, y1)
        alo, ahi = (y0, y1) if vertical else (x0, x1)
        rows = []
        c = lo + a.step
        while c < hi - a.step / 2:
            w = alo
            while w < ahi - 1e-6:
                we = min(w + a.window, ahi)
                demand = 0.0
                nets = set()
                for net, (p, q) in edges:
                    pc, qc = (p[0], q[0]) if vertical else (p[1], q[1])
                    pa, qa = (p[1], q[1]) if vertical else (p[0], q[0])
                    if not (min(pc, qc) < c < max(pc, qc)):
                        continue
                    s0, s1 = min(pa, qa), max(pa, qa)
                    if s1 - s0 < 1e-6:
                        share = 1.0 if w <= s0 < we else 0.0
                    else:
                        share = max(0.0, min(s1, we) - max(s0, w)) / (s1 - s0)
                    if share:
                        demand += share
                        nets.add(net)
                cap = 0.0
                for layer in layers:
                    free = we - w
                    for l, (bx0, by0, bx1, by1), _ in spans:
                        if l != layer:
                            continue
                        crosses = (bx0 < c < bx1) if vertical else (by0 < c < by1)
                        if crosses:
                            b0, b1 = (by0, by1) if vertical else (bx0, bx1)
                            free -= max(0.0, min(b1, we) - max(b0, w))
                    cap += max(0.0, free) / pitch
                rows.append({"cut": f"{'x' if vertical else 'y'} = {c:.1f}",
                             "window": f"{'y' if vertical else 'x'} {w:.1f}..{we:.1f}",
                             "demand": round(demand, 1), "capacity": round(cap, 1),
                             "fill": round(demand / cap, 3) if cap else (float("inf") if demand else 0.0),
                             "nets": sorted(nets)[:12]})
                w = we
            c += a.step
        return rows

    rows = window_rows(True) + window_rows(False)
    rows.sort(key=lambda r: -r["fill"])
    worst = rows[: a.top]
    print(f"{len(by_net)} routed nets, {len(edges)} MST connections; signal layers {', '.join(layers)};"
          f" {pitch:.2f} mm track pitch; {len(spans)} blocked layer span(s)")
    for name in sorted({s[2] for s in spans}):
        print(f"  blocked: {name} on {', '.join(sorted({s[0] for s in spans if s[2] == name}))}")
    print(f"{'cut':12} {'window':16} {'demand':>7} {'capacity':>8} {'fill':>6}")
    for r in worst:
        print(f"{r['cut']:12} {r['window']:16} {r['demand']:7.1f} {r['capacity']:8.1f} {r['fill'] * 100:5.0f}%")
    errors = [r for r in rows if r["fill"] > 1.0]
    warns = [r for r in rows if 0.6 < r["fill"] <= 1.0]
    print(f"{len(errors)} window(s) over 100 % (ERROR), {len(warns)} over 60 % (WARN)")
    if a.json:
        json.dump({"layers": layers, "pitch_mm": pitch, "worst": worst, "errors": len(errors), "warns": len(warns)},
                  open(a.json, "w"), indent=2)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
