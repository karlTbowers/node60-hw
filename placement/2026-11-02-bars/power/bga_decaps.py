#!/usr/bin/env python3
"""Pose U401's top-side decoupling caps on its via grid (D22 repair R3, 2026-11-04).

Run with KiCad's Python from the repo root:

    $KPY bga_decaps.py BOARD OUT.kicad_pcb OUT.json [--ref U401] [--caps C401,C402,...]

The BGA's vias sit at its cell centres (the diagonal points between four balls, 0.8 mm pitch).
Each cap gets its rail pad over a via of its own net and its GND pad over a GND via in the
neighbouring cell (0402: the next cell, 0.8 mm; 0603: two cells over, the middle cell kept
empty), so the cap joins its vias with no track. Rules:

- V11, V25 and 1V5 caps sit on a dogbone of one of their own balls (those nets have no plane
  but the 1V5 island, which is redrawn round its vias); 3V3 caps may also sit on a new 3V3 via
  in any free cell (the In3 plane joins it), nearest a 3V3 ball first;
- every ball keeps one diagonal cell for its own dogbone: a power or ground ball's is chosen
  here, a signal ball's is reserved for the hand escape (pointing away from the BGA's centre
  first) and no cap via may take it;
- no 3V3 via in or beside the core box, where the In3 1V5 island is;
- caps' courtyards may not overlap each other or any other top-side part's;
- a cell's via clears every other-net pad on either side (0.10 mm copper, ESCAPE_U401's
  clearance; 0.20 mm hole clearance).

Greedy, most constrained cap first (fewest legal poses). The board is saved with the caps moved
(no vias drawn); OUT.json holds the cap poses, the power and ground dogbone cells ("prefer" for
draw_power.py's dogbones), the extra vias, and the caps that found no pose.
"""
import argparse
import json
import math

import pcbnew

F, M = pcbnew.FromMM, pcbnew.ToMM
PITCH = 0.8
VIA, DRILL = 0.4, 0.2
CLR, HCLR = 0.10, 0.20
CORE = (199.33, 49.89, 202.53, 53.09)      # U401's core box on In3: the 1V5 island, no 3V3 vias in it


def short(n):
    return n.split("/")[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board"); ap.add_argument("out"); ap.add_argument("json")
    ap.add_argument("--ref", default="U401")
    ap.add_argument("--caps", default="C401,C402,C403,C404,C406,C407,C408,C410,C412,C413,C414,C415,C423,"
                                      "C417,C418,C419,C421,C422")
    a = ap.parse_args()
    b = pcbnew.LoadBoard(a.board)
    bga = b.FindFootprintByReference(a.ref)
    balls = list(bga.Pads())
    bx = [M(p.GetPosition().x) for p in balls]; by = [M(p.GetPosition().y) for p in balls]
    cx, cy = (min(bx) + max(bx)) / 2, (min(by) + max(by)) / 2
    x0, y0 = min(bx), min(by)
    caps = [b.FindFootprintByReference(r) for r in a.caps.split(",")]
    capset = {c.GetReference() for c in caps}
    POWER = {"3V3_MAIN", "1V5_CORE", "1V1_MCU_V11", "2V5_MCU_V25", "GND"}

    def cell_xy(i, j):
        return x0 + PITCH / 2 + i * PITCH, y0 + PITCH / 2 + j * PITCH
    ni = int(round((max(bx) - min(bx)) / PITCH))
    # every cell a via could use: inside the ball field and one ring outside it
    cells = {(i, j): cell_xy(i, j) for i in range(-2, ni + 2) for j in range(-2, ni + 2)}
    # fixed copper the vias must clear: every pad except the caps being moved
    fixed = [p for fp in b.GetFootprints() if fp.GetReference() not in capset for p in fp.Pads()
             if abs(M(p.GetPosition().x) - cx) < 12 and abs(M(p.GetPosition().y) - cy) < 12]

    def via_ok(ij, netname):
        x, y = cells[ij]
        pt = pcbnew.VECTOR2I(F(x), F(y))
        for q in fixed:
            if short(q.GetNetname()) == netname and q.GetParentFootprint().GetReference() == a.ref:
                continue                     # its own ball (a dogbone touches it through the track)
            if q.HitTest(pt, F(VIA / 2 + CLR)) or q.HitTest(pt, F(DRILL / 2 + HCLR)):
                return False
        return True
    ok_cache = {}

    def free_for(ij, netname):
        k = (ij, netname)
        if k not in ok_cache:
            ok_cache[k] = ij in cells and via_ok(ij, netname)
            if ok_cache[k] and netname == "3V3_MAIN" and ij in cells:   # the 1V5 island's core box
                x, y = cells[ij]
                if CORE[0] - 0.3 <= x <= CORE[2] + 0.3 and CORE[1] - 0.3 <= y <= CORE[3] + 0.3:
                    ok_cache[k] = False
        return ok_cache[k]

    def diag(p):
        """a ball's four diagonal cells, the one away from the BGA's centre first"""
        x, y = M(p.GetPosition().x), M(p.GetPosition().y)
        i0, j0 = int(round((x - x0) / PITCH)), int(round((y - y0) / PITCH))
        sx = 1 if x > cx + 1e-3 else -1
        sy = 1 if y > cy + 1e-3 else -1
        # cell (i, j) is the centre between balls i, i+1 and j, j+1
        res = []
        for dx in (sx, -sx):
            for dy in (sy, -sy):
                res.append(((i0 if dx > 0 else i0 - 1), (j0 if dy > 0 else j0 - 1)))
        return res

    via = {}          # cell -> net
    dog = {}          # ball number -> cell
    reserved = {}     # cell -> ball number (a signal ball's escape cell)
    blocked = set()   # cells under an 0603's body
    # signal balls reserve their first legal diagonal (hand escape); power balls are chosen below
    for p in balls:
        n = short(p.GetNetname())
        if not n or n.startswith("unconnected") or n in POWER:
            continue
        for ij in diag(p):
            if ij not in reserved and free_for(ij, n):
                reserved[ij] = p.GetNumber(); break
    power_balls = {short(p.GetNetname()): [] for p in balls}
    for p in balls:
        power_balls.setdefault(short(p.GetNetname()), [])
    for p in balls:
        if short(p.GetNetname()) in POWER:
            power_balls[short(p.GetNetname())].append(p)

    # the core nets without a plane (1V5 has only its island) get their dogbones first, so caps can
    # grow from them; 3V3 and GND balls are chosen with the caps
    PRE = ("1V5_CORE", "1V1_MCU_V11", "2V5_MCU_V25")
    links = []        # [cell a, cell b, net]: a B stub between a new via and its net's via
    for net in PRE:
        for p in power_balls.get(net, []):
            for ij in diag(p):
                if ij in reserved or ij in via or not free_for(ij, net):
                    continue
                dog[p.GetNumber()] = ij; via[ij] = net; break

    # courtyards of the other top-side parts nearby
    def crt(fp):
        c = fp.GetCourtyard(pcbnew.F_CrtYd)
        return c if c.OutlineCount() else None
    others = [crt(fp) for fp in b.GetFootprints() if fp.GetReference() not in capset and not fp.IsFlipped()
              and abs(M(fp.GetPosition().x) - cx) < 15 and abs(M(fp.GetPosition().y) - cy) < 15]
    others = [c for c in others if c]
    placed_crt = []

    def crt_ok(fp):
        c = fp.GetCourtyard(pcbnew.F_CrtYd)
        for o in others + placed_crt:
            if c.BBox().Intersects(o.BBox()):
                inter = pcbnew.SHAPE_POLY_SET(c); inter.BooleanIntersection(o)
                if inter.Area() > 1e3:          # more than 0.001 mm² (touching is fine)
                    return False
        return True

    def poses(fp):
        """legal (score, x, y, rot, rail cell, gnd cell, new rail via?, ball) for a cap now"""
        pads = {p.GetNumber(): p for p in fp.Pads()}
        rail = short(pads["1"].GetNetname())
        span = abs(M(pads["1"].GetPosition().x - pads["2"].GetPosition().x)) + abs(M(pads["1"].GetPosition().y - pads["2"].GetPosition().y))
        step = 2 if span > 1.2 else 1
        cands = []
        # rail cells: a ball's dogbone (taken or open), or for 3V3 any open cell near a 3V3 ball
        rcells = []
        for p in power_balls.get(rail, []):
            if p.GetNumber() in dog:
                rcells.append((dog[p.GetNumber()], p, False))
            else:
                rcells += [(ij, p, False) for ij in diag(p)]
        if rail in PRE:
            rcells = [(ij, None, False) for ij, n_ in via.items() if n_ == rail]
            for ij, n_ in list(via.items()):
                if n_ != rail:
                    continue
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nb = (ij[0] + di, ij[1] + dj)
                    if nb not in via:
                        rcells.append((nb, ("link", ij), True))
        if rail == "3V3_MAIN":
            for ij, (x, y) in cells.items():
                d = min(math.hypot(x - M(p.GetPosition().x), y - M(p.GetPosition().y)) for p in power_balls[rail])
                if d < 2.5:
                    rcells.append((ij, None, True))
        for ij, ball, new in rcells:
            if ij in reserved or ij in blocked:
                continue
            if via.get(ij, rail) != rail or not free_for(ij, rail):
                continue
            if ball is not None and not isinstance(ball, tuple) and ball.GetNumber() not in dog and ij in via:
                continue
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                g = (ij[0] + di * step, ij[1] + dj * step)
                mid = (ij[0] + di, ij[1] + dj) if step == 2 else None
                if g in reserved or g in blocked or via.get(g, "GND") != "GND" or not free_for(g, "GND"):
                    continue
                if mid and (mid in via or mid in reserved):
                    continue
                (xa, ya), (xg, yg) = cells[ij], cells[g]
                rot = {(1, 0): 0, (-1, 0): 180, (0, 1): 90, (0, -1): 270}[(di, dj)]
                fp.SetPosition(pcbnew.VECTOR2I(F((xa + xg) / 2), F((ya + yg) / 2)))
                for r_ in (rot, (rot + 180) % 360, (rot + 90) % 360, (rot + 270) % 360):
                    fp.SetOrientationDegrees(r_)
                    p1, p2 = pads["1"].GetPosition(), pads["2"].GetPosition()
                    if math.hypot(M(p1.x) - xa, M(p1.y) - ya) < 0.12 and math.hypot(M(p2.x) - xg, M(p2.y) - yg) < 0.12:
                        break
                else:
                    continue
                if not crt_ok(fp):
                    continue
                dball = min(math.hypot(xa - M(p.GetPosition().x), ya - M(p.GetPosition().y)) for p in power_balls[rail]) - 0.566
                score = dball + (0.3 if new else 0) + (0 if g in via else 0.2)
                cands.append((score, (xa + xg) / 2, (ya + yg) / 2, fp.GetOrientationDegrees(), ij, g, new, ball, mid))
        return sorted(cands, key=lambda c: c[0])

    home = {fp.GetReference(): (fp.GetPosition(), fp.GetOrientationDegrees()) for fp in caps}
    todo = list(caps)
    result, failed = {}, []
    while todo:
        options = []
        for fp in todo:
            c = poses(fp)
            fp.SetPosition(home[fp.GetReference()][0]); fp.SetOrientationDegrees(home[fp.GetReference()][1])
            options.append((len(c), fp, c))
        options.sort(key=lambda o: o[0])
        n, fp, c = options[0]
        todo.remove(fp)
        if not c:
            failed.append(fp.GetReference())
            continue
        score, x, y, rot, ij, g, new, ball, mid = c[0]
        fp.SetPosition(pcbnew.VECTOR2I(F(x), F(y))); fp.SetOrientationDegrees(rot)
        placed_crt.append(pcbnew.SHAPE_POLY_SET(fp.GetCourtyard(pcbnew.F_CrtYd)))
        rail = short(fp.Pads()[0].GetNetname()) if fp.Pads()[0].GetNumber() == "1" else short(fp.Pads()[1].GetNetname())
        via[ij] = rail; via[g] = "GND"
        if mid:
            blocked.add(mid)
        link = None
        if isinstance(ball, tuple):
            link = ball[1]
            if rail != "1V5_CORE":                        # the island joins 1V5; V11/V25 need a stub
                links.append([list(cells[ij]), list(cells[link]), rail])
            ball = None
        if ball is not None:
            dog[ball.GetNumber()] = ij
        result[fp.GetReference()] = {"x": round(x, 3), "y": round(y, 3), "rot": rot, "rail_cell": list(cells[ij]),
                                     "gnd_cell": list(cells[g]), "new_rail_via": new,
                                     "ball": ball.GetNumber() if ball is not None else None,
                                     "linked_to": list(cells[link]) if link else None}
    # caps that found no pose go back where they were
    for r in failed:
        fp = b.FindFootprintByReference(r)
        fp.SetPosition(home[r][0]); fp.SetOrientationDegrees(home[r][1])
    # the remaining power and ground balls: their first legal free diagonal
    for net, ps in power_balls.items():
        if net not in POWER:
            continue
        for p in ps:
            if p.GetNumber() in dog:
                continue
            for ij in diag(p):
                if ij in reserved or ij in blocked or ij in via or not free_for(ij, net):
                    continue
                dog[p.GetNumber()] = ij; via[ij] = net; break
    # a power ball still without a cell joins an orthogonal neighbour ball of its net on B
    ball_links = []
    for net, ps in power_balls.items():
        if net not in POWER:
            continue
        for p in ps:
            if p.GetNumber() in dog:
                continue
            x, y = M(p.GetPosition().x), M(p.GetPosition().y)
            for q in ps:
                if q.GetNumber() in dog and abs(math.hypot(M(q.GetPosition().x) - x, M(q.GetPosition().y) - y) - PITCH) < 0.01:
                    ball_links.append([round(x, 4), round(y, 4), round(M(q.GetPosition().x), 4), round(M(q.GetPosition().y), 4), net, p.GetNumber()])
                    break
    # extra vias: cap vias that are not a ball's dogbone
    dogcells = set(dog.values())
    extra = [[round(cells[ij][0], 3), round(cells[ij][1], 3), n] for ij, n in via.items() if ij not in dogcells]
    prefer = {}
    for p in balls:
        if p.GetNumber() in dog:
            (vx, vy) = cells[dog[p.GetNumber()]]
            prefer[p.GetNumber()] = [int(round((vx - M(p.GetPosition().x)) / (PITCH / 2))), int(round((vy - M(p.GetPosition().y)) / (PITCH / 2)))]
    nopower = [p.GetNumber() for net, ps in power_balls.items() if net in POWER for p in ps if p.GetNumber() not in dog]
    one5 = [list(cells[ij]) for ij, n_ in via.items() if n_ == "1V5_CORE"]
    out = {"reserved_cells": [[round(cells[ij][0], 3), round(cells[ij][1], 3), n_] for ij, n_ in reserved.items()],
           "ball_links": ball_links, "all_vias": [[round(cells[ij][0], 3), round(cells[ij][1], 3), n_] for ij, n_ in via.items()], "links": links, "v1v5_cells": one5, "v3v3_cells": [list(cells[ij]) for ij, n_ in via.items() if n_ == "3V3_MAIN"],
           "caps": result, "failed": failed, "prefer": prefer, "extra_vias": extra, "balls_without_dogbone": nopower,
           "reserved_signal_cells": len(reserved)}
    json.dump(out, open(a.json, "w"), indent=1)
    b.Save(a.out)
    print(f"{len(result)} caps on vias, failed: {failed}; {len(extra)} extra vias; power/GND balls without a dogbone: {nopower};"
          f" {len(reserved)} signal cells reserved")


if __name__ == "__main__":
    main()
