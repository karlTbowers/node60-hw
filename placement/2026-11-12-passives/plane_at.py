"""Which zone net fills each copper layer at each pad of each 2-pad part, and on a 1 mm grid (read-only).
usage: $KPY plane_at.py board.kicad_pcb out.json"""
import sys, json, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM; MM = pcbnew.FromMM
layers = [l for l in b.GetEnabledLayers().CuStack()]
zones = [z for z in b.Zones() if not z.GetIsRuleArea()]
fills = {}
for l in layers:
    fills[l] = [(z.GetNetname(), z.GetFilledPolysList(l)) for z in zones if z.IsOnLayer(l)]
def at(x, y, l, acc=0):
    p = pcbnew.VECTOR2I(MM(x), MM(y))
    for net, poly in fills[l]:
        if poly.Contains(p, -1, MM(acc)):
            return net
    return ""
out = {"layers": [b.GetLayerName(l) for l in layers], "pads": {}, "grid": {}}
for f in b.GetFootprints():
    for pd in f.Pads():
        x, y = mm(pd.GetPosition().x), mm(pd.GetPosition().y)
        out["pads"][f.GetReference() + "." + pd.GetNumber()] = [at(x, y, l, 0.3) for l in layers]
x0, y0, x1, y1 = 40, 30, 270, 140
for l in layers:
    rows = []
    nets = {}
    for j in range(y0, y1):
        row = []
        for i in range(x0, x1):
            n = at(i + 0.5, j + 0.5, l)
            row.append(nets.setdefault(n, len(nets)))
        rows.append(row)
    out["grid"][b.GetLayerName(l)] = {"nets": list(nets), "rows": rows}
json.dump(out, open(sys.argv[2], "w"))
