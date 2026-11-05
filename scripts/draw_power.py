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
  "zones": [{"name": "PWR_GND_In1", "net": "GND", "layers": ["In1.Cu"], "priority": 0, "solid": false,
             "rects": [[x0, y0, x1, y1], ...] | "board", "poly": [[x, y], ...],    # rects or one polygon
             "holes": [[x0, y0, x1, y1], ...]}],                                    # with "board" only
  "vias": [{"name": "VBAT_D corridor", "net": "/Power entry/VBAT_D",
            "rect": [x0, y0, x1, y1] | "annulus": [cx, cy, r0, r1] | "edge": {"outline": [x0, y0, x1, y1], "inset": 1.0}
            (sites every pitch along the outline, inset), "avoid": [[x0, y0, x1, y1], ...],
            "toward": [[x, y], ...] (rank: nearest first), "min": 93, "max": 200,
            "clip": [x0, y0, x1, y1] (sites only inside: keep a via field within its own zone),
            "pitch": 0.65 (the field's own), "in_pad": ["U601", "17"] (vias inside that pad, filled and
            capped: DEC-027), "mirror": {"net": "/OUT2", "axis_x": 77.65} (the same sites mirrored about
            x = axis_x on another net; a site is kept only if both are free: identical outputs),
            "copies": [{"dx": 0, "net": "/OUT1", "mirror_net": "/OUT2", "axis_x": 77.65}, ...] (the field
            repeated at each dx, with its mirror; a site is kept only if free at every copy),
            "allow_under": ["REF", ...], "same_net_pads_ok": true (a site may sit in a pad of its own net,
            e.g. a B pad under an F pad of the same net)}]
}

Also "keep_clear" ([{"name", "rect": [x0, y0, x1, y1]}]: no via of any field in these rects, e.g. the T1S
trunk's corridor on F.Cu, which every via passes), "class_clearance" ({"T1S_100R": 0.75}: a via site keeps
this far from routed tracks and vias of that net class), "pad_vias" (one via per pad of a net), "dogbones" (a BGA's balls, "prefer": {ball: [dx, dy]}),
"points" ({"name", "points": [[x, y, net], ...]}: vias at given points), "clear" ([{"net", "rect"}]: a retired field's locked vias and tracks to remove), "via_overrides" ([{"rect",
"size", "drill"}]: any via drawn inside rect takes that size) and "stubs" ({"name", "layer",
"width", "stubs": [[x1, y1, x2, y2, net], ...]}); see place_pad_vias and place_dogbones.

A via site is kept when, at the spec's via size: it is inside the board by the edge clearance; it
clears every pad on any copper layer by the clearance (including its own net's pads: no vias in
pads, except an in_pad field's own pad), and every drilled hole by the hole clearance; it is not inside the courtyard of any part
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
    if z.get("solid"):                                  # small parts' pads too narrow for 0.5 mm spokes
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
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
    if "edge" in v:                                      # a ring inset from the board's rectangular outline
        x0, y0, x1, y1 = v["edge"]["outline"]
        d = v["edge"]["inset"]
        x0, y0, x1, y1 = x0 + d, y0 + d, x1 - d, y1 - d
        out = []
        for (ax, ay), (bx, by) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            n = max(1, int(round(math.hypot(bx - ax, by - ay) / pitch)))
            out += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n)]
        return out
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


def pad_layer(p):
    """the copper layer an SMD pad is on (GetPrincipalLayer says F.Cu for a flipped part's pads)"""
    return pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) and not p.IsOnLayer(pcbnew.F_Cu) else pcbnew.F_Cu


VIA_OVERRIDES = []     # [{"rect": [x0, y0, x1, y1], "size", "drill"}]: smaller vias where the spec asks


def add_via(board, x, y, netname, size, drill):
    for o in VIA_OVERRIDES:
        r_ = o["rect"]
        if r_[0] <= x <= r_[2] and r_[1] <= y <= r_[3]:
            size, drill = o["size"], o["drill"]
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(F(x), F(y)))
    via.SetWidth(F(size)); via.SetDrill(F(drill))
    via.SetNet(net(board, netname)); via.SetLocked(True)
    board.Add(via)


def add_stub(board, a, b_, layer, width, netname):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(F(a[0]), F(a[1]))); t.SetEnd(pcbnew.VECTOR2I(F(b_[0]), F(b_[1])))
    t.SetWidth(F(width)); t.SetLayer(layer)
    t.SetNet(net(board, netname)); t.SetLocked(True)
    board.Add(t)


def seg_clear(board, a, b_, layer, width, netname, clr, skip):
    """a stub from a to b on layer clears every other-net pad, track and via by clr"""
    seg = pcbnew.SHAPE_SEGMENT(pcbnew.VECTOR2I(F(a[0]), F(a[1])), pcbnew.VECTOR2I(F(b_[0]), F(b_[1])), F(width))
    for fp in board.GetFootprints():
        q = fp.GetPosition()
        if abs(M(q.x) - a[0]) > 20 or abs(M(q.y) - a[1]) > 20:
            continue
        for p in fp.Pads():
            if any(p is s for s in skip) or p.GetNetname() == netname or not p.IsOnLayer(layer):
                continue
            if p.GetEffectiveShape(layer).Collide(seg, F(clr)):
                return False
    for t in board.GetTracks():
        if t.GetNetname() == netname or abs(M(t.GetPosition().x) - a[0]) > 5 or abs(M(t.GetPosition().y) - a[1]) > 5:
            continue
        if t.Type() == pcbnew.PCB_VIA_T or t.IsOnLayer(layer):
            if t.GetEffectiveShape(layer).Collide(seg, F(clr)):
                return False
    return True


def place_pad_vias(board, v, free, placed, vsize, vdrill, clr):
    """{"name", "net", "rect": [x0, y0, x1, y1] (pads whose centre is inside), "except": [REF, ...],
        "except_rects": [[x0, y0, x1, y1], ...], "size", "drill", "reach" (mm beyond the pad edge for a
        stub via), "stub" (track width),
        "gnd": true (also the GND pad of each two-pad part given a via)}
    Each pad gets one via: in the pad when the pad holds the whole ring with 0.05 mm to spare (filled
    and capped, DEC-027), else on rings outward from its edge, nearest first, with a stub track."""
    size, drill = v.get("size", vsize), v.get("drill", vdrill)
    r = size / 2
    rect, exc = v.get("rect"), set(v.get("except", []))
    jobs = []
    for fp in board.GetFootprints():
        if fp.GetReference() in exc:
            continue
        for p in fp.Pads():
            if p.GetNetname() != v["net"] or p.HasHole():
                continue
            x, y = M(p.GetPosition().x), M(p.GetPosition().y)
            if rect and not (rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]):
                continue
            if any(e[0] <= x <= e[2] and e[1] <= y <= e[3] for e in v.get("except_rects", [])):
                continue
            jobs.append(p)
            if v.get("gnd") and len(fp.Pads()) == 2:
                other = [q for q in fp.Pads() if q is not p][0]
                if other.GetNetname() == "GND":
                    jobs.append(other)
    n_place = n_stub = 0
    missing = []
    for p in jobs:
        fp = p.GetParentFootprint()
        ref, num, netname = fp.GetReference(), p.GetNumber(), p.GetNetname()
        layer = pad_layer(p)
        x, y = M(p.GetPosition().x), M(p.GetPosition().y)
        sz = p.GetSize()
        w_min = min(M(sz.x), M(sz.y))
        apart = lambda sx, sy: all(math.hypot(sx - px, sy - py) >= size + 0.2 for px, py in placed)
        if w_min >= size + 0.1 and apart(x, y) and free(x, y, {ref}, (ref, num), netname):
            add_via(board, x, y, netname, size, drill); placed.append((x, y)); n_place += 1
            continue
        bb = p.GetBoundingBox()
        half = max(M(bb.GetWidth()), M(bb.GetHeight())) / 2
        best = None
        d = min(M(bb.GetWidth()), M(bb.GetHeight())) / 2 + clr + r
        while d <= half + v.get("reach", 1.5) + r and best is None:
            for k in range(24):
                ang = 2 * math.pi * k / 24
                sx, sy = x + d * math.cos(ang), y + d * math.sin(ang)
                if not apart(sx, sy) or not free(sx, sy, {ref}, None, netname):
                    continue
                if not seg_clear(board, (x, y), (sx, sy), layer, v.get("stub", 0.3), netname, clr, [p]):
                    continue
                best = (sx, sy); break
            d += 0.1
        if best is None:
            missing.append(f"{ref}.{num}")
            continue
        add_via(board, best[0], best[1], netname, size, drill)
        add_stub(board, (x, y), best, layer, v.get("stub", 0.3), netname)
        placed.append(best); n_place += 1; n_stub += 1
    return n_place, n_stub, missing


def place_dogbones(board, v, placed):
    """{"name", "ref": "U401", "nets": [...], "size", "drill", "track", "pitch"}: each ball of those nets
    gets a via at one of its four diagonal cell centres, the one pointing away from the BGA's centre
    first (the usual quadrant fan-out), with a short track; a cell already holding a via is skipped"""
    fp = board.FindFootprintByReference(v["ref"])
    size, drill, w = v["size"], v["drill"], v.get("track", 0.2)
    balls = [p for p in fp.Pads() if p.GetNetname() in v["nets"]]
    xs = [M(p.GetPosition().x) for p in fp.Pads()]; ys = [M(p.GetPosition().y) for p in fp.Pads()]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    off = v.get("pitch", 0.8) / 2
    clr, hclr = v.get("clearance", 0.1), v.get("hole_clearance", 0.2)     # ESCAPE_U401's 0.1 mm; board hole clearance
    near = [q for f2 in board.GetFootprints() for q in f2.Pads()
            if abs(M(q.GetPosition().x) - M(fp.GetPosition().x)) < 12 and abs(M(q.GetPosition().y) - M(fp.GetPosition().y)) < 12]

    def site_ok(vx, vy, netname):
        """clear of every other-net pad on either side (copper and hole clearance); a same-net pad over
        the via is welcome (a decap on its own via)"""
        pt = pcbnew.VECTOR2I(F(vx), F(vy))
        for q in near:
            if q.GetNetname() == netname:
                continue
            if q.HitTest(pt, F(size / 2 + clr)) or q.HitTest(pt, F(drill / 2 + hclr)):
                return False
        return True
    n, missing = 0, []
    for p in sorted(balls, key=lambda q: -math.hypot(M(q.GetPosition().x) - cx, M(q.GetPosition().y) - cy)):
        x, y = M(p.GetPosition().x), M(p.GetPosition().y)
        sx_ = 1 if x > cx + 1e-3 else -1 if x < cx - 1e-3 else 0
        sy_ = 1 if y > cy + 1e-3 else -1 if y < cy - 1e-3 else 0
        order = [(a_, b_) for a_ in ((sx_, -sx_) if sx_ else (1, -1)) for b_ in ((sy_, -sy_) if sy_ else (1, -1))]
        if p.GetNumber() in v.get("skip", []):               # joined another way (a stub to a neighbour)
            continue
        pref = v.get("prefer", {}).get(p.GetNumber())        # a ball's cell by hand: [dx, dy] in (-1, 1)
        if pref:
            order = [tuple(pref)] + [o for o in order if o != tuple(pref)]
        if v.get("strict") and "prefer" in v:               # the planned cell or none
            order = [tuple(pref)] if pref else []
        for dx, dy in order:
            vx, vy = x + dx * off, y + dy * off
            if any(math.hypot(vx - px, vy - py) < size + 0.15 for px, py in placed):
                continue
            if not site_ok(vx, vy, p.GetNetname()):
                continue
            add_via(board, vx, vy, p.GetNetname(), size, drill)
            add_stub(board, (x, y), (vx, vy), pad_layer(p), w, p.GetNetname())
            placed.append((vx, vy)); n += 1
            break
        else:
            missing.append(p.GetNumber())
    return n, missing


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
    VIA_OVERRIDES[:] = spec.get("via_overrides", [])
    outer = board_rect(board)
    edge = board.GetDesignSettings().m_CopperEdgeClearance

    # replace what a previous run drew
    for z in list(board.Zones()):
        if not z.GetIsRuleArea() and z.GetZoneName().startswith("PWR_"):
            board.Delete(z)
    def region(v):
        """(rect or None, annulus or None) a via field covers, for removing a previous run's vias"""
        if "in_pad" in v:
            pad = next(p for fp in board.GetFootprints() if fp.GetReference() == v["in_pad"][0] for p in fp.Pads()
                       if p.GetNumber() == v["in_pad"][1])
            bb = pad.GetBoundingBox()
            return [M(bb.GetLeft()), M(bb.GetTop()), M(bb.GetRight()), M(bb.GetBottom())], None
        if "edge" in v:
            return None, None
        return v.get("rect"), v.get("annulus")

    regions = []
    for v in spec.get("vias", []):
        rect, ann = region(v)
        regions.append((v["net"], rect, ann))
        if "mirror" in v and rect:
            ax = v["mirror"]["axis_x"]
            regions.append((v["mirror"]["net"], [2 * ax - rect[2], rect[1], 2 * ax - rect[0], rect[3]], None))
        # every copy's region too (and its mirror): until 2026-11-04 only the first copy was cleared,
        # so each rerun stacked another set of vias on the other copies (OUT2-OUT6 reached 198 each)
        for c in (v.get("copies", []) if rect else []):
            dx = c["dx"]
            regions.append((c["net"], [rect[0] + dx, rect[1], rect[2] + dx, rect[3]], None))
            if "mirror_net" in c:
                ax = c["axis_x"]
                regions.append((c["mirror_net"], [2 * ax - (rect[2] + dx), rect[1], 2 * ax - (rect[0] + dx), rect[3]], None))
    edge_bands = [(v["net"], v["edge"]) for v in spec.get("vias", []) if "edge" in v]
    for t in list(board.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T and t.IsLocked():
            x, y = M(t.GetPosition().x), M(t.GetPosition().y)
            gone = False
            for n, e in edge_bands:                       # an edge ring's previous vias: within its inset band
                ox0, oy0, ox1, oy1 = e["outline"]
                if t.GetNetname() == n and min(x - ox0, ox1 - x, y - oy0, oy1 - y) <= e["inset"] + 0.3:
                    board.Delete(t); gone = True; break
            if gone:
                continue
            for n, rect, ann in regions:
                if t.GetNetname() != n or rect is None and ann is None:
                    continue
                inside = (rect[0] - 0.01 <= x <= rect[2] + 0.01 and rect[1] - 0.01 <= y <= rect[3] + 0.01) if rect \
                    else math.hypot(x - ann[0], y - ann[1]) <= ann[3] + 0.01
                if inside:
                    board.Delete(t); break
    # pad vias and dogbones: a previous run's locked vias and stub tracks of those nets (inside the
    # field's rect, or the BGA's outline for dogbones) go; unlocked copper (hand routing) stays
    sweeps = [(v["net"], v.get("rect") or [-1e9, -1e9, 1e9, 1e9]) for v in spec.get("pad_vias", [])]
    # retired fields: their locked vias and tracks go too ("clear": [{"net", "rect"}])
    for c in spec.get("clear", []):
        for t in list(board.GetTracks()):
            if t.IsLocked() and t.GetNetname() == c["net"]:
                x, y = M(t.GetPosition().x), M(t.GetPosition().y)
                r_ = c["rect"]
                if r_[0] <= x <= r_[2] and r_[1] <= y <= r_[3]:
                    board.Delete(t)
    for v in spec.get("points", []) + spec.get("stubs", []):
        for q in v.get("points", []) + v.get("stubs", []):
            sweeps.append((q[-1], [q[0] - 0.05, q[1] - 0.05, q[0] + 0.05, q[1] + 0.05]))
    for v in spec.get("dogbones", []):
        bb = board.FindFootprintByReference(v["ref"]).GetBoundingBox(False)
        for n_ in v["nets"]:
            sweeps.append((n_, [M(bb.GetLeft()), M(bb.GetTop()), M(bb.GetRight()), M(bb.GetBottom())]))
    for t in list(board.GetTracks()):
        if not t.IsLocked():
            continue
        x, y = M(t.GetPosition().x if t.Type() == pcbnew.PCB_VIA_T else t.GetEnd().x), \
            M(t.GetPosition().y if t.Type() == pcbnew.PCB_VIA_T else t.GetEnd().y)
        for n_, r_ in sweeps:
            if t.GetNetname() == n_ and r_[0] - 2 <= x <= r_[2] + 2 and r_[1] - 2 <= y <= r_[3] + 2:
                board.Delete(t); break

    for z in spec.get("zones", []):
        add_zone(board, z, outer)
    print(f"{len(spec.get('zones', []))} zone(s)")

    # obstacles for via sites
    pads = [p for fp in board.GetFootprints() for p in fp.Pads() if p.IsOnCopperLayer() or p.HasHole()]   # paste-only pads don't block a via
    bucket = {}
    for p in pads:
        bb = p.GetBoundingBox()
        for i in range(int(M(bb.GetLeft()) // 5), int(M(bb.GetRight()) // 5) + 1):
            for j in range(int(M(bb.GetTop()) // 5), int(M(bb.GetBottom()) // 5) + 1):
                bucket.setdefault((i, j), []).append(p)
    cyards = []
    for fp in board.GetFootprints():
        nets = {p.GetNetname() for p in fp.Pads()}
        for L in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
            c = fp.GetCourtyard(L)
            if c.OutlineCount():
                cyards.append((fp.GetReference(), c, c.BBox(), nets))
    placed = [(M(t.GetPosition().x), M(t.GetPosition().y)) for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    # routed copper of other nets (tracks and vias), bucketed: a via site must clear it too, so via
    # fields and stitching can be drawn after routing (2026-11-05)
    tbucket = {}
    for t in board.GetTracks():
        bb = t.GetBoundingBox()
        for i in range(int(M(bb.GetLeft()) // 5), int(M(bb.GetRight()) // 5) + 1):
            for j in range(int(M(bb.GetTop()) // 5), int(M(bb.GetBottom()) // 5) + 1):
                tbucket.setdefault((i, j), []).append(t)
    copper_layers = [l for l in board.GetEnabledLayers().CuStack()]
    r = vsize / 2
    total = 0
    short = []

    keep_clear = spec.get("keep_clear", [])
    class_clr = spec.get("class_clearance", {})

    def free(x, y, allow, own_pad=None, netname=None, same_ok=False):
        """a via site clear of the edge, the spec's keep_clear rects, pads (but own_pad, the pad a via-in-pad
        field fills), holes, routed copper (by class_clearance for their net class, else the clearance), and
        the courtyards of parts with no pad on the via's own net (a via in a pad skips courtyards: only pads matter)"""
        if not (outer[0] + M(edge) + r <= x <= outer[2] - M(edge) - r and outer[1] + M(edge) + r <= y <= outer[3] - M(edge) - r):
            return False
        if any(k[0] - r <= x <= k[2] + r and k[1] - r <= y <= k[3] + r for k in (kc["rect"] for kc in keep_clear)):
            return False
        pt = pcbnew.VECTOR2I(F(x), F(y))
        near = {id(q): q for di in (-1, 0, 1) for dj in (-1, 0, 1) for q in bucket.get((int(x // 5) + di, int(y // 5) + dj), [])}
        for p in near.values():                          # the 3 x 3 buckets: a part just over a bucket edge counts
            if own_pad is not None and p.GetParentFootprint().GetReference() == own_pad[0] and p.GetNumber() == own_pad[1]:
                continue
            if same_ok and netname and p.GetNetname() == netname and not p.HasHole():
                continue                                    # a same-net pad on the other side joins the via
            if p.HitTest(pt, F(r + clr)):
                return False
            if p.HasHole():
                d = p.GetDrillSize()
                if math.hypot(x - M(p.GetPosition().x), y - M(p.GetPosition().y)) < M(max(d.x, d.y)) / 2 + r + hclr:
                    return False
        circle = pcbnew.SHAPE_CIRCLE(pt, F(r))
        for t in {id(q): q for di in (-1, 0, 1) for dj in (-1, 0, 1)
                  for q in tbucket.get((int(x // 5) + di, int(y // 5) + dj), [])}.values():
            if netname and t.GetNetname() == netname:
                continue
            c_t = class_clr.get(t.GetNetClassName(), clr) if class_clr else clr
            if t.Type() == pcbnew.PCB_VIA_T:
                if math.hypot(x - M(t.GetPosition().x), y - M(t.GetPosition().y)) < r + M(t.GetWidth(pcbnew.F_Cu)) / 2 + c_t:
                    return False
            elif t.GetEffectiveShape(t.GetLayer()).Collide(circle, F(c_t)):
                return False
        if own_pad is not None:
            return True
        for ref, c, bb, nets in cyards:
            if ref in allow or (netname and netname in nets):
                continue
            if M(bb.GetLeft()) - r <= x <= M(bb.GetRight()) + r and M(bb.GetTop()) - r <= y <= M(bb.GetBottom()) + r \
                    and c.Contains(pt, -1, F(r)):
                return False
        return True

    for v in spec.get("vias", []):
        allow = set(v.get("allow_under", [])) | {"BB901", "BB902"}
        cand = []
        clip = v.get("clip")
        vp = v.get("pitch", pitch)
        own = pad = None
        if "in_pad" in v:                                   # vias inside one pad (filled and capped, DEC-027)
            ref, num = v["in_pad"]
            pad = next(p for fp in board.GetFootprints() if fp.GetReference() == ref for p in fp.Pads() if p.GetNumber() == num)
            bb = pad.GetBoundingBox()
            v = dict(v, rect=[M(bb.GetLeft()) + r, M(bb.GetTop()) + r, M(bb.GetRight()) - r, M(bb.GetBottom()) - r])
            own = (ref, num)
            allow.add(ref)
        # every image of a site: itself, its mirror, and both in each copy (dx, net, mirror net, axis)
        if "copies" in v:
            images = []
            for c in v["copies"]:
                images.append((lambda x, y, dx=c["dx"]: (x + dx, y), c["net"]))
                if "mirror_net" in c:
                    images.append((lambda x, y, dx=c["dx"], ax=c["axis_x"]: (2 * ax - (x + dx), y), c["mirror_net"]))
        else:
            images = [(lambda x, y: (x, y), v["net"])]
            if v.get("mirror"):
                m = v["mirror"]
                images.append((lambda x, y, ax=m["axis_x"]: (2 * ax - x, y), m["net"]))
        for x, y in sites(v, vp):
            if clip and not (clip[0] + r <= x <= clip[2] - r and clip[1] + r <= y <= clip[3] - r):
                continue
            if any(a_[0] - r <= x <= a_[2] + r and a_[1] - r <= y <= a_[3] + r for a_ in v.get("avoid", [])):
                continue
            ok = True
            for k, (f_, n_) in enumerate(images):            # kept only if every image is free (identical outputs)
                xi, yi = f_(x, y)
                if not free(xi, yi, allow, own if k == 0 else None, n_, v.get("same_net_pads_ok", False)):
                    ok = False; break
            if ok:
                cand.append((x, y))
        tow = v.get("toward")
        if tow:
            cand.sort(key=lambda s: min(math.hypot(s[0] - tx, s[1] - ty) for tx, ty in tow))
        keep = []
        for x, y in cand:
            if len(keep) >= v.get("max", 10 ** 6):
                break
            if any(math.hypot(x - px, y - py) < vp - 1e-6 for px, py in keep):
                continue
            if any(math.hypot(f_(x, y)[0] - px, f_(x, y)[1] - py) < vp - 1e-6 for f_, _ in images for px, py in placed):
                continue
            keep.append((x, y))
        groups = [(net(board, n_), [f_(x, y) for x, y in keep]) for f_, n_ in images]
        for n, pts in groups:
            for x, y in pts:
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(pcbnew.VECTOR2I(F(x), F(y)))
                via.SetWidth(F(vsize)); via.SetDrill(F(vdrill))
                via.SetNet(n); via.SetLocked(True)
                board.Add(via)
            placed += pts
        total += sum(len(p) for _, p in groups)
        flag = "" if len(keep) >= v.get("min", 0) else f"  BELOW the {v['min']} needed"
        if flag:
            short.append(v["name"])
        print(f"vias {v['name']:40s} {len(keep):4d} of {len(cand):4d} free sites (min {v.get('min', 0)}){flag}")
    # pad vias: one via per pad of a small rail, in the pad (filled and capped, DEC-027) when the pad
    # takes it, else just outside it with a stub track; and BGA dogbones (2026-11-04, small rails)
    for v in spec.get("points", []):                     # vias at given points (a BGA's cap vias)
        for x, y, n_ in v["points"]:
            add_via(board, x, y, n_, v.get("size", vsize), v.get("drill", vdrill)); placed.append((x, y)); total += 1
        print(f"points   {v['name']:36s} {len(v['points']):4d} placed")
    for v in spec.get("stubs", []):                      # short tracks between two of those vias
        for x1, y1, x2, y2, n_ in v["stubs"]:
            add_stub(board, (x1, y1), (x2, y2), board.GetLayerID(v.get("layer", "B.Cu")), v.get("width", 0.2), n_)
        print(f"stubs    {v['name']:36s} {len(v['stubs']):4d} drawn")
    for v in spec.get("dogbones", []):
        n_place, missing = place_dogbones(board, v, placed)
        total += n_place
        if missing:
            short.append(v["name"])
        print(f"dogbones {v['name']:36s} {n_place:4d} placed{'  NO SITE: ' + ', '.join(missing) if missing else ''}")
    for v in spec.get("pad_vias", []):
        n_place, n_stub, missing = place_pad_vias(board, v, free, placed, vsize, vdrill, clr)
        total += n_place
        if missing:
            short.append(v["name"])
        print(f"pad vias {v['name']:36s} {n_place:4d} placed ({n_stub} with a stub)"
              f"{'  NO SITE: ' + ', '.join(missing) if missing else ''}")
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
