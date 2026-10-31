#!/usr/bin/env python3
"""Node60's enclosure-fixed connectors (J901-J912), board outline and busbars, per design version.

Eight mechanical versions are kept as candidates (docs: Enclosure options). Each is a set
of parameters in VERSIONS; enclosure_geometry.py, check_surlok_clearance.py, the
dimensioned drawings and the 3D mockup are all generated from them. The PCB holds one:
CURRENT, unless another is named on the command line.

Run with KiCad's own Python (it provides the pcbnew module):

    kicad-cli sch export netlist --format kicadsexpr -o /tmp/node60.net node60.kicad_sch
    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
        scripts/place_connectors.py /tmp/node60.net [v2]

Close the PCB editor first. The script moves J901-J912, redraws the Edge.Cuts outline and
the busbar outlines (User.Drawings); every other item on the board is left alone.
Footprints get the schematic symbol path, so a later Update PCB from Schematic (F8) links
to them and keeps their positions. A version whose terminal footprint differs from the
schematic's (the press-fit versions) can't be placed until the schematic changes.

Positions are written in plan as seen from above the lid (x east, KiCad Y toward the
front face). A board mounted component side down (version 1) is mirrored in KiCad, whose
top view then looks at the board from below.
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
CX = X0 + W / 2
THICKNESS = 2.6      # mm (DEC-020): the SMT REDCUBE's 2.6 mm spigot ends flush with the far face

# Board edge sits this far behind each connector's flange (panel) face, so the
# flange, not the board, meets the wall.
EDGE_GAP = 0.5
AT13_PANEL = 15.5    # pin row to flange face, footprint local +y
ATM13_PANEL = 16.5
AT13_CY_X = 2.7      # courtyard centre relative to pin 1 along the pin row
ATM13_CY_X = 2.1
AT13_BACK = 6.6      # header body behind its pin row (courtyard)
ATM13_BACK = 10.85
ATM13_ALONG = (16.81, 21.01)   # ATM13 courtyard along its pin row, either side of pin 1
HEADER_CLEAR = 3.0

OUT_PITCH = 40.0     # 36.2 mm courtyard + 3.8 mm between headers (user, 2026-10-30)
OUT_ROW = FRONT - (AT13_PANEL - EDGE_GAP)          # AT13 pin row
T1S_PITCH = 45.0     # J903 / J912 side by side on the north edge (DEC-021 as accepted)
# Versions 2 and 4 (user, 2026-10-31): 41 mm, so the T stem is narrow enough for the
# receptacles beside it to stagger (_T_LAYOUT). 41.98 mm is the most that works. Version 7
# takes it too (user, 2026-10-31).
T1S_PITCH_T = 41.0
# T1S on the side walls: version 1 at 60 % of the depth from the front (DEC-020);
# version 3 as near the outputs as the AT13 bodies allow (user, 2026-10-30).
T1S_SIDE_MID = FRONT - 0.60 * D
T1S_SIDE_FRONT = OUT_ROW - AT13_BACK - HEADER_CLEAR - max(ATM13_ALONG)
# Version 6 (user, 2026-10-30): two outputs on each of the west, south and east walls. Each
# side wall has one in its back corner and one in its front corner, 20 mm from the board
# edge so the courtyard and panel seal clear the corner; the power receptacles sit between
# them, so an outward plug passes between the two headers' raised sections.
OUT_SIDE_BACK, OUT_SIDE_FRONT = Y0 + 20.0, FRONT - 20.0
# Version 6's board is shallower (user, 2026-10-31): 139 mm is about the least that keeps every
# plug check, set by the chain back-corner hood > return row > battery row (2 mm between the
# flanges; a battery plug pointing north stops short of the T1S hood) > front band. Its rows
# are measured from the north edge.
V6_DEPTH = 139.0
V6_FRONT = Y0 + V6_DEPTH

# Version 8 (user, 2026-10-31): a second board, for the microcontroller, under the main
# board; the T1S pair J903/J912 sits on it, in the same plan positions, and stands up
# through a notch in the main board's north edge. Outline PROVISIONAL (plan, KiCad Y).
MCU_BOARD = (CX - 60.0, Y0, CX + 60.0, Y0 + 80.0)
MCU_THICKNESS = 1.6
NOTCH_CLEAR = 1.0    # notch edge to the ATM13 courtyards
NOTCH = (CX - T1S_PITCH / 2 - sum(ATM13_ALONG) / 2 - NOTCH_CLEAR, Y0,
         CX + T1S_PITCH / 2 + sum(ATM13_ALONG) / 2 + NOTCH_CLEAR,
         Y0 + ATM13_PANEL - EDGE_GAP + ATM13_BACK + NOTCH_CLEAR)

# Busbars (DEC-021): 1/8" x 1" C110 copper flat bar, cut to length and drilled in house,
# one per terminal pair. Ends run half a width past each hole.
BUSBAR_W, BUSBAR_T = 25.4, 3.175
BUSBAR_HOLE = 6.5    # M6 clearance
BUSBARS = {"VBAT_IN": ("J910", "J901"), "GND": ("J911", "J902")}

AT13 = ("DropOut_Connector_Amphenol", "Amphenol_AT13-2P-BMxx_1x02_P5.40mm_Horizontal")
ATM13 = ("DropOut_Connector_Amphenol", "Amphenol_ATM13-2P-BMxx_1x02_P4.20mm_Horizontal")
REDCUBE = {"smt": ("DropOut_TerminalBlock_Wuerth", "Wuerth_REDCUBE-SMT_WP-SMRT_74660016"),
           "pressfit": ("DropOut_TerminalBlock_Wuerth", "Wuerth_REDCUBE-PRESS-FIT_WP-PFIFUA_786202106_PressFit")}

# Lid terminal layouts (plan, x east, KiCad Y).
_T_LAYOUT = {    # DEC-021: one battery/return pair in each low section beside the raised T. Battery
    "J910": (CX - 57.5, FRONT - 45), "J901": (CX + 57.5, FRONT - 45),   # close to the stem and in front,
    "J911": (CX - 78.7, FRONT - 115), "J902": (CX + 78.7, FRONT - 115)} # return wide, so a battery plug's
# cable pointing north passes beside the return receptacle (user, 2026-10-31).
_STAGGER = {     # version 3: behind the raised front band; battery close, return wide, so a
    "J910": (CX - 40, FRONT - 87), "J901": (CX + 40, FRONT - 87),     # battery plug pointing
    "J911": (CX - 75, FRONT - 120), "J902": (CX + 75, FRONT - 120)}   # north passes beside the return

_FRONT_OUTS = {f"J{904 + i}": ("S", CX + (i - 2.5) * OUT_PITCH) for i in range(6)}
_WALL_OUTS = {   # version 6: OUT1-2 west (north first), OUT3-4 south, OUT5-6 east (front first),
    "J904": ("W", OUT_SIDE_BACK), "J905": ("W", OUT_SIDE_FRONT),                      # going round
    "J906": ("S", CX - OUT_PITCH / 2), "J907": ("S", CX + OUT_PITCH / 2),           # the board
    "J908": ("E", OUT_SIDE_FRONT), "J909": ("E", OUT_SIDE_BACK)}
_WALL_OUTS_V6 = {**_WALL_OUTS, "J905": ("W", V6_FRONT - 20.0), "J908": ("E", V6_FRONT - 20.0)}
# Versions 6 to 8: battery close and in front, return wide, so a battery plug pointing north passes
# beside the return. Battery 52 mm from the centre line so its cable, pointing north, passes the
# T1S hood (user, 2026-10-31); return 26 mm further out.
BAT_X, RET_X = 52.0, 78.0
_MIDDLE = {"J910": (CX - BAT_X, FRONT - 58), "J901": (CX + BAT_X, FRONT - 58),
           "J911": (CX - RET_X, FRONT - 105), "J902": (CX + RET_X, FRONT - 105)}
_MIDDLE_V6 = {"J910": (CX - BAT_X, Y0 + 82), "J901": (CX + BAT_X, Y0 + 82),
              "J911": (CX - RET_X, Y0 + 53), "J902": (CX + RET_X, Y0 + 53)}

# board: "up" (component side faces the lid) or "down"; t1s: "north" or "sides" (y of the
# pair centre); lid: "flat", "T" (crossbar over the outputs, stem over a north T1S pair) or
# "front" (one raised band across the front; with a north T1S pair, a separate hood over
# it) or "corners" (a front band, a raised
# section in each back corner and one over a north T1S pair); outputs: wall ("S", "W", "E") and position along it (plan x
# on the south wall, KiCad Y on the side walls), default all six on the south wall;
# plugs: "WNE" (any of west, north, east) or "ON" (outward or north); depth: board depth
# (default D), the north edge stays at Y0; t1s_pitch: J903 to J912 (default T1S_PITCH); t1s_board: "main"
# (default) or "mcu" (on the board under the main board, through a notch in it).
VERSIONS = {
    "v1": dict(title="Version 1: board flipped", decision="DEC-020", board="down", terminal="smt", busbars=False,
               t1s="sides", t1s_y=T1S_SIDE_MID, lid="flat", plugs="WNE", back_gap=2.0,
               terminals={"J910": (CX - 48, FRONT - 65), "J901": (CX + 48, FRONT - 65),
                          "J911": (CX - 75, FRONT - 125), "J902": (CX + 75, FRONT - 125)},
               summary="Board component side down under a flat lid; the SurLok studs reach SMT REDCUBEs through "
                       "the board. T1S on the side walls. No busbars."),
    "v2": dict(title="Version 2: busbars, raised T", decision="DEC-021", board="up", terminal="smt", busbars=True,
               t1s="north", t1s_pitch=T1S_PITCH_T, lid="T", plugs="ON", back_gap=EDGE_GAP, terminals=_T_LAYOUT,
               summary="Board component side up; SMT REDCUBEs underneath, busbars on top; a raised T over the "
                       "outputs and the T1S pair on the north wall, 41 mm apart. The receptacles are staggered "
                       "so a battery plug's cable pointing north passes beside the return receptacle."),
    "v3": dict(title="Version 3: busbars, raised front", decision=None, board="up", terminal="smt", busbars=True,
               t1s="sides", t1s_y=T1S_SIDE_FRONT, lid="front", plugs="ON", back_gap=2.0, terminals=_STAGGER,
               summary="As version 2, but the T1S pair moves to the side walls next to the outputs, so one raised "
                       "band across the front covers every header; the power receptacles sit behind it, staggered."),
    "v4": dict(title="Version 4: press-fit, raised T", decision=None, board="up", terminal="pressfit", busbars=True,
               t1s="north", t1s_pitch=T1S_PITCH_T, lid="T", plugs="ON", back_gap=EDGE_GAP, terminals=_T_LAYOUT,
               summary="Version 2's layout with REDCUBE press-fit 786202106 terminals on top of the board and the "
                       "busbars on the terminal blocks."),
    "v5": dict(title="Version 5: press-fit, raised front", decision=None, board="up", terminal="pressfit", busbars=True,
               t1s="sides", t1s_y=T1S_SIDE_FRONT, lid="front", plugs="ON", back_gap=2.0, terminals=_STAGGER,
               summary="Version 3's layout with REDCUBE press-fit 786202106 terminals and the busbars on the "
                       "terminal blocks."),
    "v6": dict(title="Version 6: outputs on three walls", decision=None, board="up", terminal="smt", busbars=True,
               t1s="north", lid="corners", plugs="ON", back_gap=EDGE_GAP, depth=V6_DEPTH, outputs=_WALL_OUTS_V6,
               terminals=_MIDDLE_V6,
               summary="Version 2 with two outputs on each of the west, south and east walls, one in each corner "
                       "of the side walls, and the T1S pair on the north wall. A raised band across the front and "
                       "raised sections in the back corners and over the T1S pair; the power receptacles sit "
                       "between them, staggered. The board is 139 mm deep, 21 mm less than version 2."),
    "v7": dict(title="Version 7: busbars, front band and T1S hood", decision=None, board="up", terminal="smt",
               busbars=True, t1s="north", t1s_pitch=T1S_PITCH_T, lid="front", plugs="ON", back_gap=EDGE_GAP,
               terminals=_MIDDLE,
               summary="Version 2 without the T's stem: a raised band across the front over the outputs and a "
                       "separate raised hood over the T1S pair on the north wall; the rest of the lid is low. "
                       "The power receptacles are placed as in version 6, staggered."),
    "v8": dict(title="Version 8: MCU board below, T1S lowered", decision=None, board="up", terminal="smt",
               busbars=True, t1s="north", t1s_board="mcu", lid="front", plugs="ON", back_gap=EDGE_GAP,
               terminals=_MIDDLE,
               summary="Version 7 with a second board for the microcontroller under the main board. The T1S pair "
                       "moves onto it and stands up through a notch in the main board, low enough to fit under "
                       "the low lid, so the T1S hood goes; only the front band over the outputs stays raised."),
}
CURRENT = "v2"       # the version on node60.kicad_pcb (DEC-021)


def front(v):
    """KiCad Y of the board's front edge (the north edge is Y0 in every version)."""
    return Y0 + v.get("depth", D)


def out_row(v):
    """KiCad Y of the south-wall AT13 pin row."""
    return front(v) - (AT13_PANEL - EDGE_GAP)


def outputs(v):
    """ref -> (wall, position along it) for the six output headers."""
    return v.get("outputs", _FRONT_OUTS)


def busbar_outline(v, net):
    """(x0, y0, x1, y1) of a busbar in plan (x east, KiCad Y); both terminals sit on one row."""
    (xa, ya), (xb, yb) = (v["terminals"][r] for r in BUSBARS[net])
    h = BUSBAR_W / 2
    return min(xa, xb) - h, ya - h, max(xa, xb) + h, ya + h


def placements(version=CURRENT):
    """ref -> (lib, footprint, x, y, rotation_deg, bottom_side), in KiCad coordinates."""
    v = VERSIONS[version]
    down = v["board"] == "down"
    kx = (lambda x: 2 * X0 + W - x) if down else (lambda x: x)
    p = {}
    edge = AT13_PANEL - EDGE_GAP
    for ref, (wall, at) in outputs(v).items():
        if wall == "S":
            p[ref] = (*AT13, kx(at) - AT13_CY_X, out_row(v), 0, False)
        else:   # as the side-wall T1S below: rotation 90 faces KiCad +x, -90 faces -x
            east = (wall == "E") != down
            p[ref] = (*AT13, *((RIGHT - edge, at + AT13_CY_X, 90) if east else (LEFT + edge, at - AT13_CY_X, -90)),
                      False)
    if v["t1s"] == "north":
        # rotation 180: shroud (local +y) points north (-y), local +x points west (-x)
        north_row = Y0 + (ATM13_PANEL - EDGE_GAP)
        pitch = v.get("t1s_pitch", T1S_PITCH)
        p["J903"] = (*ATM13, kx(CX + pitch / 2) + ATM13_CY_X, north_row, 180, False)
        p["J912"] = (*ATM13, kx(CX - pitch / 2) + ATM13_CY_X, north_row, 180, False)
    else:
        # J903 on the east wall, J912 on the west wall, as seen from outside. Rotation 90:
        # shroud (local +y) points to KiCad +x, local +x points to -y; -90 the other way.
        cy, edge = v["t1s_y"], ATM13_PANEL - EDGE_GAP
        right, left = (RIGHT - edge, cy + ATM13_CY_X, 90, False), (LEFT + edge, cy - ATM13_CY_X, -90, False)
        p["J903"], p["J912"] = (*ATM13, *(left if down else right)), (*ATM13, *(right if down else left))
    # SMT REDCUBE: its thread opens through the board, away from its body, so the body sits
    # on the side facing away from the lid. Press-fit: block on the side facing the lid.
    on_bottom = v["terminal"] == "smt" and not down
    for ref, (x, y) in v["terminals"].items():
        p[ref] = (*REDCUBE[v["terminal"]], kx(x), y, 0, on_bottom)
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


def main(netlist, version=CURRENT):
    v = VERSIONS[version]
    if v.get("t1s_board", "main") != "main":
        sys.exit(f"{version}: J903/J912 sit on the MCU board, which isn't a separate PCB yet; not placeable")
    place = placements(version)
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
    outline.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(RIGHT), pcbnew.FromMM(front(v))))
    outline.SetLayer(pcbnew.Edge_Cuts)
    outline.SetWidth(pcbnew.FromMM(0.1))
    board.Add(outline)

    mm = lambda v: pcbnew.FromMM(v)
    for net in (BUSBARS if v["busbars"] else ()):
        x0, y0, x1, y1 = busbar_outline(v, net)
        if v["board"] == "down":
            x0, x1 = 2 * X0 + W - x1, 2 * X0 + W - x0
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
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else CURRENT)
