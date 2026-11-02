#!/usr/bin/env python3
"""Node60's enclosure-fixed connectors (J901-J912), board outline and busbars, per design version.

Fifteen mechanical versions are kept as candidates (docs: Enclosure options). Each is a set
of parameters in VERSIONS; enclosure_geometry.py, check_surlok_clearance.py, the
dimensioned drawings and the 3D mockup are all generated from them. The PCB holds one:
CURRENT, unless another is named on the command line.

Run with KiCad's own Python (it provides the pcbnew module):

    kicad-cli sch export netlist --format kicadsexpr -o /tmp/node60.net node60.kicad_sch
    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
        scripts/place_connectors.py /tmp/node60.net [v2]

Close the PCB editor first. The script moves J901-J912, redraws the Edge.Cuts outline and
the busbar outlines (User.Drawings), footprints (BB901, BB902) and rule areas; every other
item on the board is left alone.
Footprints get the schematic symbol path, so a later Update PCB from Schematic (F8) links
to them and keeps their positions. A version whose terminal footprint differs from the
schematic's (the press-fit versions) can't be placed until the schematic changes.

Positions are written in plan as seen from above the lid (x east, KiCad Y toward the
front face). A board mounted component side down (version 1) is mirrored in KiCad, whose
top view then looks at the board from below.
"""
import os
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
CX = X0 + W / 2
THICKNESS = 2.6      # mm (DEC-020): the SMT REDCUBE's 2.6 mm spigot ends flush with the far face
# Version 10 (DEC-023, user, 2026-11-01): version 7 on a standard 2.0 mm board. The spigot then stands
# 0.6 mm proud of the top face and the busbar rests on it alone; Wurth has not confirmed that yet.
V10_THICKNESS = 2.0

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
# Versions 2, 4 and 7 (user, 2026-10-31): 40 mm. In versions 2 and 4 it also keeps the T stem
# narrow enough for the receptacles beside it to stagger (_T_LAYOUT); 41.98 mm is the most
# that works there.
T1S_PITCH_T = 40.0
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

# Version 9 (user, 2026-11-01): version 7 with every connector as close to the next as the
# checks and the parts allow, for the smallest board. The board stays centred on CX.
#   Headers: 1 mm between courtyards (AT13 36.3 mm, ATM13 37.9 mm along the row).
#   Battery: its plug pointing north passes 3 mm beside the T1S hood (hood half width
#     V9_T1S_PITCH / 2 + 18.41 flange + 3, plus 3 + 9 plug half width = 52.9 mm). The rows are
#     too close to the north wall for the plug to end short of the hood; moving them 9.4 mm south
#     instead would cost more board area than the 8.5 mm of width this costs.
#   Return: its flange 3 mm beside a battery plug pointing north (9 + 3 + 13.5 = 25.5 mm out).
#   Width: outward plugs may overhang the side walls (user, 2026-11-01), so the outputs set it.
#     The outer outputs' panel seals must clear the inside corner of the machined base, taken as
#     POCKET_R, so the side walls' inside faces are 2.5 x 37.3 pitch + 17.6 seal half width + 5 =
#     115.85 mm from the centre line. The board is a round 230 mm, so it stops 0.85 mm short of
#     them (user, 2026-11-01): the side walls don't locate the board, only the front wall does. Until
#     then a return plug pointing outward had to end inside the board edge, which made it
#     78.5 + 46.1 = 124.6 mm (board 249.5 mm).
#   Return row: the GND busbar 1 mm south of the T1S courtyards (Y0 + 26.85 + 1 + 12.7).
#   Battery row: the flanges 2 mm apart (27 + 2 = 29 mm south of the return row).
#   Depth: the battery flange 2 mm north of the front band (13.5 + 2 + 3 + 6.6 + 15 = 40.1 mm
#     from the front edge).
# The plug check confirms the receptacles (not the return row: it doesn't check the busbars).
POCKET_R = 5.0       # inside vertical corners of the machined base: ASSUMED, a 10 mm cutter for a ~30 mm deep pocket
V9_OUT_PITCH = 37.3
V9_T1S_PITCH = 39.0
V9_BAT_X, V9_RET_X = 53.0, 78.5
V9_WIDTH = 230.0
V9_SIDE_GAP = 2.5 * V9_OUT_PITCH + 17.6 + POCKET_R - V9_WIDTH / 2   # 0.85 mm
V9_RET_Y = Y0 + 40.6
V9_BAT_Y = V9_RET_Y + 29.0
V9_DEPTH = 110.0

# Version 8 (user, 2026-10-31): a second board, for the microcontroller, under the main
# board; the T1S pair J903/J912 sits on it, in the same plan positions, and stands up
# through a notch in the main board's north edge. Outline PROVISIONAL (plan, KiCad Y).
MCU_BOARD = (CX - 60.0, Y0, CX + 60.0, Y0 + 80.0)
MCU_THICKNESS = 1.6
NOTCH_CLEAR = 1.0    # notch edge to the ATM13 courtyards
# Fitting the boards one at a time (2026-10-31): a header's shroud passes through its wall
# cutout, so a board goes in by sliding toward its headers' wall, by the shroud's length past
# the flange face plus INSERT_CLEAR. Shroud lengths from Amphenol's STEP models.
AT13_SHROUD = 30.1 - AT13_PANEL      # 14.6 mm past the flange face
ATM13_SHROUD = 29.4 - ATM13_PANEL    # 12.9 mm
INSERT_CLEAR = 0.5
# Floor to the board's underside where only 3 mm hangs below it (SMT REDCUBE bodies, press-fit
# pins), plus 2 mm: versions 2, 4 and 7 (user, 2026-10-31). The others keep the default.
MIN_STANDOFF = 3.0 + 2.0
# Versions 2 and 7: 1 mm from the tallest header to the inside of a raised section (user,
# 2026-10-31), so the step over the low lid is 2 mm smaller. In plan the raised sections still
# reach enclosure_geometry.HOOD_GAP past the headers.
MIN_HOOD_GAP = 1.0
# Version 8: the MCU board goes in first and slides north; then the main board is lowered
# MAIN_TRAVEL north of its place and slides south, so it stops that far short of the north
# wall, and its notch is that much deeper so it clears the T1S headers while it is lowered.
# A mezzanine joins the boards: the main board slides in MEZZ_DROP high and drops onto it,
# so the output cutouts are MEZZ_DROP taller. Mezzanine size, place and stroke PROVISIONAL.
MAIN_TRAVEL = AT13_SHROUD + INSERT_CLEAR
MEZZ_DROP = 2.5
MEZZANINE = (CX - 20.0, Y0 + 66.0, CX + 20.0, Y0 + 74.0)   # plan outline, on the MCU board
MEZZ_PINS = ((CX - 26.0, Y0 + 70.0), (CX + 26.0, Y0 + 70.0)), 3.0   # guide pins and their diameter


def notch(v):
    """(x0, y0, x1, y1) of the main board's notch for a T1S pair on the MCU board."""
    half = v.get("t1s_pitch", T1S_PITCH) / 2 + sum(ATM13_ALONG) / 2 + NOTCH_CLEAR
    return (CX - half, main_north(v), CX + half,
            Y0 + ATM13_PANEL - EDGE_GAP + ATM13_BACK + NOTCH_CLEAR + (main_north(v) - Y0))


def main_north(v):
    """KiCad Y of the main board's north edge: Y0, or MAIN_TRAVEL short of it (version 8)."""
    return Y0 + (MAIN_TRAVEL if v.get("insert") == "boards" else 0.0)

# Busbars (DEC-021): 1/8" x 1" C110 copper flat bar, cut to length and drilled in house,
# one per terminal pair. Ends run half a width past each hole. A version may set its own bar
# with "busbar": (width, thickness, stock).
BUSBAR_W, BUSBAR_T = 25.4, 3.175
BUSBAR_STOCK = '1/8" x 1" C110 copper flat bar'
BUSBAR_HOLE = 6.5    # M6 clearance
BUSBARS = {"VBAT_IN": ("J910", "J901"), "GND": ("J911", "J902")}
# The bar rests on the spigots 0.6 mm above the top face (DEC-023), so no part fits under it.
# Each bar goes on the board as a generated board-only footprint (BUSBAR_REFS; not in the
# library or the schematic, out of the BOM and placement files) whose F.CrtYd is the bar
# outline, so KiCad's courtyard check keeps top-side parts out; the parts' own courtyard
# margin covers the bar's play on the stud (M6 clearance hole, about +/-0.25 mm). A rule area
# BUSBAR_<net> on F.Cu, the same size, lets node60.kicad_dru keep other nets' copper out.
BUSBAR_REFS = {"VBAT_IN": "BB901", "GND": "BB902"}
# Each bar footprint carries the library's model of that bar (model-only parts DropOut_Busbar,
# named from width, thickness, length and hole pitch) when the library has one, raised onto
# the spigots. Versions whose bar the library doesn't model get no 3D model.
BUSBAR_MODELS = "lib/dropout-kicad-library/3dmodels/DropOut_Busbar.3dshapes"
BUSBAR_Z = 0.6       # spigots above the top face (DEC-023)


def busbar(v):
    """(width, thickness, stock) of a version's busbars."""
    return v.get("busbar", (BUSBAR_W, BUSBAR_T, BUSBAR_STOCK))

AT13 = ("DropOut_Connector_Amphenol", "Amphenol_AT13-2P-BMxx_1x02_P5.40mm_Horizontal")
ATM13 = ("DropOut_Connector_Amphenol", "Amphenol_ATM13-2P-BMxx_1x02_P4.20mm_Horizontal")
REDCUBE = {"smt": ("DropOut_TerminalBlock_Wuerth", "Wuerth_REDCUBE-SMT_WP-SMRT_74660016"),
           "pressfit": ("DropOut_TerminalBlock_Wuerth", "Wuerth_REDCUBE-PRESS-FIT_WP-PFIFUA_786202106_PressFit")}

# Lid terminal layouts (plan, x east, KiCad Y).
_T_LAYOUT = {    # DEC-021: one battery/return pair in each low section beside the raised T. Battery
    "J910": (CX - 57.5, FRONT - 50), "J901": (CX + 57.5, FRONT - 50),   # close to the stem and in front,
    "J911": (CX - 78.7, FRONT - 115), "J902": (CX + 78.7, FRONT - 115)} # return wide, so a battery plug's
# cable pointing north passes beside the return receptacle (user, 2026-10-31). Battery row 50 mm
# from the front (user, 2026-10-31); 52.4 mm is the most before a battery plug pointing north
# comes within 3 mm of the return flange.
_STAGGER = {     # version 3: behind the raised front band; battery close, return wide, so a
    "J910": (CX - 40, FRONT - 87), "J901": (CX + 40, FRONT - 87),     # battery plug pointing
    "J911": (CX - 75, FRONT - 120), "J902": (CX + 75, FRONT - 120)}   # north passes beside the return

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
_MIDDLE_V8 = {**_MIDDLE, "J911": (CX - RET_X, FRONT - 103), "J902": (CX + RET_X, FRONT - 103)}  # GND bar clear of the notch
_COMPACT = {"J910": (CX - V9_BAT_X, V9_BAT_Y), "J901": (CX + V9_BAT_X, V9_BAT_Y),
            "J911": (CX - V9_RET_X, V9_RET_Y), "J902": (CX + V9_RET_X, V9_RET_Y)}
_MIDDLE_V6 = {"J910": (CX - BAT_X, Y0 + 82), "J901": (CX + BAT_X, Y0 + 82),
              "J911": (CX - RET_X, Y0 + 53), "J902": (CX + RET_X, Y0 + 53)}

# board: "up" (component side faces the lid) or "down"; t1s: "north" or "sides" (y of the
# pair centre); lid: "flat", "T" (crossbar over the outputs, stem over a north T1S pair) or
# "front" (one raised band across the front; with a north T1S pair, a separate hood over
# it), "seats" (flat at the headers' height, with a pocket for each receptacle down to the
# height it needs; version 4) or "corners" (a front band, a raised
# section in each back corner and one over a north T1S pair); outputs: wall ("S", "W", "E") and position along it (plan x
# on the south wall, KiCad Y on the side walls), default all six on the south wall;
# out_pitch: south-wall output pitch (default OUT_PITCH); width: board width, centred on CX (default W);
# side_gap: board edge to the inside of the east and west walls (default EDGE_GAP); thickness: board
# thickness (default THICKNESS);
# overhang: True when a plug pointing west or east may reach past the side walls (default: it must
# end inside the board edge); plugs: "WNE" (any of west, north, east) or "ON" (outward or north); depth: board depth
# (default D), the north edge stays at Y0; standoff: floor to the board's underside (default
# enclosure_geometry.STANDOFF); hood_gap: tallest header to the inside of a raised section
# (default enclosure_geometry.HOOD_GAP); insert: "boards" when each board goes in on its own
# (version 8: shorter main board, mezzanine); removable: walls that are separate panels, fitted
# after the board (versions 2 and 7: the north wall, so the board slides south into the
# one-piece front wall first; user, 2026-10-31); t1s_pitch: J903 to J912 (default T1S_PITCH); t1s_board: "main"
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
               removable=("back",), standoff=MIN_STANDOFF, hood_gap=MIN_HOOD_GAP,
               summary="Board component side up; SMT REDCUBEs underneath, busbars on top; a raised T over the "
                       "outputs and the T1S pair on the north wall, 40 mm apart. The receptacles are staggered "
                       "so a battery plug's cable pointing north passes beside the return receptacle."),
    "v3": dict(title="Version 3: busbars, raised front", decision=None, board="up", terminal="smt", busbars=True,
               t1s="sides", t1s_y=T1S_SIDE_FRONT, lid="front", plugs="ON", back_gap=2.0, terminals=_STAGGER,
               summary="As version 2, but the T1S pair moves to the side walls next to the outputs, so one raised "
                       "band across the front covers every header; the power receptacles sit behind it, staggered."),
    "v4": dict(title="Version 4: press-fit, flat lid", decision=None, board="up", terminal="pressfit", busbars=True,
               t1s="north", t1s_pitch=T1S_PITCH_T, lid="seats", plugs="ON", back_gap=EDGE_GAP, terminals=_T_LAYOUT,
               removable=("back",), standoff=MIN_STANDOFF,
               summary="Version 2's layout with REDCUBE press-fit 786202106 terminals on top of the board and the "
                       "busbars on the terminal blocks. The blocks lift the receptacles almost to the headers' "
                       "height, so the lid is flat, with a shallow seat machined for each receptacle (user, "
                       "2026-10-31); only the press-fit pins hang under the board, so it sits 5 mm off the floor."),
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
    "v7": dict(title="Version 7: busbars, front band and T1S hood", decision="DEC-022", board="up", terminal="smt",
               busbars=True, t1s="north", t1s_pitch=T1S_PITCH_T, lid="front", plugs="ON", back_gap=EDGE_GAP,
               terminals=_MIDDLE, removable=("back",), standoff=MIN_STANDOFF, hood_gap=MIN_HOOD_GAP,
               summary="Version 2 without the T's stem: a raised band across the front over the outputs and a "
                       "separate raised hood over the T1S pair on the north wall; the rest of the lid is low. "
                       "The power receptacles are placed as in version 6, staggered."),
    "v8": dict(title="Version 8: MCU board below, T1S lowered", decision=None, board="up", terminal="smt",
               busbars=True, t1s="north", t1s_board="mcu", insert="boards", lid="front", plugs="ON",
               back_gap=EDGE_GAP, terminals=_MIDDLE_V8,
               summary="Version 7 with a second board for the microcontroller under the main board. The T1S pair "
                       "moves onto it and stands up through a notch in the main board, low enough to fit under "
                       "the low lid, so the T1S hood goes; only the front band over the outputs stays raised. "
                       "Each board goes in on its own: the MCU board slides north into its wall, then the main "
                       "board, 15 mm shorter so it can, slides south and drops onto a mezzanine."),
    "v9": dict(title="Version 9: version 7, compact", decision=None, board="up", terminal="smt", busbars=True,
               t1s="north", t1s_pitch=V9_T1S_PITCH, lid="front", plugs="ON", back_gap=EDGE_GAP,
               terminals=_COMPACT, removable=("back",), standoff=MIN_STANDOFF, hood_gap=MIN_HOOD_GAP,
               out_pitch=V9_OUT_PITCH, width=V9_WIDTH, side_gap=V9_SIDE_GAP, depth=V9_DEPTH, overhang=True,
               summary="Version 7 with every connector as close to the next as the checks allow, for the "
                       "smallest board: outputs at a 37.3 mm pitch and the T1S pair 39 mm apart (1 mm between "
                       "courtyards), the receptacles pulled in until a battery plug pointing north just clears the "
                       "T1S hood, and the rows stacked as tight as the flanges, the GND busbar and the "
                       "front band allow. Plugs pointing outward may reach past the side walls, so the outputs "
                       "set the width. The board is 230 x 110 mm."),
}
VERSIONS["v10"] = {**VERSIONS["v7"], "title": "Version 10: version 7 on a 2.0 mm board", "decision": "DEC-023",
                   "thickness": V10_THICKNESS,
                   "summary": "Version 7 on a standard 2.0 mm board instead of 2.6 mm. The SMT REDCUBE's 2.6 mm spigot "
                              "stands 0.6 mm proud of the top face, so the busbar rests on the spigots alone: the joint "
                              "clamps no laminate, and the receptacles stay at version 7's height. The headers stand "
                              "0.6 mm lower, so the front band and T1S hood drop 0.6 mm, and their pin tails come "
                              "through 0.7 to 1.5 mm instead of 0.1 to 0.5 mm. Whether Würth allows the spigot to "
                              "stand proud is not confirmed."}
# Version 11 (DEC-024, user, 2026-11-01): version 9 (compact) on the 2.0 mm board of version 10. The plan is
# version 9's; only the heights change, as in version 10.
VERSIONS["v11"] = {**VERSIONS["v9"], "title": "Version 11: version 9 on a 2.0 mm board", "decision": "DEC-024",
                   "thickness": V10_THICKNESS,
                   "summary": "Version 9 (version 7, compact: a 230 x 110 mm board, outward plugs overhanging the side "
                              "walls) on the 2.0 mm board of version 10. The plan is version 9's; as in version 10 the "
                              "busbar rests on the REDCUBE spigots, 0.6 mm proud, and the front band and T1S hood are "
                              "0.6 mm lower."}
# Version 12 (user, 2026-11-01): version 11 on a 1.6 mm board. The spigot stands 1.0 mm proud.
V12_THICKNESS = 1.6
VERSIONS["v12"] = {**VERSIONS["v11"], "title": "Version 12: version 11 on a 1.6 mm board", "decision": None,
                   "thickness": V12_THICKNESS,
                   "summary": "Version 11 on a 1.6 mm board instead of 2.0 mm: version 9's compact plan (230 x 110 mm, "
                              "outward plugs overhanging the side walls). The REDCUBE's 2.6 mm spigot stands 1.0 mm "
                              "proud, and the busbar rests on it, so the receptacles stay where they are. The front band "
                              "and T1S hood are 1.0 mm lower than version 9's, and the header pin tails come through "
                              "1.1 to 1.9 mm."}
# Version 13 (user, 2026-11-01): version 11 with Amphenol RADLOK 5.7 mm receptacles (RL9057-101-F1x) and
# right-angle plugs (RL00571-25x) instead of SurLok Plus. The plug is 18.5 wide, 0.5 more than SurLok's, so a
# battery plug pointing north needs the battery receptacles 0.25 further out to stay 3 mm from the T1S hood
# (40.91 + 3 + 9.25 = 53.16): 53.5 mm.
V13_BAT_X = 53.5
VERSIONS["v13"] = {**VERSIONS["v11"], "title": "Version 13: version 11 with RADLOK receptacles", "decision": None,
                   "receptacle": "radlok",
                   "terminals": {**_COMPACT, "J910": (CX - V13_BAT_X, V9_BAT_Y), "J901": (CX + V13_BAT_X, V9_BAT_Y)},
                   "summary": "Version 11 (the compact plan on a 2.0 mm board) with Amphenol RADLOK 5.7 mm "
                              "feed-through receptacles (RL9057-101-F1x) and right-angle plugs (RL00571-25x) instead "
                              "of SurLok Plus. The receptacle sits 5 mm lower on the busbar, takes a 3 mm panel at "
                              "most (so the 4 mm lid has a 1 mm seat at each) and has a 10 mm stud that passes "
                              "through the REDCUBE, so the board sits higher to keep the stud tip 2 mm off the "
                              "floor. Its plug is shorter, 37 mm from the axis instead of 46."}
# Version 14 (user, 2026-11-01): version 11 with 3/16" x 3/4" C110 busbars instead of 1/8" x 1", to free top-side
# area along the bars. The receptacles rise 1.59 mm with the thicker bar; the SurLok stud's 9.95 mm then ends inside
# the REDCUBE (9.95 - 4.76 = 5.19 of its 5.6 mm thread), so nothing hangs below it and the board drops back to the
# 5 mm floor standoff. 5.19 mm is a full-height M6 nut's worth of thread (ISO 4032: 4.9 to 5.2 mm), the nut the
# threaded SurLok is normally fitted with. Würth's minimum thread engagement isn't known yet.
V14_BUSBAR = (19.05, 4.7625, '3/16" x 3/4" C110 copper flat bar')
VERSIONS["v14"] = {**VERSIONS["v11"], "title": "Version 14: version 11 with 3/16 x 3/4 in busbars", "decision": None,
                   "busbar": V14_BUSBAR,
                   "summary": "Version 11 (the compact plan on a 2.0 mm board) with 3/16\" x 3/4\" C110 busbars "
                              "instead of 1/8\" x 1\": 6.35 mm narrower, freeing top-side area along both bars, and "
                              "1.59 mm thicker, with 13 % more copper. The receptacles and the low lid rise with the "
                              "bar. The SurLok stud then ends inside the REDCUBE, engaging 5.2 of its 5.6 mm of "
                              "thread, so nothing hangs below the terminal and the board sits 5 mm off the floor. "
                              "Würth's minimum thread engagement is not confirmed."}

# Version 15 (DEC-025, user, 2026-11-01): version 11 with 1/8" x 3/4" C110 busbars: version 14's narrower bar, so the same
# top-side area comes free, at version 11's thickness, so the SurLok stud engages the REDCUBE's whole 5.6 mm thread
# and the heights are version 11's.
V15_BUSBAR = (19.05, 3.175, '1/8" x 3/4" C110 copper flat bar')
VERSIONS["v15"] = {**VERSIONS["v11"], "title": "Version 15: version 11 with 1/8 x 3/4 in busbars", "decision": "DEC-025",
                   "busbar": V15_BUSBAR,
                   "summary": "Version 11 (the compact plan on a 2.0 mm board) with 1/8\" x 3/4\" C110 busbars "
                              "instead of 1/8\" x 1\": version 14's 6.35 mm narrower bar, freeing the same top-side "
                              "area along both bars, at version 11's thickness, so the SurLok stud engages the "
                              "REDCUBE's whole thread and every height is version 11's. 25 % less copper in the bars."}

CURRENT = "v15"      # the version on node60.kicad_pcb (DEC-025)


def left(v):
    """KiCad X of the board's west edge (the board is centred on CX in every version)."""
    return CX - v.get("width", W) / 2


def right(v):
    return CX + v.get("width", W) / 2


def front(v):
    """KiCad Y of the board's front edge (the north edge is Y0 in every version)."""
    return Y0 + v.get("depth", D)


def out_row(v):
    """KiCad Y of the south-wall AT13 pin row."""
    return front(v) - (AT13_PANEL - EDGE_GAP)


def outputs(v):
    """ref -> (wall, position along it) for the six output headers."""
    if "outputs" in v:
        return v["outputs"]
    pitch = v.get("out_pitch", OUT_PITCH)
    return {f"J{904 + i}": ("S", CX + (i - 2.5) * pitch) for i in range(6)}


def busbar_model(v, net):
    """Library path of the 3D model for a version's busbar (it may not exist)."""
    (xa, _), (xb, _) = (v["terminals"][r] for r in BUSBARS[net])
    bw, bt, _ = busbar(v)
    pitch = round(abs(xb - xa), 3)
    return (f"{BUSBAR_MODELS}/Busbar_Cu_{bw:g}x{bt:g}mm_L{round(pitch + bw, 3):g}mm"
            f"_2xD{BUSBAR_HOLE:g}mm_P{pitch:g}mm.step")


def busbar_outline(v, net):
    """(x0, y0, x1, y1) of a busbar in plan (x east, KiCad Y); both terminals sit on one row."""
    (xa, ya), (xb, yb) = (v["terminals"][r] for r in BUSBARS[net])
    h = busbar(v)[0] / 2
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
            p[ref] = (*AT13, *((right(v) - edge, at + AT13_CY_X, 90) if east else (left(v) + edge, at - AT13_CY_X, -90)),
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
        east, west = (right(v) - edge, cy + ATM13_CY_X, 90, False), (left(v) + edge, cy - ATM13_CY_X, -90, False)
        p["J903"], p["J912"] = (*ATM13, *(west if down else east)), (*ATM13, *(east if down else west))
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
    # The busbar footprints are drawn anew and the old ones removed just before saving (see
    # above); the rule areas are reused.
    old_bars = [fp for fp in (board.FindFootprintByReference(ref) for ref in BUSBAR_REFS.values()) if fp]
    areas = {z.GetZoneName(): z for z in board.Zones()
             if z.GetIsRuleArea() and z.GetZoneName().startswith("BUSBAR_")}
    board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(v.get("thickness", THICKNESS)))

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
    outline.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(left(v)), pcbnew.FromMM(Y0)))
    outline.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(right(v)), pcbnew.FromMM(front(v))))
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
        bw, bt, stock = busbar(v)
        label.SetText(f"{net} busbar {bw:g} x {bt:g} Cu ({stock}), on top: no parts under it")
        label.SetPosition(pcbnew.VECTOR2I(mm((x0 + x1) / 2), mm(y0 - 2)))
        label.SetLayer(pcbnew.Dwgs_User)
        label.SetTextSize(pcbnew.VECTOR2I(mm(1.5), mm(1.5)))
        board.Add(label)
        keepout = areas.pop(f"BUSBAR_{net}", None)
        if keepout is None:
            keepout = pcbnew.ZONE(board)
            keepout.SetZoneName(f"BUSBAR_{net}")
            board.Add(keepout)
        keepout.SetIsRuleArea(True)
        keepout.SetLayer(pcbnew.F_Cu)
        for allow in (keepout.SetDoNotAllowTracks, keepout.SetDoNotAllowVias, keepout.SetDoNotAllowPads,
                      keepout.SetDoNotAllowZoneFills, keepout.SetDoNotAllowFootprints):
            allow(False)                              # node60.kicad_dru and the courtyard do the work
        corners = keepout.Outline()
        corners.RemoveAllContours()
        corners.NewOutline()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            corners.Append(mm(x), mm(y))
        fp = pcbnew.FOOTPRINT(board)
        fp.SetReference(BUSBAR_REFS[net])
        board.Add(fp)
        fp.SetFPID(pcbnew.LIB_ID("", f"Busbar_{bw:g}x{bt:g}mm"))
        fp.SetValue(f"{stock}, {x1 - x0:.1f} mm")
        fp.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        fp.SetPosition(pcbnew.VECTOR2I(mm((x0 + x1) / 2), mm((y0 + y1) / 2)))
        for text, dy in ((fp.Reference(), -2), (fp.Value(), 2)):
            text.SetLayer(pcbnew.F_Fab)
            text.SetPosition(pcbnew.VECTOR2I(mm((x0 + x1) / 2), mm((y0 + y1) / 2 + dy)))
            text.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
        for layer, width in ((pcbnew.F_CrtYd, 0.05), (pcbnew.F_Fab, 0.1)):
            r = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_RECT)
            r.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
            r.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
            r.SetLayer(layer)
            r.SetWidth(mm(width))
            fp.Add(r)
        # The terminals' spigot holes (NPTH) are cut out of the courtyard, which would otherwise
        # hold another footprint's hole (a DRC error); nothing else fits there anyway.
        for term in BUSBARS[net]:
            for pad in board.FindFootprintByReference(term).Pads():
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    hole = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_CIRCLE)
                    hole.SetCenter(pad.GetPosition())
                    hole.SetRadius(pad.GetDrillSize().x // 2 + mm(0.1))
                    hole.SetLayer(pcbnew.F_CrtYd)
                    hole.SetWidth(mm(0.05))
                    fp.Add(hole)
        step = busbar_model(v, net)
        if v["board"] == "up" and os.path.exists(step):
            model = pcbnew.FP_3DMODEL()
            model.m_Filename = "${KIPRJMOD}/" + step
            model.m_Offset = pcbnew.VECTOR3D(0, 0, BUSBAR_Z)
            fp.Models().push_back(model)
        fp.SetLocked(True)

    if areas:
        sys.exit(f"{version}: no such busbars, but the board has {sorted(areas)}; delete them in KiCad first")
    for ref in sorted(place):
        fp = board.FindFootprintByReference(ref)
        bb = fp.GetCourtyard(fp.GetLayer()).BBox() if fp.GetCourtyard(fp.GetLayer()).OutlineCount() else fp.GetBoundingBox()
        print(f"{ref} {fp.GetLayerName():5} {pcbnew.ToMM(fp.GetPosition().x):7.2f} {pcbnew.ToMM(fp.GetPosition().y):7.2f} "
              f"rot {fp.GetOrientationDegrees():6.1f}  courtyard x {pcbnew.ToMM(bb.GetLeft()):.1f}..{pcbnew.ToMM(bb.GetRight()):.1f} "
              f"y {pcbnew.ToMM(bb.GetTop()):.1f}..{pcbnew.ToMM(bb.GetBottom()):.1f}  "
              + " ".join(f"{p.GetNumber()}={p.GetNetname()}" for p in fp.Pads() if p.GetNumber()))
    for fp in old_bars:
        board.Remove(fp)
    board.Save(PCB)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else CURRENT)
