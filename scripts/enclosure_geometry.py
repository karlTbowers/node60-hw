#!/usr/bin/env python3
"""Node60 enclosure geometry, per design version: the spec for the drawings and the mockup.

The handbook's enclosure-drawing skill draws from this: spec(version) returns the geometry
spec (format: the skill's references/spec.md) and scripts/enclosure_drawing.py, the
skill's engine copied into this repo, turns it into views. scripts/enclosure_versions.py
does that for every version at docs build time; the 3D mockup reads the same JSON.

Board and connector positions come from place_connectors.py (VERSIONS), so each drawing
follows its layout. Everything the enclosure adds (wall, gaps) is a named assumption below.

Enclosure frame, seen from outside: origin at the front-left-bottom outer corner, x east
along the front face, y north (depth from the front face), z up.

    python3 scripts/enclosure_geometry.py [v2]      # print one version's spec
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from place_connectors import (  # noqa: E402
    AT13_BACK, AT13_PANEL, ATM13_ALONG, ATM13_BACK, ATM13_PANEL, BUSBAR_HOLE, BUSBAR_T, BUSBAR_W, BUSBARS, CURRENT,
    CX, EDGE_GAP, FRONT, LEFT, MCU_BOARD, MCU_THICKNESS, NOTCH, OUT_ROW, RIGHT, T1S_PITCH, THICKNESS, VERSIONS, Y0,
    busbar_outline, outputs,
)

# Enclosure assumptions: PROVISIONAL until an enclosure is chosen.
WALL = 3.0            # wall, floor and lid thickness
STANDOFF = 8.0        # board up: floor (inside) to the board's bottom face (SMT REDCUBE bodies or press-fit pins hang below)
FLOOR_GAP = 3.0       # board down: deepest header to the floor
HOOD_GAP = 3.0        # tallest header to the inside of a raised section; raised edges this far past the headers
MCU_STANDOFF = 5.0    # version 8: floor (inside) to the MCU board's bottom face
BOARD_GAP = 10.0      # version 8: MCU board top to main board bottom. It also sets whether the T1S pair on the
                      # MCU board fits under the low lid: it needs 9.5 mm or more for HOOD_GAP above the ATM13s

# Header heights above the board, measured from Amphenol's STEP models (the drawings give
# the cutouts but not, for the ATM13, their height).
AT13_HEIGHT, AT13_AXIS = 27.84, 13.8      # axis per drawing C-AT13-2P-BMXX rev. A2
ATM13_HEIGHT, ATM13_AXIS = 28.48, 15.0    # axis = mating-shroud centre in the STEP
ATM13_HALF = 18.41    # flange half width
AT13_HALF = 35.20 / 2  # panel seal half width
SURLOK_DEPTH = 36.7 - 16.5 - 1.0          # SurLok catalog IC-10 p. 6: contact face to panel face (B - A - C)
STUD = 7.7            # SurLok M6 stud length: ESTIMATE in the library model; Amphenol publishes none

# Power terminals: what the stud screws into, and where its thread starts.
TERMINALS = {
    # Würth 74660016R: reverse SMT, Ø12 x 3.0 flange on the far face, Ø9.0 spigot 2.6 long flush
    # with the near face; M6 through thread 5.6 long (flange + spigot).
    "smt": {"name": "Würth REDCUBE 74660016R (SMT, reverse)", "height": 3.0, "thread": 5.6, "pins": 0.0},
    # Würth 786202106: 10 x 10 x 10.5 block, M6 blind thread 6.0 deep from its top, 16 press-fit
    # pins 3.0 below the board; 4 mm component keep-out, 3 mm from the board edge.
    "pressfit": {"name": "Würth REDCUBE 786202106 (press-fit)", "height": 10.5, "thread": 6.0, "pins": 3.0},
}

CUTOUT_TYPES = {
    # Amphenol "recommended panel cutout", drawing C-AT13-2P-BMXX rev. A2. Near edge 4.8 from the board.
    "AT13": {"shape": "keyed", "name": "AT13-2P-BM04", "width": 18.16, "full": 14.87, "total": 18.03,
             "tab": 11.18, "corner": 4.32, "near": AT13_AXIS - 4.8, "holes": 25.40, "hole_d": 3.94,
             "seal": [35.20, 27.69]},
    # Drawing ATM13-2P-BMXX rev. A2; holes 8.58 from the near edge, placed on the STEP's axis.
    "ATM13": {"shape": "keyed", "name": "ATM13-2P-BM04", "width": 14.00, "full": 13.00, "total": 17.15,
              "tab": 17.60, "corner": 4.00, "near": 8.58, "holes": 25.79, "hole_d": 4.06,
              "seal": [36.82, 26.95]},
    # SurLok Plus catalog IC-10 p. 13, 5.7 mm: the catalog gives "M4 screw", not a hole size.
    "SURLOK": {"shape": "round", "name": "SurLok Plus 5.7 mm", "d": 14.3, "screw_square": 18.0,
               "screw": "M4", "screw_d": 4.0, "flange": 27.0},
}


def spec(version=CURRENT):
    v = VERSIONS[version]
    up = v["board"] == "up"
    term = TERMINALS[v["terminal"]]
    mcu = v.get("t1s_board", "main") == "mcu"           # T1S on the MCU board under the main board
    deepest = AT13_HEIGHT if mcu else max(AT13_HEIGHT, ATM13_HEIGHT)   # tallest header on the main board
    x_in_l, x_in_r = LEFT - EDGE_GAP, RIGHT + EDGE_GAP
    y_in_f, y_in_b = FRONT + EDGE_GAP, Y0 - v["back_gap"]
    ex = lambda x: x - (x_in_l - WALL)                 # plan X (seen from above) -> enclosure x
    ey = lambda y: (y_in_f + WALL) - y                  # KiCad Y -> depth from the front outer face

    if up:
        m0 = WALL + MCU_STANDOFF                        # MCU board bottom (version 8)
        z0 = m0 + MCU_THICKNESS + BOARD_GAP if mcu else WALL + STANDOFF   # board bottom
        z1 = z0 + THICKNESS                             # component side, facing the lid
        cs, side_sign = z1, 1                           # headers stand up from the component side
        term_top = z1 + (term["height"] if v["terminal"] == "pressfit" else 0.0)
        term_z = [z1, term_top] if v["terminal"] == "pressfit" else [z0 - term["height"], z0]
    else:
        z0 = WALL + FLOOR_GAP + deepest                 # component side, facing the floor
        z1 = z0 + THICKNESS                             # back face, facing the lid
        cs, side_sign = z0, -1                          # headers hang from the component side
        term_top = z1                                   # SMT spigot flush with the back face
        term_z = [z0 - term["height"], z0]
    contact = term_top + (BUSBAR_T if v["busbars"] else 0.0)   # SurLok contact face
    low = contact + SURLOK_DEPTH                                # lid outside where the receptacles sit
    outside = {"x": x_in_r - x_in_l + 2 * WALL, "y": y_in_f - y_in_b + 2 * WALL, "z": low}

    # Raised lid sections over the headers, where they don't fit under the low lid.
    hood = cs + deepest + HOOD_GAP + WALL
    raised = []
    outs = outputs(v)
    t1s_cs = m0 + MCU_THICKNESS if mcu else cs          # component side the T1S pair stands on
    t1s_hood = t1s_cs + ATM13_HEIGHT + HOOD_GAP + WALL
    if up and hood > low and v["lid"] == "corners":
        # A front band over the south-wall outputs and the side-wall outputs in the front
        # corners; a raised section over each back-corner output and over the T1S pair.
        # HOOD_GAP past the header bodies and the panel seals.
        side = [at for wall, at in outs.values() if wall != "S"]
        back = [at for at in side if at < (Y0 + FRONT) / 2]
        band = max([ey(OUT_ROW - AT13_BACK) + HOOD_GAP]
                   + [ey(at - AT13_HALF - HOOD_GAP) for at in side if at not in back])
        raised.append({"x0": 0, "x1": outside["x"], "y0": 0, "y1": band, "z": hood, "label": "raised front"})
        corner_y0 = ey(max(back) + AT13_HALF + HOOD_GAP)
        inner = ex(LEFT + AT13_PANEL - EDGE_GAP + AT13_BACK + HOOD_GAP)     # inner edge of a corner section
        raised.append({"x0": 0, "x1": inner, "y0": corner_y0, "y1": outside["y"], "z": hood,
                       "label": "west back corner"})
        raised.append({"x0": outside["x"] - inner, "x1": outside["x"], "y0": corner_y0, "y1": outside["y"],
                       "z": hood, "label": "east back corner"})
        half = T1S_PITCH / 2 + ATM13_HALF + HOOD_GAP
        raised.append({"x0": ex(CX) - half, "x1": ex(CX) + half,
                       "y0": ey(Y0 + ATM13_PANEL - EDGE_GAP + ATM13_BACK) - HOOD_GAP, "y1": outside["y"],
                       "z": hood, "label": "T1S hood"})
    elif up and hood > low:
        cross_y1 = ey(OUT_ROW - AT13_BACK) + HOOD_GAP
        if v["t1s"] == "sides":                         # the band also covers the side-wall T1S bodies
            cross_y1 = max(cross_y1, ey(v["t1s_y"] - max(ATM13_ALONG)) + HOOD_GAP)
        raised.append({"x0": 0, "x1": outside["x"], "y0": 0, "y1": cross_y1, "z": hood,
                       "label": "T crossbar" if v["lid"] == "T" else "raised front"})
        if v["t1s"] == "north":
            stem_half = T1S_PITCH / 2 + ATM13_HALF + HOOD_GAP
            if v["lid"] == "T":                         # the stem joins the crossbar
                raised.append({"x0": ex(CX) - stem_half, "x1": ex(CX) + stem_half, "y0": cross_y1,
                               "y1": outside["y"], "z": hood, "label": "T stem"})
            elif t1s_hood > low:                        # a separate hood over the T1S pair only
                raised.append({"x0": ex(CX) - stem_half, "x1": ex(CX) + stem_half,
                               "y0": ey(Y0 + ATM13_PANEL - EDGE_GAP + ATM13_BACK) - HOOD_GAP,
                               "y1": outside["y"], "z": t1s_hood, "label": "T1S hood"})

    near = "down" if up else "up"
    faces = {"S": "front", "W": "left", "E": "right"}     # plan positions are seen from above
    cutouts = [{"ref": r, "label": f"OUT{int(r[1:]) - 903}", "face": faces[wall], "type": "AT13",
                **({"x": ex(at)} if wall == "S" else {"y": ey(at)}), "z": cs + side_sign * AT13_AXIS,
                "near_edge": near}
               for r, (wall, at) in outs.items()]
    if v["t1s"] == "north":
        cutouts += [{"ref": r, "label": lbl, "face": "back", "type": "ATM13", "x": ex(CX + sx * T1S_PITCH / 2),
                     "z": t1s_cs + side_sign * ATM13_AXIS, "near_edge": near, "base": t1s_cs}
                    for r, lbl, sx in (("J903", "T1S upstream", 1), ("J912", "T1S downstream", -1))]
    else:
        cutouts += [{"ref": r, "label": lbl, "face": face, "type": "ATM13", "y": ey(v["t1s_y"]),
                     "z": cs + side_sign * ATM13_AXIS, "near_edge": near}
                    for r, lbl, face in (("J903", "T1S upstream", "right"), ("J912", "T1S downstream", "left"))]
    nets = {"J910": "VBAT_IN", "J901": "VBAT_IN", "J911": "GND", "J902": "GND"}
    mid = outside["x"] / 2
    for r, (x, y) in sorted(v["terminals"].items()):
        dirs = ["W", "N", "E"] if v["plugs"] == "WNE" else ["W" if ex(x) < mid else "E", "N"]
        cutouts.append({"ref": r, "label": nets[r], "face": "top", "type": "SURLOK", "x": ex(x), "y": ey(y),
                        "plug_dirs": dirs})

    busbars = []
    for net, refs in (BUSBARS.items() if v["busbars"] else ()):
        x0, y0, x1, y1 = busbar_outline(v, net)
        holes = [ex(v["terminals"][r][0]) for r in refs]
        busbars.append({"net": net, "refs": list(refs), "x0": ex(x0), "x1": ex(x1), "y0": ey(y1), "y1": ey(y0),
                        "z0": term_top, "z1": contact, "length": x1 - x0, "hole_pitch": abs(holes[1] - holes[0]),
                        "hole_d": BUSBAR_HOLE})
    engage = STUD - (contact - term_top)
    levels = [{"z": WALL, "label": "floor, inside"}]
    if v["busbars"]:
        levels.append({"z": contact, "label": "busbar top"})
    levels.append({"z": low - WALL, "label": "lid, inside" if not raised else "low lid, inside"})
    return {
        "title": f"Node60 enclosure, {v['title'].split(':')[0].lower()}",
        "version": {"id": version, "title": v["title"], "summary": v["summary"], "decision": v["decision"],
                    "current": version == CURRENT, "lid": v["lid"],
                    "outputs": sorted({w for w, _ in outs.values()})},
        "outside": outside,
        "wall": WALL,
        "board": {"x0": ex(LEFT), "x1": ex(RIGHT), "y0": ey(FRONT), "y1": ey(Y0), "z0": z0, "z1": z1,
                  "component_side": "top" if up else "bottom",
                  "note": "component side (z1) faces the lid" if up else "component side (z0) faces the floor",
                  "notches": [{"x0": ex(NOTCH[0]), "x1": ex(NOTCH[2]), "y0": ey(NOTCH[3]), "y1": ey(NOTCH[1]),
                               "label": "notch for the T1S pair"}] if mcu else []},
        "boards": [{"label": "MCU board", "x0": ex(MCU_BOARD[0]), "x1": ex(MCU_BOARD[2]), "y0": ey(MCU_BOARD[3]),
                    "y1": ey(MCU_BOARD[1]), "z0": m0, "z1": m0 + MCU_THICKNESS}] if mcu else [],
        "levels": levels,
        "raised": raised,
        "cutout_types": CUTOUT_TYPES,
        "cutouts": cutouts,
        "busbars": busbars,
        "terminal": {**term, "kind": v["terminal"], "z0": term_z[0], "z1": term_z[1], "thread_top": term_top,
                     "stud_engagement": min(engage, term["thread"])},
        "parts": {"AT13": {"height": AT13_HEIGHT, "axis": AT13_AXIS, "panel": AT13_PANEL, "back": AT13_BACK},
                  "ATM13": {"height": ATM13_HEIGHT, "axis": ATM13_AXIS, "panel": ATM13_PANEL, "back": ATM13_BACK},
                  "SURLOK": {"depth": SURLOK_DEPTH, "stud": STUD, "contact_z": contact, "plug": [18.0, 55.1, 22.6]},
                  "busbar": {"width": BUSBAR_W, "thickness": BUSBAR_T, "stock": '1/8" x 1" C110 copper flat bar'}},
        "assumptions": {"standoff": None if mcu or not up else STANDOFF, "floor_gap": None if up else FLOOR_GAP,
                        "mcu_standoff": MCU_STANDOFF if mcu else None, "board_gap": BOARD_GAP if mcu else None,
                        "hood_gap": HOOD_GAP, "edge_gap": EDGE_GAP, "back_gap": v["back_gap"],
                        "deepest_header": deepest, "surlok_depth": SURLOK_DEPTH,
                        "hood_z": hood if raised else None, "low_z": low},
    }


if __name__ == "__main__":
    print(json.dumps(spec(sys.argv[1] if len(sys.argv) > 1 else CURRENT), indent=1))
