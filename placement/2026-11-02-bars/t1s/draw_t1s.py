#!/usr/bin/env python3
"""Draw a hand-routed spec onto a board: moves, deletions, tracks, vias, rule areas (Node60, T1S route).

    $KPY draw_t1s.py BOARD SPEC.json OUT.kicad_pcb

SPEC.json:
{"moves": {"C502": {"x": 156.1, "y": 47.5, "rot": 90, "side": "B"}},
 "delete": [{"net": "3V3_MAIN", "rect": [x0, y0, x1, y1]} | {"net": "/RMII0_T1S_TXD0"}],   tracks and vias
 "tracks": [{"net": "/T1S_N", "layer": "F.Cu", "width": 0.165, "points": [[x, y], ...]}],
 "vias": [{"net": "/T1S_N", "at": [x, y], "size": 0.35, "drill": 0.2}],
 "areas": [{"name": "T1S_PINS_U501", "layers": ["B.Cu"], "rect": [x0, y0, x1, y1]}]}
Everything drawn is locked unless a track says "locked": false (hand copper on a power net, which
draw_power.py would otherwise take for its own and sweep); zones are refilled by kicad-cli afterwards (pcbnew's Python filler differs).
"""
import json
import sys

import pcbnew

F = pcbnew.FromMM


def inside(t, r):
    pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
    return any(r[0] <= pcbnew.ToMM(p.x) <= r[2] and r[1] <= pcbnew.ToMM(p.y) <= r[3] for p in pts)


def main():
    b = pcbnew.LoadBoard(sys.argv[1])
    spec = json.load(open(sys.argv[2]))
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    for ref, m in spec.get("moves", {}).items():
        f = fps[ref]
        want_b = m.get("side", "B" if f.IsFlipped() else "F") == "B"
        if want_b != f.IsFlipped():
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        f.SetPosition(pcbnew.VECTOR2I(F(m["x"]), F(m["y"])))
        f.SetOrientationDegrees(m["rot"])
    gone = 0
    for d in spec.get("delete", []):
        for t in list(b.GetTracks()):
            if t.GetNetname() == d["net"] and ("rect" not in d or inside(t, d["rect"])):
                b.Delete(t); gone += 1
    nets = {}
    def net(n):
        if n not in nets:
            nets[n] = b.FindNet(n)
            if nets[n] is None:
                sys.exit(f"no net {n}")
        return nets[n]
    nt = nv = 0
    for tr in spec.get("tracks", []):
        layer = b.GetLayerID(tr["layer"]) if tr["layer"] not in ("F.Cu", "B.Cu") else (pcbnew.F_Cu if tr["layer"] == "F.Cu" else pcbnew.B_Cu)
        if tr["layer"].startswith("In"):
            layer = {"In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu, "In3.Cu": pcbnew.In3_Cu, "In4.Cu": pcbnew.In4_Cu}[tr["layer"]]
        pts = tr["points"]
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(F(a[0]), F(a[1]))); t.SetEnd(pcbnew.VECTOR2I(F(c[0]), F(c[1])))
            t.SetWidth(F(tr["width"])); t.SetLayer(layer); t.SetNet(net(tr["net"])); t.SetLocked(tr.get("locked", True))
            b.Add(t); nt += 1
    for v in spec.get("vias", []):
        o = pcbnew.PCB_VIA(b)
        o.SetPosition(pcbnew.VECTOR2I(F(v["at"][0]), F(v["at"][1])))
        o.SetWidth(F(v.get("size", 0.35))); o.SetDrill(F(v.get("drill", 0.2)))
        o.SetNet(net(v["net"])); o.SetLocked(True); b.Add(o); nv += 1
    for a in spec.get("areas", []):
        for z in list(b.Zones()):
            if z.GetIsRuleArea() and z.GetZoneName() == a["name"]:
                b.Delete(z)
        z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName(a["name"])
        ls = pcbnew.LSET()
        for l in a["layers"]:
            ls.AddLayer(b.GetLayerID(l) if l not in ("F.Cu", "B.Cu") else (pcbnew.F_Cu if l == "F.Cu" else pcbnew.B_Cu))
        z.SetLayerSet(ls)
        for allow in (z.SetDoNotAllowTracks, z.SetDoNotAllowVias, z.SetDoNotAllowPads, z.SetDoNotAllowZoneFills, z.SetDoNotAllowFootprints):
            allow(False)
        o = z.Outline(); o.RemoveAllContours(); o.NewOutline()
        x0, y0, x1, y1 = a["rect"]
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            o.Append(F(x), F(y))
        b.Add(z)
    b.Save(sys.argv[3])
    print(f"{sys.argv[3]}: {len(spec.get('moves', {}))} moved, {gone} deleted, {nt} tracks, {nv} vias drawn")


if __name__ == "__main__":
    main()
