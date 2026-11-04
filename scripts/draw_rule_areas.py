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
"""
import sys

import pcbnew

AREAS = {
    # name: (ref, margin mm, layers)
    "ESCAPE_U401": ("U401", 1.0, ("F.Cu", "B.Cu")),
    "ESCAPE_U501": ("U501", 1.0, ("F.Cu", "B.Cu")),
    "UNDER_Y401": ("Y401", 0.5, ("B.Cu", "In4.Cu")),
    "UNDER_Y501": ("Y501", 0.5, ("B.Cu", "In4.Cu")),
}


def main(path):
    board = pcbnew.LoadBoard(path)
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for z in list(board.Zones()):
        if z.GetIsRuleArea() and z.GetZoneName() in AREAS:
            board.Delete(z)
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
    main(sys.argv[1] if len(sys.argv) > 1 else "node60.kicad_pcb")
