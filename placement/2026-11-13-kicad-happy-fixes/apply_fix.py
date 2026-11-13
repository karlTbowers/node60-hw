#!/usr/bin/env python3
"""apply_fix.py IN.kicad_pcb SPEC.json [SPEC2.json ...] OUT.kicad_pcb -- apply hand specs to a board (KiCad's Python).

SPEC.json (every key optional):
  "delete": [{"seg": [x1, y1, x2, y2], "layer": "B.Cu", "net": "MDC"}, {"via": [x, y], "net": "..."}]
            a seg or via must match exactly one item unless "all": true (duplicates on one spot); locked items too.
  "tracks": [{"net": "TX_EN", "layer": "In2.Cu", "w": 0.15, "pts": [[x, y], ...], "lock": true}]
  "vias":   [{"net": "GND", "x": 1, "y": 2, "d": 0.6, "drill": 0.33, "lock": true}]
  "resize": [{"via": [x, y], "d": 0.45, "drill": 0.25}]
Nets are matched by their last path element. Layer names without KiCad's .PWR/.GND suffix."""
import json, math, sys
import pcbnew
F, M = pcbnew.FromMM, pcbnew.ToMM


def main():
    src, out, specs = sys.argv[1], sys.argv[-1], sys.argv[2:-1]
    b = pcbnew.LoadBoard(src)
    lname = lambda l: b.GetLayerName(l).split(".PWR")[0].split(".GND")[0]
    lid = {lname(l): l for l in b.GetEnabledLayers().Seq()}
    nets = {}
    for nm, ni in b.GetNetsByName().items():
        nets.setdefault(str(nm).split("/")[-1], ni)
    loaded = [(sp, json.load(open(sp))) for sp in specs]
    items = [(t, t.Type() == pcbnew.PCB_VIA_T, (M(t.GetStart().x), M(t.GetStart().y)), (M(t.GetEnd().x), M(t.GetEnd().y)),
              t.GetNetname().split("/")[-1], None if t.Type() == pcbnew.PCB_VIA_T else lname(t.GetLayer())) for t in b.GetTracks()]
    n = {"deleted": 0, "tracks": 0, "vias": 0, "resized": 0}
    for sp, a in loaded:
        for rz in a.get("resize", []):
            hit = [t for t, isvia, P1, _, net, _ in items if isvia and math.dist(P1, rz["via"]) < 0.006]
            if len(hit) != 1: sys.exit(f"{sp}: resize {rz} matched {len(hit)}")
            for l in b.GetEnabledLayers().Seq():
                if pcbnew.IsCopperLayer(l): hit[0].SetWidth(l, F(rz["d"]))
            hit[0].SetDrill(F(rz["drill"])); n["resized"] += 1
    for sp, a in loaded:
        for tr in a.get("tracks", []):
            for p, q in zip(tr["pts"], tr["pts"][1:]):
                t = pcbnew.PCB_TRACK(b)
                t.SetStart(pcbnew.VECTOR2I(F(p[0]), F(p[1]))); t.SetEnd(pcbnew.VECTOR2I(F(q[0]), F(q[1])))
                t.SetWidth(F(tr["w"])); t.SetLayer(lid[tr["layer"]]); t.SetNet(nets[tr["net"]]); t.SetLocked(bool(tr.get("lock"))); b.Add(t)
                n["tracks"] += 1
        for v in a.get("vias", []):
            via = pcbnew.PCB_VIA(b)
            via.SetPosition(pcbnew.VECTOR2I(F(v["x"]), F(v["y"])))
            via.SetWidth(pcbnew.F_Cu, F(v.get("d", 0.45))); via.SetDrill(F(v.get("drill", 0.25)))
            via.SetNet(nets[v["net"]]); via.SetLocked(bool(v.get("lock"))); b.Add(via); n["vias"] += 1
    doomed = set()
    for sp, a in loaded:
        for dl in a.get("delete", []):
            hit = []
            for k, (t, isvia, P1, P2, net, layer) in enumerate(items):
                if k in doomed or ("net" in dl and dl["net"] != net): continue
                if "seg" in dl and not isvia and dl.get("layer", layer) == layer:
                    q1, q2 = tuple(dl["seg"][:2]), tuple(dl["seg"][2:])
                    if (math.dist(P1, q1) < 0.006 and math.dist(P2, q2) < 0.006) or (math.dist(P1, q2) < 0.006 and math.dist(P2, q1) < 0.006): hit.append(k)
                elif "via" in dl and isvia and math.dist(P1, tuple(dl["via"])) < 0.006: hit.append(k)
            if not hit or (len(hit) > 1 and not dl.get("all")): sys.exit(f"{sp}: delete {dl} matched {len(hit)}")
            doomed.update(hit)
    for k in doomed: b.Remove(items[k][0])
    n["deleted"] = len(doomed)
    b.Save(out); print(n)


if __name__ == "__main__":
    main()
