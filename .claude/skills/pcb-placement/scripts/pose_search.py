#!/usr/bin/env python3
"""Find legal poses for one or more parts in one process (pcbnew skill).

Run with KiCad's Python. Loads the board once, tries every candidate pose of each part in
memory and keeps the best one that passes a fast screen; only the result is handed to KRT's
check_floorplan and check_assembly (once, at the end). A search that ran the KRT tools on
every pose took about a minute per pose; this screens hundreds of poses a second.

The screen, per candidate, against every other part on the board (parts already moved in this
run included):
- courtyard overlap on the same side, or courtyards closer than --courtyard-gap (0.02 mm; any
  overlap is an error in the project, and KRT's polygon measure reads a touch as a sliver);
- pad copper within the clearance of another part's pad on a shared copper layer, any net
  (same-net pads may not touch either: two parts' pads stacked are never legal);
- pad copper within the hole clearance of another part's hole (NPTH included), and the
  moved part's holes against the other parts' pads;
- pad copper or courtyard outside the board outline, inset by the edge clearance;
- a pad inside a rule area that forbids pads or footprints on that layer;
- the spec's `require` expression.
It does not judge tracks, zone fills, intent keepouts or heights: those are KRT's, at the end.

    $KPY pose_search.py BOARD IN_SPEC.json -o OUT.kicad_pcb [--verify --intent I --baseline B]
    $KPY pose_search.py BOARD --ref TP806 --near 231 108 [--radius 4] [--step 0.5]
                        [--rots 0,90,180,270] [--require EXPR] -o OUT.kicad_pcb

SPEC.json is a list, searched in order (each part greedily, the ones before it already moved):
  [{"ref": "TP806", "near": [231, 108], "radius": 4, "step": 0.5, "rots": [0, 90, 180, 270],
    "require": "dist(m('TP806','1'), m('U801','1')) <= 12", "rank": "d"}]
`near` defaults to the part's current position, `rots` to its current rotation, `radius` 2,
`step` 0.25. Expressions see m(ref, pad) -> (x, y) of a pad centre, pos(ref) -> (x, y, rot),
dist, math, and d: the candidate's distance from `near`. `rank` (smaller is better) defaults
to d, then the rotation change. `side` may be "F" or "B" to flip a part (default: stays).

--verify runs KRT's check_floorplan (0 ERROR) and check_assembly (VERDICT: buildable) on the
output with KRT_PY (a Python with numpy, scipy and shapely) from KRT_DIR (default
~/Dev/KiCadRoutingTools). Exit 0 when every part found a pose (and the verify passed), 1 when
a part found none (it is left where it was), 2 when the verify failed.
"""
import argparse
import json
import math
import os
import subprocess
import sys

import pcbnew

mm, FM = pcbnew.ToMM, pcbnew.FromMM
CU = [l for l in range(pcbnew.PCB_LAYER_ID_COUNT) if pcbnew.IsCopperLayer(l)]


def side_cy(fp):
    return fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)


def bbox(b):
    return b.GetLeft(), b.GetTop(), b.GetRight(), b.GetBottom()


def apart(a, b, margin=0):
    return a[2] + margin < b[0] or b[2] + margin < a[0] or a[3] + margin < b[1] or b[3] + margin < a[1]


class Board:
    def __init__(self, path, clearance, hole_clearance, edge, courtyard_gap=0.02):
        self.b = pcbnew.LoadBoard(path)
        ds = self.b.GetDesignSettings()
        self.clr = FM(clearance) if clearance is not None else ds.m_NetSettings.GetDefaultNetclass().GetClearance()
        self.hclr = FM(hole_clearance) if hole_clearance is not None else ds.m_HoleClearance
        self.edge = FM(edge) if edge is not None else ds.m_CopperEdgeClearance
        self.cy_gap = FM(courtyard_gap)
        o = self.b.GetBoardEdgesBoundingBox()
        self.outline = (o.GetLeft() + self.edge, o.GetTop() + self.edge, o.GetRight() - self.edge, o.GetBottom() - self.edge)
        self.cy_outline = bbox(o)
        self.fps = {f.GetReference(): f for f in self.b.GetFootprints()}
        self.rule_areas = [z for z in self.b.Zones() if z.GetIsRuleArea()
                           and (z.GetDoNotAllowPads() or z.GetDoNotAllowFootprints())]

    def m(self, ref, pad):
        p = next(p for p in self.fps[ref].Pads() if p.GetNumber() == str(pad))
        return mm(p.GetPosition().x), mm(p.GetPosition().y)

    def pos(self, ref):
        f = self.fps[ref]
        return mm(f.GetPosition().x), mm(f.GetPosition().y), f.GetOrientationDegrees()

    def why_not(self, fp):
        """None when fp's current pose passes the screen, else the first reason it does not."""
        ref = fp.GetReference()
        cy = side_cy(fp)
        cyb = bbox(cy.BBox()) if cy.OutlineCount() else None
        if cyb and (cyb[0] < self.cy_outline[0] or cyb[1] < self.cy_outline[1]
                    or cyb[2] > self.cy_outline[2] or cyb[3] > self.cy_outline[3]):
            return "courtyard off the board"
        pads = list(fp.Pads())
        pb = [bbox(p.GetBoundingBox()) for p in pads]
        for b in pb:
            if b[0] < self.outline[0] or b[1] < self.outline[1] or b[2] > self.outline[2] or b[3] > self.outline[3]:
                return "pad within the edge clearance"
        for z in self.rule_areas:
            for p in pads:
                if any(z.IsOnLayer(l) for l in CU if p.IsOnLayer(l)) and z.Outline().Contains(p.GetPosition()):
                    return f"pad {p.GetNumber()} in rule area {z.GetZoneName()}"
        reach = max(self.clr, self.hclr)
        mine = bbox(fp.GetBoundingBox(False))
        for oref, o in self.fps.items():
            if oref == ref or apart(mine, bbox(o.GetBoundingBox(False)), reach):
                continue
            if cyb and o.IsFlipped() == fp.IsFlipped():
                ocy = side_cy(o)
                if ocy.OutlineCount() and not apart(cyb, bbox(ocy.BBox()), self.cy_gap):
                    x = pcbnew.SHAPE_POLY_SET(cy)
                    x.BooleanIntersection(ocy)
                    # within cy_gap counts too: KRT measures arcs as polygons, so a pose this test
                    # calls touching-free can read 0.006 mm2 in check_floorplan's overlap budget
                    if x.Area() > 0 or any(cy.Collide(ocy.Outline(i), self.cy_gap) for i in range(ocy.OutlineCount())):
                        return f"courtyard overlaps {oref}"
            for p, b in zip(pads, pb):
                for q in o.Pads():
                    if apart(b, bbox(q.GetBoundingBox()), reach):
                        continue
                    for l in CU:
                        if p.IsOnLayer(l) and q.IsOnLayer(l) and \
                                p.GetEffectiveShape(l).Collide(q.GetEffectiveShape(l), self.clr):
                            return f"pad {p.GetNumber()} near {oref}.{q.GetNumber()}"
                    if q.HasHole() and p.GetEffectiveShape(pcbnew.F_Cu if not fp.IsFlipped() else pcbnew.B_Cu) \
                            .Collide(q.GetEffectiveHoleShape(), self.hclr):
                        return f"pad {p.GetNumber()} near {oref}'s hole"
                    if p.HasHole() and q.GetEffectiveShape(pcbnew.F_Cu if not o.IsFlipped() else pcbnew.B_Cu) \
                            .Collide(p.GetEffectiveHoleShape(), self.hclr):
                        return f"hole near {oref}.{q.GetNumber()}"
        return None


def frange(c, r, s):
    n = int(round(r / s))
    return [c + i * s for i in range(-n, n + 1)]


def search(B, s):
    ref = s["ref"]
    fp = B.fps[ref]
    x0, y0, r0 = B.pos(ref)
    start = (fp.GetPosition(), fp.GetOrientation(), fp.IsFlipped())
    if s.get("side") and (s["side"] == "B") != fp.IsFlipped():
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    nx, ny = s.get("near", (x0, y0))
    rots = s.get("rots", [r0])
    env = {"m": B.m, "pos": B.pos, "dist": math.dist, "math": math}
    cands = []
    for x in frange(nx, s.get("radius", 2.0), s.get("step", 0.25)):
        for y in frange(ny, s.get("radius", 2.0), s.get("step", 0.25)):
            d = math.hypot(x - nx, y - ny)
            if d <= s.get("radius", 2.0) + 1e-9:
                cands += [(d, abs(((r - r0) + 180) % 360 - 180), x, y, r) for r in rots]
    cands.sort()
    tried, best, reasons = 0, None, {}
    for d, dr, x, y, r in cands:
        fp.SetPosition(pcbnew.VECTOR2I(FM(x), FM(y)))
        fp.SetOrientationDegrees(r)
        tried += 1
        env["d"] = d
        if "require" in s and not eval(s["require"], env):
            reasons["require"] = reasons.get("require", 0) + 1
            continue
        why = B.why_not(fp)
        if why:
            # group by the part in the way, not by pad number: "clearance to J908"
            k = "clearance to " + why.split(" near ")[1].split(".")[0].replace("'s hole", " (hole)") \
                if " near " in why else why
            reasons[k] = reasons.get(k, 0) + 1
            continue
        rank = eval(s["rank"], env) if "rank" in s else (d, dr)
        if best is None or rank < best[0]:
            best = (rank, x, y, r)
        if "rank" not in s:
            break   # the candidates are already in (d, rotation change) order
    if best is None:
        fp.SetPosition(start[0])
        fp.SetOrientation(start[1])
        if fp.IsFlipped() != start[2]:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        top = sorted(reasons.items(), key=lambda kv: -kv[1])[:5]
        print(f"{ref}: nothing legal in {tried} poses; most common: " + "; ".join(f"{k} ({v})" for k, v in top))
        return False
    _, x, y, r = best
    fp.SetPosition(pcbnew.VECTOR2I(FM(x), FM(y)))
    fp.SetOrientationDegrees(r)
    print(f"{ref}: ({x0:.3f}, {y0:.3f}, {r0:g}) -> ({x:.3f}, {y:.3f}, {r:g}), "
          f"{math.hypot(x - x0, y - y0):.2f} mm, {tried} poses tried")
    return True


def verify(out, intent, baseline):
    py = os.environ.get("KRT_PY")
    if not py:
        print("verify: set KRT_PY to a Python with numpy, scipy and shapely")
        return False
    krt = os.environ.get("KRT_DIR", os.path.expanduser("~/Dev/KiCadRoutingTools"))
    ia = ["--intent", intent] if intent else []
    fo = subprocess.run([py, "-X", "utf8", "py_tools/check_floorplan.py", out] + ia,
                        cwd=krt, capture_output=True, text=True).stdout
    if any(s in fo for s in ("cannot parse", "Traceback", "No module named")):
        print("verify: check_floorplan could not run\n" + fo[-800:])
        return False
    errs = [l for l in fo.splitlines() if "[ERROR]" in l]
    ca = subprocess.run([py, "-X", "utf8", "py_tools/check_assembly.py", out]
                        + (["--baseline", baseline] if baseline else []) + ia,
                        cwd=krt, capture_output=True, text=True).stdout
    ok = not errs and "VERDICT: buildable" in ca
    print(f"verify: check_floorplan {len(errs)} ERROR; check_assembly "
          + next((l.strip() for l in ca.splitlines() if "VERDICT" in l), "no verdict"))
    for l in errs[:10]:
        print("  " + l.strip())
    if "VERDICT: buildable" not in ca:
        keep = False
        for l in ca.splitlines():
            if l.lstrip().startswith(("COURTYARD", "BLOCKING", "pad/hole")) or "GATE" in l:
                keep = True
            elif keep and not l.startswith("    "):
                keep = False
            if keep:
                print("  " + l.rstrip())
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("spec", nargs="?")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--ref")
    ap.add_argument("--near", nargs=2, type=float)
    ap.add_argument("--radius", type=float, default=2.0)
    ap.add_argument("--step", type=float, default=0.25)
    ap.add_argument("--rots")
    ap.add_argument("--require")
    ap.add_argument("--clearance", type=float, help="mm; default the board's Default net class")
    ap.add_argument("--hole-clearance", type=float, help="mm; default the board's")
    ap.add_argument("--edge", type=float, help="mm; default the board's copper-to-edge clearance")
    ap.add_argument("--courtyard-gap", type=float, default=0.02,
                    help="mm courtyards must stay apart (default 0.02, so KRT's polygon measure reads no overlap)")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--intent")
    ap.add_argument("--baseline")
    a = ap.parse_args()
    if a.spec:
        specs = json.load(open(a.spec))
    elif a.ref:
        s = {"ref": a.ref, "radius": a.radius, "step": a.step}
        if a.near:
            s["near"] = a.near
        if a.rots:
            s["rots"] = [float(r) for r in a.rots.split(",")]
        if a.require:
            s["require"] = a.require
        specs = [s]
    else:
        ap.error("give a SPEC.json or --ref")
    B = Board(a.board, a.clearance, a.hole_clearance, a.edge, a.courtyard_gap)
    found = [search(B, s) for s in specs]
    B.b.Save(a.out)
    # KRT reads the project and rule files beside a board, and refuses a board whose siblings
    # differ from its input's: give the output the input's, and no stale ones.
    src, dst = os.path.splitext(a.board)[0], os.path.splitext(a.out)[0]
    if os.path.abspath(src) != os.path.abspath(dst):
        for ext in (".kicad_pro", ".kicad_dru"):
            if os.path.exists(src + ext):
                open(dst + ext, "w").write(open(src + ext).read())
            elif os.path.exists(dst + ext):
                os.remove(dst + ext)
    print(f"wrote {a.out}")
    if not all(found):
        return 1
    if a.verify and not verify(a.out, a.intent, a.baseline):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
