#!/usr/bin/env python3
"""Turn the three output switches 180 degrees with their pin-local parts (D30 D work-up, 2026-11-05).

    $KPY turn_cells.py BOARD SPEC.json OUT_BOARD OUT_SPEC.json [--keep-nets]

--keep-nets (D31 as landed): the schematic already swaps each switch's channels (output-switch sheet,
OUT_A/OUT_B), and apply_netlist.py has given the pads their nets, so the connectors, pours and via
fields keep their OUT numbers; only the geometry turns.

Each switch (U601/U701/U801) turns 180 degrees about its centre, so its logic pins (1-5, 12-16) face
north and its OUT pins (6-11) face south, over the column heads. Its pin-local parts turn with it
about the same centre: CVBB1 (Cx01, over the VBB pad on F.Cu), the VDD decap, CSNS, the two output
caps and R x01-x06. These stay where they are: the NTC group (Cx07, Rx07, RTx01) north of the chip,
the VBB bulk cap Cx02 south of it (between the new OUT blocks), and the parked test points. The
second output's cap Cx06 goes to the mirror image of Cx05's new place, beside its own pins.

Turned, each switch's first channel is on the east and its second on the west, so each cell's two
connectors swap channels: J904 takes OUT2 and J905 OUT1, J906 OUT4 and J907 OUT3, J908 OUT6 and J909
OUT5. On this copy that is done on the connectors' pads (schematic parity will flag it until the
schematic says the same).

The spec's output pours and via fields mirror about y = 111.6 (the chips' centre line): the B.Cu
blocks from y 104.5-111 to 112.2-118.7, the F.Cu strips from 109.25-111 to 112.2-113.95, and each
pair's west and east swap nets. The columns to the connectors stay. Joins whose parts moved (pad 17
to Cx01, OUT pad 11 to Cx06, the pocket 3V3 feeds of D29) leave the spec, to be planned again.
"""
import json
import sys

import pcbnew

board, spec_in, board_out, spec_out = sys.argv[1:5]
KEEP = "--keep-nets" in sys.argv
CELLS = {"U601": "6", "U701": "7", "U801": "8"}
TURN = ["C{}01", "C{}03", "C{}04", "C{}05", "C{}06", "R{}01", "R{}02", "R{}03", "R{}04", "R{}05", "R{}06"]
SWAP = [("J904", "J905"), ("J906", "J907"), ("J908", "J909")]
YC = 111.6

b = pcbnew.LoadBoard(board)
for u, k in CELLS.items():
    fu = b.FindFootprintByReference(u)
    c = fu.GetPosition()
    for ref in [u] + [t.format(k) for t in TURN]:
        f = b.FindFootprintByReference(ref)
        p = f.GetPosition()
        f.SetPosition(pcbnew.VECTOR2I(2 * c.x - p.x, 2 * c.y - p.y))
        f.SetOrientationDegrees((f.GetOrientationDegrees() + 180) % 360)
# the second output's cap sits at its own pins: the mirror image of the first's about the chip's centre line
for u, k in CELLS.items():
    c = b.FindFootprintByReference(u).GetPosition()
    f5, f6 = b.FindFootprintByReference(f"C{k}05"), b.FindFootprintByReference(f"C{k}06")
    p5 = f5.GetPosition()
    f6.SetPosition(pcbnew.VECTOR2I(2 * c.x - p5.x, p5.y))
    f6.SetOrientationDegrees((f5.GetOrientationDegrees() + 180) % 360)
for a, z in ([] if KEEP else SWAP):
    fa, fz = b.FindFootprintByReference(a), b.FindFootprintByReference(z)
    na = {p.GetNumber(): p.GetNet() for p in fa.Pads()}
    nz = {p.GetNumber(): p.GetNet() for p in fz.Pads()}
    for p in fa.Pads():
        if p.GetNumber() in nz and "OUT" in nz[p.GetNumber()].GetNetname():
            p.SetNet(nz[p.GetNumber()])
    for p in fz.Pads():
        if p.GetNumber() in na and "OUT" in na[p.GetNumber()].GetNetname():
            p.SetNet(na[p.GetNumber()])
# the cells' copper is the old orientation's: clear it, draw_power.py lays the fields and joins again
n = 0
for t in list(b.GetTracks()):
    for u in CELLS:
        c = b.FindFootprintByReference(u).GetPosition()
        cx = c.x / 1e6
        pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
        if all(cx - 22.4 <= q.x / 1e6 <= cx + 22.4 and 103.5 <= q.y / 1e6 <= 127.5 for q in pts):
            b.Remove(t); n += 1
            break
print(f"{n} tracks and vias cleared in the three cells")
b.Save(board_out)

d = json.load(open(spec_in))


def mirror_y(v):
    return round(2 * YC - v, 3)


out_b = {}
for z in d["zones"]:
    if z["name"].startswith("PWR_OUT") and z.get("poly"):
        p = z["poly"]
        xs = sorted({x for x, y in p})
        col = sorted({x for x, y in p if y == 127.0})          # the column's x range
        blk = [x for x in xs if x not in col]                   # the block's far edge
        cx0, cx1 = col
        far = blk[0]
        west = far > cx1                                        # column west of the block
        if "_B" in z["name"]:
            y0, y1 = 112.2, 118.7
            if west:
                poly = [[far, y0], [cx1, y0], [cx1, 108.9], [cx0, 108.9], [cx0, 127.0], [cx1, 127.0], [cx1, y1], [far, y1]]
            else:
                poly = [[far, y0], [cx0, y0], [cx0, 108.9], [cx1, 108.9], [cx1, 127.0], [cx0, 127.0], [cx0, y1], [far, y1]]
        else:
            y0, y1 = 112.2, 113.95
            if west:
                poly = [[far, y1], [cx1, y1], [cx1, 127.0], [cx0, 127.0], [cx0, 109.25], [cx1, 109.25], [cx1, y0], [far, y0]]
            else:
                poly = [[far, y1], [cx0, y1], [cx0, 127.0], [cx1, 127.0], [cx1, 109.25], [cx0, 109.25], [cx0, y0], [far, y0]]
        z["poly"] = poly
        z["why"] = "D30 D work-up: switch turned 180 degrees, block at the chip's south end (OUT pins), the column unchanged"
# each pair's nets swap: the west column now carries the switch's second channel
pairs = {"/OUT1": "/OUT2", "/OUT2": "/OUT1", "/OUT3": "/OUT4", "/OUT4": "/OUT3", "/OUT5": "/OUT6", "/OUT6": "/OUT5"}
for z in d["zones"]:
    if z["name"].startswith("PWR_OUT") and not KEEP:
        z["net"] = pairs[z["net"]]
for v in d["vias"]:
    if v["name"].startswith("OUT strips"):
        r = v["rect"]; v["rect"] = [r[0], mirror_y(r[3]), r[2], mirror_y(r[1])]
        v["toward"] = [[x, mirror_y(y)] for x, y in v["toward"]]
    if v["name"].startswith(("OUT strips", "OUT bands")) and not KEEP:
        v["net"] = pairs[v["net"]]
        for cp in v["copies"]:
            cp["net"], cp["mirror_net"] = pairs[cp["net"]], pairs[cp["mirror_net"]]
DROP = ["U601.17 to C601", "U701.17 to C701", "U801.17 to C801", "U601.11 to C606", "U701.11 to C706", "U801.11 to C806",
        "R601 (pocket", "R701 (pocket", "R801 (pocket"]
for k in ("stubs", "points"):
    before = len(d[k])
    d[k] = [s for s in d[k] if not any(x in s["name"] for x in DROP)]
    print(f"{k}: {before - len(d[k])} entries dropped (their parts moved)")
json.dump(d, open(spec_out, "w"), indent=1)
print(board_out, spec_out)
