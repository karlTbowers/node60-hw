#!/usr/bin/env python3
"""Copy only the copper a router ADDED on some nets onto the real board (Node60 power joins, 2026-11-05).

    $KPY transplant_new.py ROUTED.kicad_pcb REAL.kicad_pcb OUT.kicad_pcb NET [NET ...] [--lock] [--json J]
        [--drop X0,Y0,X1,Y1 ...]

rmii/transplant_nets.py copies a net's whole copper, right for a net with none; a power net already
carries pours, vias and stubs, so this copies a track or via only when the real board has none at the
same place (same layer and ends, or same via position). The new items are grouped by touch into joins,
and each join is listed (net, length per layer, vias, box) so it can be reviewed one by one; a join whose
box centre falls in a --drop box is left out. Zones are refilled; DRC with the board's own rules judges.
"""
import json
import sys

import pcbnew


def key(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        return ("v", round(p.x / 1e3), round(p.y / 1e3))
    s, e = t.GetStart(), t.GetEnd()
    a, b = sorted([(round(s.x / 1e3), round(s.y / 1e3)), (round(e.x / 1e3), round(e.y / 1e3))])
    return ("t", t.GetLayer(), a, b)


def ends(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        return [(p.x, p.y)]
    return [(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)]


def main():
    argv = sys.argv[1:]
    lock = "--lock" in argv
    drops, jpath, args = [], None, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--drop":
            drops.append([float(v) for v in argv[i + 1].split(",")]); i += 2; continue
        if a == "--json":
            jpath = argv[i + 1]; i += 2; continue
        if not a.startswith("--"):
            args.append(a)
        i += 1
    src, dst = pcbnew.LoadBoard(args[0]), pcbnew.LoadBoard(args[1])
    nets = set(args[3:])
    have = {key(t) for t in dst.GetTracks()}
    # routers split a track where they join it: a piece lying along an existing track of the same net,
    # layer and width is not new
    segs = {}
    for t in dst.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T:
            segs.setdefault((t.GetNetname(), t.GetLayer(), t.GetWidth()), []).append(
                (t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y))

    def on(px, py, s):
        x0, y0, x1, y1 = s
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        u = 0 if L2 == 0 else max(0, min(1, ((px - x0) * dx + (py - y0) * dy) / L2))
        return (px - x0 - u * dx) ** 2 + (py - y0 - u * dy) ** 2 < 4e6     # 2 um

    def covered(t):
        if t.Type() != pcbnew.PCB_TRACE_T:
            return False
        for s in segs.get((t.GetNetname(), t.GetLayer(), t.GetWidth()), ()):
            if on(t.GetStart().x, t.GetStart().y, s) and on(t.GetEnd().x, t.GetEnd().y, s):
                return True
        return False
    new = [t for t in src.GetTracks() if t.GetNetname() in nets and key(t) not in have and not covered(t)]
    # group by shared end points (tracks meet at ends; a via joins what ends on it), per net
    parent = list(range(len(new)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    at = {}
    for i, t in enumerate(new):
        for p in ends(t):
            k = (t.GetNetname(), round(p[0] / 1e3), round(p[1] / 1e3))
            if k in at:
                parent[find(i)] = find(at[k])
            else:
                at[k] = i
    groups = {}
    for i in range(len(new)):
        groups.setdefault(find(i), []).append(new[i])
    rows, n, nv = [], 0, 0
    for g in groups.values():
        xs = [p[0] / 1e6 for t in g for p in ends(t)]; ys = [p[1] / 1e6 for t in g for p in ends(t)]
        box = [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        dropped = any(d[0] <= cx <= d[2] and d[1] <= cy <= d[3] for d in drops)
        per = {}
        vias = 0
        widths = set()
        for t in g:
            if t.Type() == pcbnew.PCB_VIA_T:
                vias += 1
            else:
                per[t.GetLayerName()] = per.get(t.GetLayerName(), 0) + t.GetLength() / 1e6
                widths.add(round(t.GetWidth() / 1e6, 3))
        rows.append({"net": g[0].GetNetname(), "box": box, "mm": {k: round(v, 2) for k, v in per.items()},
                     "vias": vias, "widths": sorted(widths), "dropped": dropped})
        if dropped:
            continue
        for t in g:
            net = dst.FindNet(t.GetNetname())
            if t.Type() == pcbnew.PCB_VIA_T:
                o = pcbnew.PCB_VIA(dst); o.SetPosition(t.GetPosition()); o.SetWidth(t.GetWidth()); o.SetDrill(t.GetDrill()); nv += 1
            else:
                o = pcbnew.PCB_TRACK(dst); o.SetStart(t.GetStart()); o.SetEnd(t.GetEnd())
                o.SetWidth(t.GetWidth()); o.SetLayer(t.GetLayer()); n += 1
            o.SetNet(net); o.SetLocked(lock); dst.Add(o)
    pcbnew.ZONE_FILLER(dst).Fill(dst.Zones())
    dst.Save(args[2])
    rows.sort(key=lambda r: (r["net"], r["box"]))
    for r in rows:
        L = sum(r["mm"].values())
        print(f"{'DROP ' if r['dropped'] else ''}{r['net']:30s} {L:6.1f} mm {r['vias']} vias {r['mm']} w{r['widths']} box {r['box']}")
    print(f"{n} tracks, {nv} vias in {sum(1 for r in rows if not r['dropped'])} joins onto {args[2]}")
    if jpath:
        json.dump(rows, open(jpath, "w"), indent=1)


if __name__ == "__main__":
    main()
