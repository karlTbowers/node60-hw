#!/usr/bin/env python3
"""Place Node60's enclosure-fixed connectors (J901-J912) and the board outline.

Run with KiCad's own Python (it provides the pcbnew module):

    kicad-cli sch export netlist --format kicadsexpr -o /tmp/node60.net node60.kicad_sch
    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
        scripts/place_connectors.py /tmp/node60.net

Close the PCB editor first. The script replaces any J901-J912 footprints and
the Edge.Cuts outline; every other item on the board is left alone. Footprints
get the schematic symbol path, so a later Update PCB from Schematic (F8)
links to them and keeps their positions.

The board mounts component side (F.Cu) up, facing the lid (DEC-021), so
KiCad's top view is the view from above the lid. Enclosure faces -> board edges:
  front face  (J904-J909, AT13 outputs)     -> bottom edge, J904 at the left
  north face  (J903, J912, T1S)             -> top edge, middle; J903 on the
              left as seen from outside the north wall (east, larger x)
  lid         (J901/J910 battery, J902/J911 return) -> REDCUBE 74660016R on
              B.Cu. Each pair is joined by a copper busbar on top of the board;
              the SurLok studs come down through the busbar into the terminals.

The busbar outlines are drawn on User.Drawings: keep components out from under
them. The outline is PROVISIONAL until the enclosure is chosen.
"""
import sys

try:
    import pcbnew  # KiCad's Python; not needed to import the positions
except ImportError:
    pcbnew = None

PCB = "node60.kicad_pcb"
LIB = "lib/dropout-kicad-library/footprints"

# Board outline (mm). Origin = top-left (back-left) corner.
X0, Y0 = 30.0, 30.0
W, D = 250.0, 160.0
FRONT = Y0 + D
LEFT, RIGHT = X0, X0 + W
THICKNESS = 2.6      # mm, DEC-020: the REDCUBE's 2.6 mm spigot ends flush with the top face

# Board edge sits this far behind each connector's flange (panel) face, so the
# flange, not the board, meets the wall.
EDGE_GAP = 0.5
AT13_PANEL = 15.5    # pin row to flange face, footprint local +y
ATM13_PANEL = 16.5
AT13_CY_X = 2.7      # courtyard centre relative to pin 1 along the pin row
ATM13_CY_X = 2.1

OUT_PITCH = 40.0     # 36.2 mm courtyard + 3.8 mm between headers (user, 2026-10-30)
T1S_PITCH = 45.0     # J903 / J912 on the north edge: 36.8 mm seal areas, ~8 mm apart (DEC-021)

# Lid terminal axes (KiCad X, Y), in the two low sections either side of the lid's
# raised T (DEC-021): one battery/return pair each side. The battery row sits far
# enough south that a battery plug pointing north clears the return receptacle; the
# return row far enough south that its busbar clears the T1S headers.
CX = X0 + W / 2
LID_TERMINALS = {
    "J910": (CX - 70, FRONT - 45),   # battery, west
    "J901": (CX + 70, FRONT - 45),   # battery, east
    "J911": (CX - 70, FRONT - 115),  # return, west
    "J902": (CX + 70, FRONT - 115),  # return, east
}

# Busbars on top of the board (DEC-021): 1/8" x 1" C110 copper flat bar, cut to length
# and drilled in house, one per terminal pair. Ends run half a width past each hole.
BUSBAR_W, BUSBAR_T = 25.4, 3.175
BUSBAR_HOLE = 6.5    # M6 clearance
BUSBARS = {"VBAT_IN": ("J910", "J901"), "GND": ("J911", "J902")}


def busbar_outline(net):
    """(x0, y0, x1, y1) of a busbar in KiCad mm; both terminals sit on one row."""
    (xa, ya), (xb, yb) = (LID_TERMINALS[r] for r in BUSBARS[net])
    h = BUSBAR_W / 2
    return min(xa, xb) - h, ya - h, max(xa, xb) + h, ya + h

AT13 = ("DropOut_Connector_Amphenol", "Amphenol_AT13-2P-BMxx_1x02_P5.40mm_Horizontal")
ATM13 = ("DropOut_Connector_Amphenol", "Amphenol_ATM13-2P-BMxx_1x02_P4.20mm_Horizontal")
REDCUBE = ("DropOut_TerminalBlock_Wuerth", "Wuerth_REDCUBE-SMT_WP-SMRT_74660016")


def placements():
    """ref -> (lib, footprint, x, y, rotation_deg, bottom_side)"""
    p = {}
    row_y = FRONT - (AT13_PANEL - EDGE_GAP)
    for i in range(6):
        cx = X0 + W / 2 + (i - 2.5) * OUT_PITCH
        p[f"J{904 + i}"] = (*AT13, cx - AT13_CY_X, row_y, 0, False)
    # rotation 180: shroud (local +y) points north (-y), local +x points west (-x)
    north_row = Y0 + (ATM13_PANEL - EDGE_GAP)
    p["J903"] = (*ATM13, CX + T1S_PITCH / 2 + ATM13_CY_X, north_row, 180, False)
    p["J912"] = (*ATM13, CX - T1S_PITCH / 2 + ATM13_CY_X, north_row, 180, False)
    # Lid terminals: REDCUBE on B.Cu, thread opening up through the board. Each
    # SurLok right-angle plug can point outward (west or east) or north
    # (scripts/check_surlok_clearance.py).
    for ref, (x, y) in LID_TERMINALS.items():
        p[ref] = (*REDCUBE, x, y, 0, True)
    return p


def parse_sexpr(text):
    stack, cur, i, n = [], [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "(":
            stack.append(cur); cur = []; i += 1
        elif c == ")":
            done = cur; cur = stack.pop(); cur.append(done); i += 1
        elif c == '"':
            j = i + 1; buf = []
            while text[j] != '"':
                if text[j] == "\\":
                    j += 1
                buf.append(text[j]); j += 1
            cur.append("".join(buf)); i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()':
                j += 1
            cur.append(text[i:j]); i = j
    return cur[0]


def child(node, key):
    for c in node[1:]:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def read_netlist(path, refs):
    root = parse_sexpr(open(path, encoding="utf-8").read())
    comps, nets = {}, {}
    for comp in child(root, "components")[1:]:
        ref = child(comp, "ref")[1]
        if ref not in refs:
            continue
        sheet = child(comp, "sheetpath")
        props = {child(p, "name")[1]: child(p, "value")[1]
                 for p in comp[1:] if isinstance(p, list) and p[0] == "property"}
        comps[ref] = dict(value=child(comp, "value")[1],
                          footprint=child(comp, "footprint")[1],
                          path=child(sheet, "tstamps")[1] + child(comp, "tstamps")[1],
                          sheetname=props.get("Sheetname", ""),
                          sheetfile=props.get("Sheetfile", ""))
    for net in child(root, "nets")[1:]:
        name = child(net, "name")[1]
        for node in net[1:]:
            if isinstance(node, list) and node[0] == "node":
                ref, pin = child(node, "ref")[1], child(node, "pin")[1]
                if ref in refs:
                    nets[(ref, pin)] = name
    return comps, nets


def main(netlist):
    place = placements()
    comps, pin_nets = read_netlist(netlist, set(place))
    missing = set(place) - set(comps)
    if missing:
        sys.exit(f"not in the netlist: {sorted(missing)}")
    for ref, (lib, name, *_rest) in place.items():
        if comps[ref]["footprint"] != f"{lib}:{name}":
            sys.exit(f"{ref}: schematic footprint {comps[ref]['footprint']} != {lib}:{name}")

    # Load the library footprints before the board, and move footprints that
    # are already on the board instead of removing them: in KiCad 10's
    # bindings, board.Remove() on a footprint breaks later calls.
    fps = {ref: pcbnew.FootprintLoad(f"{LIB}/{lib}.pretty", name)
           for ref, (lib, name, *_rest) in place.items()}

    board = pcbnew.LoadBoard(PCB)
    existing = {fp.GetReference(): fp for fp in board.GetFootprints()
                if fp.GetReference() in place}
    # board.GetDrawings() isn't iterable in KiCad 10's bindings
    board.RemoveAllItemsOnLayer(pcbnew.Edge_Cuts)
    board.RemoveAllItemsOnLayer(pcbnew.Dwgs_User)     # busbar outlines, redrawn below
    board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(THICKNESS))

    netinfo = {}
    for name in sorted(set(pin_nets.values())):
        ni = board.FindNet(name)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(board, name)
            board.Add(ni)
        netinfo[name] = ni

    for ref, (lib, name, x, y, rot, bottom) in sorted(place.items()):
        c = comps[ref]
        fp = existing.get(ref)
        if fp is None:
            fp = fps[ref]
            fp.SetFPID(pcbnew.LIB_ID(lib, name))
            fp.SetReference(ref)
            fp.SetValue(c["value"])
            fp.SetPath(pcbnew.KIID_PATH(c["path"].rstrip("/")))
            fp.SetSheetname(c["sheetname"])
            fp.SetSheetfile(c["sheetfile"])
            board.Add(fp)
        elif fp.IsFlipped():
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        pos = pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
        fp.SetPosition(pos)
        fp.SetOrientationDegrees(rot)
        if bottom:
            fp.Flip(pos, pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        for pad in fp.Pads():
            net = pin_nets.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(netinfo[net])
        fp.SetLocked(True)

    outline = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECT)
    outline.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(X0), pcbnew.FromMM(Y0)))
    outline.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(RIGHT), pcbnew.FromMM(FRONT)))
    outline.SetLayer(pcbnew.Edge_Cuts)
    outline.SetWidth(pcbnew.FromMM(0.1))
    board.Add(outline)

    mm = lambda v: pcbnew.FromMM(v)
    for net in BUSBARS:
        x0, y0, x1, y1 = busbar_outline(net)
        bar = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECT)
        bar.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
        bar.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        bar.SetLayer(pcbnew.Dwgs_User)
        bar.SetWidth(mm(0.15))
        board.Add(bar)
        label = pcbnew.PCB_TEXT(board)
        label.SetText(f"{net} busbar {BUSBAR_W:g} x {BUSBAR_T:g} Cu (1/8 x 1 in C110), on top: no parts under it")
        label.SetPosition(pcbnew.VECTOR2I(mm((x0 + x1) / 2), mm(y0 - 2)))
        label.SetLayer(pcbnew.Dwgs_User)
        label.SetTextSize(pcbnew.VECTOR2I(mm(1.5), mm(1.5)))
        board.Add(label)

    board.Save(PCB)
    for ref in sorted(place):
        fp = board.FindFootprintByReference(ref)
        bb = fp.GetCourtyard(fp.GetLayer()).BBox() if fp.GetCourtyard(fp.GetLayer()).OutlineCount() else fp.GetBoundingBox()
        print(f"{ref} {fp.GetLayerName():5} {pcbnew.ToMM(fp.GetPosition().x):7.2f} {pcbnew.ToMM(fp.GetPosition().y):7.2f} "
              f"rot {fp.GetOrientationDegrees():6.1f}  courtyard x {pcbnew.ToMM(bb.GetLeft()):.1f}..{pcbnew.ToMM(bb.GetRight()):.1f} "
              f"y {pcbnew.ToMM(bb.GetTop()):.1f}..{pcbnew.ToMM(bb.GetBottom()):.1f}  "
              + " ".join(f"{p.GetNumber()}={p.GetNetname()}" for p in fp.Pads() if p.GetNumber()))


if __name__ == "__main__":
    main(sys.argv[1])
