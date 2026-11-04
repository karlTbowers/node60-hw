#!/usr/bin/env python3
"""Add the footprints the schematic has and the board lacks, with their nets: Update PCB from Schematic's
"add" step, without the GUI. Existing footprints, tracks and zones are not touched.

Run with KiCad's own Python (it provides the pcbnew module) from the repo root:

    kicad-cli sch export netlist --format kicadsexpr -o /tmp/node60.net node60.kicad_sch
    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
        scripts/add_missing_footprints.py /tmp/node60.net C207=130,40,0,F L201=108.7,43.7,90,B
    python3 ... scripts/sync_footprint_fields.py .     # the symbols' fields and DNP flags
    git checkout -- node60.kicad_pro                   # pcbnew's save rewrites it

Each REF=X,Y,ROT,SIDE places a new footprint (mm, degrees, F or B); a missing part not named is
placed off the board's north-east corner for placement to move. Footprints load from the project's
fp-lib-table (`${KIPRJMOD}` = the repo root). Each is linked to its symbol by the netlist's sheet and
symbol stamps, so schematic parity matches them, and each pad gets the net the netlist gives it.
Unconnected pins' nets ("unconnected-(...)") are created as KiCad names them.
"""
import os
import re
import sys

import pcbnew

ROOT = os.path.abspath('.')


def netlist(path):
    s = open(path).read()
    comps = {}
    for blk in s.split('\n\t\t(comp\n')[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', blk).group(1)
        fp = re.search(r'\(footprint "([^"]*)"\)', blk)
        stamps = re.findall(r'\(tstamps "([^"]+)"\)', blk)
        comps[ref] = {'footprint': fp.group(1) if fp else '',
                      'value': re.search(r'\(value "([^"]*)"\)', blk).group(1),
                      'path': stamps[0] + stamps[1] if len(stamps) >= 2 else None}
    pins = {}
    for blk in s.split('\n\t\t(net\n')[1:]:
        name = re.search(r'\(name "([^"]+)"\)', blk).group(1)
        for r, p in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk):
            pins[(r, p)] = name
    return comps, pins


def libs():
    t = open(os.path.join(ROOT, 'fp-lib-table')).read()
    return {n: u.replace('${KIPRJMOD}', ROOT) for n, u in re.findall(r'\(name "([^"]+)"\)\(type "[^"]+"\)\(uri "([^"]+)"\)', t)}


def main():
    comps, pins = netlist(sys.argv[1])
    poses = {}
    for arg in sys.argv[2:]:
        ref, v = arg.split('=')
        x, y, rot, side = v.split(',')
        poses[ref] = (float(x), float(y), float(rot), side.upper())
    board_path = os.path.join(ROOT, 'node60.kicad_pcb')
    # which refs the board has, read as text: pcbnew's wrappers go bad if footprints are loaded
    # from a library after a board is open, so the library footprints load first
    have = set(re.findall(r'\(property "Reference" "([^"]+)"', open(board_path).read()))
    missing = [r for r, c in comps.items() if r not in have and c['footprint'] and not r.startswith('#')]
    table = libs()
    loaded = {}
    for r in missing:
        lib, name = comps[r]['footprint'].split(':', 1)
        loaded[r] = pcbnew.FootprintLoad(table[lib], name)
        loaded[r].SetFPID(pcbnew.LIB_ID(lib, name))
    b = pcbnew.LoadBoard(board_path)
    o = b.GetBoardEdgesBoundingBox()
    park = [pcbnew.ToMM(o.GetRight()) + 10, pcbnew.ToMM(o.GetTop())]
    for r in missing:
        fp = loaded[r]
        fp.SetReference(r)
        fp.SetValue(comps[r]['value'])
        if comps[r]['path']:
            fp.SetPath(pcbnew.KIID_PATH(comps[r]['path']))
        b.Add(fp)
        x, y, rot, side = poses.get(r, (park[0], park[1], 0, 'B'))
        if r not in poses:
            park[1] += 10
        if side == 'B':
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            name = pins.get((r, pad.GetNumber()))
            if name:
                net = b.FindNet(name)
                if net is None:
                    net = pcbnew.NETINFO_ITEM(b, name)
                    b.Add(net)
                pad.SetNet(net)
        print(f'{r}: {comps[r]["footprint"]} at ({x}, {y}, {rot}, {side}); pads: '
              + ', '.join(f'{p.GetNumber()}={p.GetNetname()}' for p in fp.Pads()))
    b.Save(board_path)
    print(f'{len(missing)} footprint(s) added' if missing else 'nothing missing')


if __name__ == '__main__':
    main()
