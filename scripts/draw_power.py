#!/usr/bin/env python3
"""Draw a board's power shapes and power via fields from a spec (Node60, 2026-11-04).

Run with KiCad's Python from the repo root:

    $KPY scripts/draw_power.py node60.kicad_pcb SPEC.json [--no-fill] [--dry-run]
    git checkout -- node60.kicad_pro      # pcbnew's save rewrites it; check the diff first

The spec is the source; every run replaces what the previous run drew (zones named PWR_*, and
the locked vias of the spec's nets inside the spec's via regions), so edit the spec, not the
board. Signals are not touched.

SPEC.json:
{
  "via": {"size": 0.45, "drill": 0.25, "pitch": 0.9, "clearance": 0.15, "hole_clearance": 0.3},
  "zones": [{"name": "PWR_GND_In1", "net": "GND", "layers": ["In1.Cu"], "priority": 0,
             "rects": [[x0, y0, x1, y1], ...] | "board", "poly": [[x, y], ...],    # rects or one polygon
             "holes": [[x0, y0, x1, y1], ...]}],                                    # with "board" only
  "vias": [{"name": "VBAT_D corridor", "net": "/Power entry/VBAT_D",
            "rect": [x0, y0, x1, y1] | "annulus": [cx, cy, r0, r1],
            "toward": [[x, y], ...] (rank: nearest first), "min": 93, "max": 200,
            "clip": [x0, y0, x1, y1] (sites only inside: keep a via field within its own zone),
            "allow_under": ["REF", ...]}]
}

A via site is kept when, at the spec's via size: it is inside the board by the edge clearance; it
clears every pad on any copper layer by the clearance (including its own net's pads: no vias in
pads), and every drilled hole by the hole clearance; it is not inside the courtyard of any part
(either side) except those named in allow_under and the busbars; and it clears the sites already
placed. Zones are filled (ZONE_FILLER) unless --no-fill; everything drawn is locked (D12-7).
"""
import argparse
import json
import math
import sys

import pcbnew

F, M = pcbnew.FromMM, pcbnew.ToMM


def net(board, name):
    n = board.FindNet(name)
    if n is None:
        sys.exit(f"no net {name!r} on the board")
    return n


def board_rect(board):
    e = board.GetBoardEdgesBoundingBox()
    return M(e.GetLeft()), M(e.GetTop()), M(e.GetRight()), M(e.GetBottom())


def add_zone(board, z, outer):
    zone = pcbnew.ZONE(board)
    zone.SetZoneName(z["name"])
    zone.SetNet(net(board, z["net"]))
    ls = pcbnew.LSET()
    for L in z["layers"]:
        ls.AddLayer(board.GetLayerID(L))
    zone.SetLayerSet(ls)
    zone.SetAssignedPriority(int(z.get("priority", 0)))
    zone.SetMinThickness(F(z.get("min_width", 0.25)))
    zone.SetThermalReliefGap(F(0.3))
    zone.SetThermalReliefSpokeWidth(F(0.5))
    zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = zone.Outline()
    o.RemoveAllContours()
    if "poly" in z:
        o.NewOutline()
        for x, y in z["poly"]:
            o.Append(F(x), F(y))
    elif z.get("rects") == "board" and z.get("holes"):
        o.NewOutline()
        x0, y0, x1, y1 = outer
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            o.Append(F(x), F(y))
        for hx0, hy0, hx1, hy1 in z["holes"]:
            h = o.NewHole()
            for x, y in ((hx0, hy0), (hx1, hy0), (hx1, hy1), (hx0, hy1)):
                o.Append(F(x), F(y), 0, h)
    else:
        rects = [outer] if z["rects"] == "board" else z["rects"]
        for x0, y0, x1, y1 in rects:
            o.NewOutline()
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                o.Append(F(x), F(y))
    zone.SetLocked(True)
    board.Add(zone)
    return zone


def sites(v, pitch):
    if "rect" in v:
        x0, y0, x1, y1 = v["rect"]
        nx, ny = int((x1 - x0) / pitch) + 1, int((y1 - y0) / pitch) + 1
        ox, oy = x0 + (x1 - x0 - (nx - 1) * pitch) / 2, y0 + (y1 - y0 - (ny - 1) * pitch) / 2
        return [(ox + i * pitch, oy + j * pitch) for i in range(nx) for j in range(ny)]
    cx, cy, r0, r1 = v["annulus"]
    out, r = [], r0
    while r <= r1 + 1e-9:
        n = int(2 * math.pi * r / pitch)
        out += [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
        r += pitch
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board"); ap.add_argument("spec")
    ap.add_argument("--no-fill", action="store_true"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    spec = json.load(open(a.spec))
    V = spec.get("via", {})
    vsize, vdrill, pitch = V.get("size", 0.45), V.get("drill", 0.25), V.get("pitch", 0.9)
    clr, hclr = V.get("clearance", 0.15), V.get("hole_clearance", 0.3)
    board = pcbnew.LoadBoard(a.board)
    outer = board_rect(board)
    edge = board.GetDesignSettings().m_CopperEdgeClearance

    # replace what a previous run drew
    for z in list(board.Zones()):
        if not z.GetIsRuleArea() and z.GetZoneName().startswith("PWR_"):
            board.Delete(z)
    regions = [(v["net"], v) for v in spec.get("vias", [])]
    for t in list(board.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T and t.IsLocked():
            x, y = M(t.GetPosition().x), M(t.GetPosition().y)
            for n, v in regions:
                if t.GetNetname() != n:
                    continue
                inside = (v["rect"][0] - 0.01 <= x <= v["rect"][2] + 0.01 and v["rect"][1] - 0.01 <= y <= v["rect"][3] + 0.01) \
                    if "rect" in v else abs(math.hypot(x - v["annulus"][0], y - v["annulus"][1])) <= v["annulus"][3] + 0.01
                if inside:
                    board.Delete(t); break

    for z in spec.get("zones", []):
        add_zone(board, z, outer)
    print(f"{len(spec.get('zones', []))} zone(s)")

    # obstacles for via sites
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    bucket = {}
    for p in pads:
        bb = p.GetBoundingBox()
        for i in range(int(M(bb.GetLeft()) // 5), int(M(bb.GetRight()) // 5) + 1):
            for j in range(int(M(bb.GetTop()) // 5), int(M(bb.GetBottom()) // 5) + 1):
                bucket.setdefault((i, j), []).append(p)
    cyards = []
    for fp in board.GetFootprints():
        for L in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            c = fp.GetCourtyard(L)
            if c.OutlineCount():
                cyards.append((fp.GetReference(), c, c.BBox()))
    placed = [(M(t.GetPosition().x), M(t.GetPosition().y)) for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    r = vsize / 2
    total = 0
    short = []
    for v in spec.get("vias", []):
        allow = set(v.get("allow_under", [])) | {"BB901", "BB902"}
        cand = []
        clip = v.get("clip")
        for x, y in sites(v, pitch):
            if clip and not (clip[0] + r <= x <= clip[2] - r and clip[1] + r <= y <= clip[3] - r):
                continue
            if not (outer[0] + M(edge) + r <= x <= outer[2] - M(edge) - r and outer[1] + M(edge) + r <= y <= outer[3] - M(edge) - r):
                continue
            pt = pcbnew.VECTOR2I(F(x), F(y))
            bad = False
            for p in bucket.get((int(x // 5), int(y // 5)), []):
                if p.HitTest(pt, F(r + clr)):
                    bad = True; break
                if p.HasHole():
                    d = p.GetDrillSize()
                    if math.hypot(x - M(p.GetPosition().x), y - M(p.GetPosition().y)) < M(max(d.x, d.y)) / 2 + r + hclr:
                        bad = True; break
            if bad:
                continue
            for ref, c, bb in cyards:
                if ref in allow:
                    continue
                if M(bb.GetLeft()) - r <= x <= M(bb.GetRight()) + r and M(bb.GetTop()) - r <= y <= M(bb.GetBottom()) + r \
                        and c.Contains(pt, -1, F(r)):
                    bad = True; break
            if bad:
                continue
            cand.append((x, y))
        tow = v.get("toward")
        if tow:
            cand.sort(key=lambda s: min(math.hypot(s[0] - tx, s[1] - ty) for tx, ty in tow))
        keep = []
        for x, y in cand:
            if len(keep) >= v.get("max", 10 ** 6):
                break
            if any(math.hypot(x - px, y - py) < pitch - 1e-6 for px, py in placed + keep):
                continue
            keep.append((x, y))
        n = net(board, v["net"])
        for x, y in keep:
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(F(x), F(y)))
            via.SetWidth(F(vsize)); via.SetDrill(F(vdrill))
            via.SetNet(n); via.SetLocked(True)
            board.Add(via)
        placed += keep
        total += len(keep)
        flag = "" if len(keep) >= v.get("min", 0) else f"  BELOW the {v['min']} needed"
        if flag:
            short.append(v["name"])
        print(f"vias {v['name']:40s} {len(keep):4d} of {len(cand):4d} free sites (min {v.get('min', 0)}){flag}")
    print(f"{total} via(s)")
    if not a.no_fill:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        print("zones filled")
    if not a.dry_run:
        board.Save(a.board)
    if short:
        print("SHORT:", ", ".join(short))
        sys.exit(2)


if __name__ == "__main__":
    main()
