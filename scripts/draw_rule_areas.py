#!/usr/bin/env python3
"""Draw the named rule areas that node60.kicad_dru's routing rules refer to (placement decision D12).

Run with KiCad's Python from the repo root, after placement moves any part named below:

    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
        scripts/draw_rule_areas.py node60.kicad_pcb
    git checkout -- node60.kicad_pro       # pcbnew's save rewrites it; check the diff first

Each area is the part's courtyard bounding box grown by a margin, on the layers given. The areas
forbid nothing themselves (every keep-out flag off): `A.intersectsArea('<name>')` in
node60.kicad_dru does the work, and a rule naming an area that doesn't exist silently never
matches, so the names here and there must agree. Existing areas of the same name are replaced;
the busbar areas (BUSBAR_*) belong to place_connectors.py and are left alone.

- ESCAPE_U401, ESCAPE_U501: where tracks may neck below 0.15 mm (JLCPCB's 0.09/0.09 mm on the
  1 oz outer layers) to escape the BGA and the PHY's QFN. 1 mm past the courtyard.
- UNDER_Y401, UNDER_Y501: under the MCU crystal and the PHY's oscillator only their own nets and
  GND, on the part's layer and the GND plane next to it (In4). Their courtyard, 0.5 mm grown.

Plane layers and signal windows (placement decision D17): `--window LAYER:X0,Y0,X1,Y1` (repeatable)
opens a rectangle of a plane layer to signal tracks: SIGNAL_WINDOW_<layer>_<n> keeps the plane's
pour out of it (zone fill not allowed), and POWER_ONLY_<layer>_<n> keep-outs cover the rest of
that layer with tracks not allowed (vias allowed: every via is through-hole, so signal vias must
pass the planes). `--power-only LAYER` (repeatable) covers a whole plane layer with such a keep-out.
Window and keep-out areas are redrawn on every run; the plan's windows are the source.
"""
import argparse
import sys

import pcbnew

AREAS = {
    # name: (ref, margin mm, layers)
    "ESCAPE_U401": ("U401", 1.0, ("F.Cu", "B.Cu")),
    "ESCAPE_U501": ("U501", 1.0, ("F.Cu", "B.Cu")),
    "UNDER_Y401": ("Y401", 0.5, ("B.Cu", "In4.Cu")),
    "UNDER_Y501": ("Y501", 0.5, ("B.Cu", "In4.Cu")),
}


def rule_area(board, name, layers, box, no_tracks=False, no_fill=False):
    mm = pcbnew.FromMM
    area = pcbnew.ZONE(board)
    area.SetZoneName(name)
    area.SetIsRuleArea(True)
    ls = pcbnew.LSET()
    for layer in layers:
        ls.AddLayer(board.GetLayerID(layer))
    area.SetLayerSet(ls)
    area.SetDoNotAllowTracks(no_tracks)
    area.SetDoNotAllowVias(False)
    area.SetDoNotAllowPads(False)
    area.SetDoNotAllowZoneFills(no_fill)
    area.SetDoNotAllowFootprints(False)
    o = area.Outline(); o.RemoveAllContours(); o.NewOutline()
    x0, y0, x1, y1 = box
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        o.Append(mm(x), mm(y))
    board.Add(area)


def complement(outer, hole):
    """outer rectangle minus an inner one, as up to four rectangles"""
    X0, Y0, X1, Y1 = outer; x0, y0, x1, y1 = (max(hole[0], X0), max(hole[1], Y0), min(hole[2], X1), min(hole[3], Y1))
    parts = [(X0, Y0, X1, y0), (X0, y1, X1, Y1), (X0, y0, x0, y1), (x1, y0, X1, y1)]
    return [p for p in parts if p[2] - p[0] > 0.01 and p[3] - p[1] > 0.01]


def main(path, windows=(), power_only=()):
    board = pcbnew.LoadBoard(path)
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for z in list(board.Zones()):
        if z.GetIsRuleArea() and (z.GetZoneName() in AREAS or z.GetZoneName().startswith(("SIGNAL_WINDOW_", "POWER_ONLY_"))):
            board.Delete(z)
    e = board.GetBoardEdgesBoundingBox()
    outer = (pcbnew.ToMM(e.GetLeft()), pcbnew.ToMM(e.GetTop()), pcbnew.ToMM(e.GetRight()), pcbnew.ToMM(e.GetBottom()))
    by_layer = {}
    for w in windows:
        layer, box = w.split(":"); by_layer.setdefault(layer, []).append(tuple(float(v) for v in box.split(",")))
    for layer, boxes in by_layer.items():
        if len(boxes) > 1:
            sys.exit(f"{layer}: one window per layer for now")
        tag = layer.replace(".", "")
        rule_area(board, f"SIGNAL_WINDOW_{tag}_1", [layer], boxes[0], no_fill=True)
        for k, part in enumerate(complement(outer, boxes[0]), 1):
            rule_area(board, f"POWER_ONLY_{tag}_{k}", [layer], part, no_tracks=True)
        print(f"{layer}: signal window x {boxes[0][0]:.2f}..{boxes[0][2]:.2f} y {boxes[0][1]:.2f}..{boxes[0][3]:.2f}; "
              f"the rest of the layer tracks not allowed (vias allowed)")
    for layer in power_only:
        rule_area(board, f"POWER_ONLY_{layer.replace('.', '')}_1", [layer], outer, no_tracks=True)
        print(f"{layer}: power only, tracks not allowed (vias allowed)")
    mm = pcbnew.FromMM
    for name, (ref, margin, layers) in AREAS.items():
        fp = fps[ref]
        bb = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd).BBox()
        x0, y0 = pcbnew.ToMM(bb.GetLeft()) - margin, pcbnew.ToMM(bb.GetTop()) - margin
        x1, y1 = pcbnew.ToMM(bb.GetRight()) + margin, pcbnew.ToMM(bb.GetBottom()) + margin
        area = pcbnew.ZONE(board)
        area.SetZoneName(name)
        area.SetIsRuleArea(True)
        ls = pcbnew.LSET()
        for layer in layers:
            ls.AddLayer(board.GetLayerID(layer))
        area.SetLayerSet(ls)
        for allow in (area.SetDoNotAllowTracks, area.SetDoNotAllowVias, area.SetDoNotAllowPads,
                      area.SetDoNotAllowZoneFills, area.SetDoNotAllowFootprints):
            allow(False)
        outline = area.Outline()
        outline.RemoveAllContours()
        outline.NewOutline()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            outline.Append(mm(x), mm(y))
        board.Add(area)
        print(f"{name}: {ref} courtyard + {margin} mm, x {x0:.2f}..{x1:.2f} y {y0:.2f}..{y1:.2f}, {'+'.join(layers)}")
    board.Save(path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board", nargs="?", default="node60.kicad_pcb")
    ap.add_argument("--window", action="append", default=[], metavar="LAYER:X0,Y0,X1,Y1")
    ap.add_argument("--power-only", action="append", default=[], metavar="LAYER")
    a = ap.parse_args()
    main(a.board, a.window, a.power_only)
