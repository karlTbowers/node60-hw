#!/usr/bin/env python3
"""Build one study attempt on a copy of the board (2026-11-12 passive-placement study). KiCad's Python.

    $KPY apply_attempt.py IN.kicad_pcb ATTEMPT.json [ATTEMPT2.json ...] OUT.kicad_pcb [--moves OUT_moves.json]

ATTEMPT.json:
  "moves":  {"R211": {"x": 113.0, "y": 69.55, "p1": "W", "side": "B"}}   p1 = which way pad 1 lies from the centre
  "delete": [{"seg": [x1, y1, x2, y2]}, {"via": [x, y]}, {"box": [x0, y0, x1, y1], "net": "3V3_MAIN"}]
  "tracks": [{"net": "3V3_MAIN", "layer": "B.Cu", "w": 0.3, "pts": [[x, y], ...]}]
  "vias":   [{"net": "3V3_MAIN", "x": 1, "y": 2, "d": 0.45, "drill": 0.25}]
  "zones":  [{"name": "PWR_X_F", "like": "PWR_VBAT_IN_bar_F", "rect": [x0, y0, x1, y1]}]   same net, layer and settings as "like"
Several attempts are applied in order (a combined board). Copper added here is unlocked study copper;
landing a move on the real board goes through power_shapes.json and the block tables.
"""
import json, math, sys
import pcbnew

F, M = pcbnew.FromMM, pcbnew.ToMM
DIRS = {"E": (1, 0), "W": (-1, 0), "N": (0, -1), "S": (0, 1)}


def net_of(b, name):
    for n in (name, "/" + name):
        ni = b.FindNet(n)
        if ni: return ni
    for nm, ni in b.GetNetsByName().items():
        if str(nm).split("/")[-1] == name: return ni
    sys.exit(f"no net {name}")


def main():
    args = sys.argv[1:]
    mv_out = None
    if "--moves" in args:
        i = args.index("--moves"); mv_out = args[i + 1]; del args[i:i + 2]
    src, out, specs = args[0], args[-1], args[1:-1]
    b = pcbnew.LoadBoard(src)
    moved = {}
    stats = {"deleted_tracks_mm": 0.0, "deleted_vias": 0, "added_tracks_mm": 0.0, "added_vias": 0}
    # Every spec's moves first, then every spec's new copper, then every delete: pcbnew's Python
    # objects go stale after a Remove, so nothing is looked up once the first item is gone.
    loaded = [(sp, json.load(open(sp))) for sp in specs]
    for sp, a in loaded:
        for ref, m in a.get("moves", {}).items():
            fp = b.FindFootprintByReference(ref)
            if ref not in moved:
                moved[ref] = {"from": [round(M(fp.GetPosition().x), 3), round(M(fp.GetPosition().y), 3), fp.GetOrientationDegrees(), "B" if fp.IsFlipped() else "F"]}
            side = m.get("side", "B" if fp.IsFlipped() else "F")
            if (side == "B") != fp.IsFlipped():
                fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            fp.SetPosition(pcbnew.VECTOR2I(F(m["x"]), F(m["y"])))
            if "rot" in m:
                fp.SetOrientationDegrees(m["rot"])
            else:
                want = DIRS[m["p1"]]
                for rot in (0, 90, 180, 270):
                    fp.SetOrientationDegrees(rot)
                    p = next(p for p in fp.Pads() if p.GetNumber() == "1").GetPosition()
                    dx, dy = M(p.x) - m["x"], M(p.y) - m["y"]
                    n = math.hypot(dx, dy)
                    if n > 0.05 and dx / n * want[0] + dy / n * want[1] > 0.9:
                        break
                else:
                    sys.exit(f"{ref}: no rotation puts pad 1 {m['p1']}")
            moved[ref]["to"] = [m["x"], m["y"], fp.GetOrientationDegrees(), side]
            moved[ref]["pads"] = {p.GetNumber(): [p.GetNetname().split("/")[-1], round(M(p.GetPosition().x), 3), round(M(p.GetPosition().y), 3)] for p in fp.Pads()}
    for sp, a in loaded:
        for tr in a.get("tracks", []):
            ni = net_of(b, tr["net"]); lid = b.GetLayerID(tr["layer"])
            for p, q in zip(tr["pts"], tr["pts"][1:]):
                t = pcbnew.PCB_TRACK(b)
                t.SetStart(pcbnew.VECTOR2I(F(p[0]), F(p[1]))); t.SetEnd(pcbnew.VECTOR2I(F(q[0]), F(q[1])))
                t.SetWidth(F(tr["w"])); t.SetLayer(lid); t.SetNet(ni); b.Add(t)
                stats["added_tracks_mm"] += math.dist(p, q)
        for v in a.get("vias", []):
            via = pcbnew.PCB_VIA(b)
            via.SetPosition(pcbnew.VECTOR2I(F(v["x"]), F(v["y"])))
            via.SetWidth(pcbnew.F_Cu, F(v.get("d", 0.45)))
            via.SetDrill(F(v.get("drill", 0.25))); via.SetNet(net_of(b, v["net"])); b.Add(via)
            stats["added_vias"] += 1
    for sp, a in loaded:                              # power shapes: a copy of a like zone with a new rectangle
        for zs in a.get("zones", []):
            src = next(z for z in b.Zones() if z.GetZoneName() == zs["like"])
            nz = pcbnew.ZONE(src)
            nz.SetZoneName(zs["name"]); nz.ResetUuid()
            nz.SetAssignedPriority(src.GetAssignedPriority() + 1)      # it overlaps its neighbour: distinct priorities
            o = nz.Outline(); o.RemoveAllContours(); o.NewOutline()
            x0, y0, x1, y1 = zs["rect"]
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                o.Append(F(x), F(y))
            nz.UnFill(); b.Add(nz)
            stats["added_zone_mm2"] = stats.get("added_zone_mm2", 0) + (x1 - x0) * (y1 - y0)
    doomed = []
    items = [(t, t.Type() == pcbnew.PCB_VIA_T, (M(t.GetStart().x), M(t.GetStart().y)), (M(t.GetEnd().x), M(t.GetEnd().y)),
              t.GetNetname().split("/")[-1]) for t in b.GetTracks()]
    for sp, a in loaded:
        for dl in a.get("delete", []):
            hit = 0
            for k, (t, isvia, P1, P2, net) in enumerate(items):
                if k in doomed:
                    continue
                kill = False
                if "seg" in dl and not isvia:
                    q1, q2 = tuple(dl["seg"][:2]), tuple(dl["seg"][2:])
                    kill = (math.dist(P1, q1) < 0.06 and math.dist(P2, q2) < 0.06) or (math.dist(P1, q2) < 0.06 and math.dist(P2, q1) < 0.06)
                elif "via" in dl and isvia:
                    kill = math.dist(P1, tuple(dl["via"])) < 0.06
                elif "box" in dl:
                    x0, y0, x1, y1 = dl["box"]
                    ins = lambda p: x0 <= p[0] <= x1 and y0 <= p[1] <= y1
                    kill = ins(P1) and ins(P2) and net == dl["net"]
                if kill:
                    if isvia: stats["deleted_vias"] += 1
                    else: stats["deleted_tracks_mm"] += math.dist(P1, P2)
                    doomed.append(k); hit += 1
            if not hit:
                sys.exit(f"{sp}: delete {dl} matched nothing")
    for k in doomed:
        b.Remove(items[k][0])
    b.Save(out)
    if mv_out:
        json.dump(moved, open(mv_out, "w"), indent=1)
    for ref, m in moved.items():
        print(f"{ref}: {m['from']} -> {m['to']}  pads {m['pads']}")
    print({k: round(v, 1) for k, v in stats.items()})


if __name__ == "__main__":
    main()
