#!/usr/bin/env python3
"""Bring every schematic part that isn't on the PCB yet onto it, in piles beside the outline.

The enclosure-fixed connectors (J901-J912) are placed by place_connectors.py; this adds
everything else, unlocked, south of the board's front edge, one pile per schematic sheet
(in sheet order), ready for placement. Parts already on the board are left alone, and
parts with no footprint in the schematic are listed and skipped.

Run with KiCad's own Python (it provides the pcbnew module):

    kicad-cli sch export netlist --format kicadsexpr -o /tmp/node60.net node60.kicad_sch
    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
        scripts/import_footprints.py /tmp/node60.net

Close the PCB editor first. Footprints get the schematic symbol path, so a later Update PCB
from Schematic (F8) links to them.
"""
import sys

import pcbnew

from place_connectors import CURRENT, LIB, PCB, VERSIONS, child, front, left, parse_sexpr

PILE_GAP = 40.0      # front edge to the first pile row (clear of the AT13 plugs)
SHEET_GAP = 10.0     # between sheet piles
PART_GAP = 1.0       # between parts in a pile
PILE_W = 60.0        # pile width before it wraps to a new row


def read_netlist(path):
    root = parse_sexpr(open(path, encoding="utf-8").read())
    comps, nets = {}, {}
    for comp in child(root, "components")[1:]:
        sheet = child(comp, "sheetpath")
        props = {}
        for p in comp[1:]:
            if isinstance(p, list) and p[0] == "property" and child(p, "value"):
                props[child(p, "name")[1]] = child(p, "value")[1]
        fp = child(comp, "footprint")
        comps[child(comp, "ref")[1]] = dict(
            value=child(comp, "value")[1],
            footprint=fp[1] if fp else "",
            path=child(sheet, "tstamps")[1] + child(comp, "tstamps")[1],
            sheet=child(sheet, "names")[1],
            sheetname=props.get("Sheetname", ""),
            sheetfile=props.get("Sheetfile", ""))
    for net in child(root, "nets")[1:]:
        name = child(net, "name")[1]
        for node in net[1:]:
            if isinstance(node, list) and node[0] == "node":
                nets[(child(node, "ref")[1], child(node, "pin")[1])] = name
    return comps, nets


def ref_key(ref):
    i = len(ref.rstrip("0123456789"))
    return ref[:i], int(ref[i:] or 0)


def main(netlist):
    comps, pin_nets = read_netlist(netlist)
    board = pcbnew.LoadBoard(PCB)
    on_board = {fp.GetReference() for fp in board.GetFootprints()}
    todo = {r: c for r, c in comps.items() if r not in on_board and c["footprint"]}
    skipped = sorted(r for r, c in comps.items() if r not in on_board and not c["footprint"])

    netinfo = {}
    for name in sorted(set(pin_nets.values())):
        ni = board.FindNet(name)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(board, name)
            board.Add(ni)
        netinfo[name] = ni

    v = VERSIONS[CURRENT]
    x_start, y = left(v), front(v) + PILE_GAP
    # Sheets in page order: the first part's reference number gives the page (R201 is page 2).
    by_sheet = {}
    for ref in sorted(todo, key=lambda r: (ref_key(r)[1] // 100, ref_key(r))):
        by_sheet.setdefault(todo[ref]["sheet"], []).append(ref)

    x0 = x_start
    for sheet, refs in by_sheet.items():
        x, row_y, row_h, pile_h = x0, y, 0.0, 0.0
        for ref in refs:
            c = todo[ref]
            lib, name = c["footprint"].split(":", 1)
            fp = pcbnew.FootprintLoad(f"{LIB}/{lib}.pretty", name)
            if fp is None:
                sys.exit(f"{ref}: footprint {c['footprint']} not found in {LIB}")
            fp.SetFPID(pcbnew.LIB_ID(lib, name))
            fp.SetReference(ref)
            fp.SetValue(c["value"])
            fp.SetPath(pcbnew.KIID_PATH(c["path"].rstrip("/")))
            fp.SetSheetname(c["sheetname"])
            fp.SetSheetfile(c["sheetfile"])
            board.Add(fp)
            for pad in fp.Pads():
                net = pin_nets.get((ref, pad.GetNumber()))
                if net:
                    pad.SetNet(netinfo[net])
            bb = fp.GetBoundingBox(False)
            w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
            if x > x0 and x + w > x0 + PILE_W:
                x, row_y, row_h = x0, row_y + row_h + PART_GAP, 0.0
            # Put the bounding box's top-left corner at (x, row_y).
            off = fp.GetPosition() - bb.GetOrigin()
            fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(row_y)) + off)
            x += w + PART_GAP
            row_h = max(row_h, h)
            pile_h = row_y + row_h - y
        print(f"{sheet}: {len(refs)} parts, pile {PILE_W:g} x {pile_h:.1f} mm at x {x0:.1f}")
        x0 += PILE_W + SHEET_GAP

    board.Save(PCB)
    print(f"added {len(todo)} footprints; no footprint in the schematic: {', '.join(skipped) or 'none'}")


if __name__ == "__main__":
    main(sys.argv[1])
