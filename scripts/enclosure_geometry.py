#!/usr/bin/env python3
"""Node60 enclosure geometry (DEC-021): the spec for the enclosure drawing.

The handbook's enclosure-drawing skill draws from this: spec() returns the geometry
spec (format: the skill's references/spec.md) and scripts/enclosure_drawing.py, the
skill's engine copied into this repo, turns it into the views on the docs site. The 3D
mockup reads the same spec from enclosure.json.

Board and connector positions come from place_connectors.py, so the drawing follows
the PCB. Everything the enclosure adds (wall, gaps) is a named assumption below; change
it here and rebuild the docs.

Enclosure frame, seen from outside: origin at the front-left-bottom outer corner, x east
along the front face, y north (depth from the front face), z up. The board sits
component side up. The lid has a raised T: a crossbar along the front over the output
headers and a stem up the middle over the T1S headers. The SurLok receptacles sit in
the two low sections either side of the stem, on 1/8" x 1" busbars.

    python3 scripts/enclosure_geometry.py       # print the spec
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from place_connectors import (  # noqa: E402
    AT13_PANEL, ATM13_PANEL, BUSBAR_HOLE, BUSBAR_T, BUSBAR_W, BUSBARS, CX, EDGE_GAP, FRONT, LEFT,
    LID_TERMINALS, OUT_PITCH, RIGHT, T1S_PITCH, THICKNESS, Y0, busbar_outline,
)

# Enclosure assumptions: PROVISIONAL until an enclosure is chosen.
WALL = 3.0            # wall, floor and lid thickness
STANDOFF = 8.0        # floor (inside) to the board's bottom face: REDCUBE bodies (3.0) hang below
HOOD_GAP = 3.0        # tallest header to the inside of the raised T; T edges this far past the headers

# Header heights above the board, measured from Amphenol's STEP models (the drawings give
# the cutouts but not, for the ATM13, their height).
AT13_HEIGHT, AT13_AXIS = 27.84, 13.8      # axis per drawing C-AT13-2P-BMXX rev. A2
ATM13_HEIGHT, ATM13_AXIS = 28.48, 15.0    # axis = mating-shroud centre in the STEP
AT13_BACK = 6.6       # header body behind its pin row (footprint courtyard)
ATM13_BACK = 10.85
ATM13_HALF = 18.41    # flange half width
SURLOK_DEPTH = 36.7 - 16.5 - 1.0          # SurLok catalog IC-10 p. 6: contact face to panel face (B - A - C)

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

# Inner faces in KiCad coordinates (component side up: KiCad's view is the view from above).
_X_IN_L, _X_IN_R = LEFT - EDGE_GAP, RIGHT + EDGE_GAP
_Y_IN_F, _Y_IN_B = FRONT + EDGE_GAP, Y0 - EDGE_GAP


def ex(x_kicad):
    """KiCad X -> enclosure x."""
    return x_kicad - (_X_IN_L - WALL)


def ey(y_kicad):
    """KiCad Y -> enclosure depth from the front outer face."""
    return (_Y_IN_F + WALL) - y_kicad


def spec():
    z_bottom = WALL + STANDOFF                    # board bottom face
    z_top = z_bottom + THICKNESS                  # component side, facing the lid
    z_busbar = z_top + BUSBAR_T                   # top of the busbars
    z_low = z_busbar + SURLOK_DEPTH               # low lid, outside: the receptacles' panel face
    z_hood = z_top + max(AT13_HEIGHT, ATM13_HEIGHT) + HOOD_GAP + WALL   # raised T, outside
    outside = {"x": _X_IN_R - _X_IN_L + 2 * WALL, "y": _Y_IN_F - _Y_IN_B + 2 * WALL, "z": z_low}

    out_row = FRONT - (AT13_PANEL - EDGE_GAP)     # AT13 pin row (KiCad Y)
    north_row = Y0 + (ATM13_PANEL - EDGE_GAP)     # ATM13 pin row
    cross_y1 = ey(out_row - AT13_BACK) + HOOD_GAP                 # crossbar reaches past the AT13 bodies
    stem_half = T1S_PITCH / 2 + ATM13_HALF + HOOD_GAP
    xc = ex(CX)
    raised = [
        {"x0": 0, "x1": outside["x"], "y0": 0, "y1": cross_y1, "z": z_hood, "label": "T crossbar"},
        {"x0": xc - stem_half, "x1": xc + stem_half, "y0": cross_y1, "y1": outside["y"], "z": z_hood,
         "label": "T stem"},
    ]
    assert ey(north_row + ATM13_BACK) + HOOD_GAP > 0, "stem covers the T1S headers"

    cutouts = [{"ref": f"J{904 + i}", "label": f"OUT{i + 1}", "face": "front", "type": "AT13",
                "x": ex(CX + (i - 2.5) * OUT_PITCH), "z": z_top + AT13_AXIS, "near_edge": "down"}
               for i in range(6)]
    cutouts += [{"ref": r, "label": lbl, "face": "back", "type": "ATM13", "x": ex(CX + sx * T1S_PITCH / 2),
                 "z": z_top + ATM13_AXIS, "near_edge": "down"}
                for r, lbl, sx in (("J903", "T1S upstream", 1), ("J912", "T1S downstream", -1))]
    nets = {"J910": "VBAT_IN", "J901": "VBAT_IN", "J911": "GND", "J902": "GND"}
    cutouts += [{"ref": r, "label": nets[r], "face": "top", "type": "SURLOK", "x": ex(x), "y": ey(y)}
                for r, (x, y) in sorted(LID_TERMINALS.items())]

    busbars = []
    for net, refs in BUSBARS.items():
        x0, y0, x1, y1 = busbar_outline(net)
        holes = [ex(LID_TERMINALS[r][0]) for r in refs]
        busbars.append({"net": net, "refs": list(refs), "x0": ex(x0), "x1": ex(x1), "y0": ey(y1), "y1": ey(y0),
                        "z0": z_top, "z1": z_busbar, "length": x1 - x0, "hole_pitch": abs(holes[1] - holes[0]),
                        "hole_d": BUSBAR_HOLE})
    return {
        "title": "Node60 enclosure",
        "outside": outside,
        "wall": WALL,
        "board": {"x0": ex(LEFT), "x1": ex(RIGHT), "y0": ey(FRONT), "y1": ey(Y0), "z0": z_bottom, "z1": z_top,
                  "note": "component side (z1) faces the lid"},
        "levels": [{"z": WALL, "label": "floor, inside"}, {"z": z_busbar, "label": "busbar top"},
                   {"z": z_low - WALL, "label": "low lid, inside"}],
        "raised": raised,
        "cutout_types": CUTOUT_TYPES,
        "cutouts": cutouts,
        "busbars": busbars,
        "parts": {"AT13": {"height": AT13_HEIGHT, "axis": AT13_AXIS, "panel": AT13_PANEL, "back": AT13_BACK},
                  "ATM13": {"height": ATM13_HEIGHT, "axis": ATM13_AXIS, "panel": ATM13_PANEL, "back": ATM13_BACK},
                  "SURLOK": {"depth": SURLOK_DEPTH, "plug": [18.0, 55.1, 22.6]},
                  "busbar": {"width": BUSBAR_W, "thickness": BUSBAR_T, "stock": '1/8" x 1" C110 copper flat bar'}},
        "assumptions": {"standoff": STANDOFF, "hood_gap": HOOD_GAP, "edge_gap": EDGE_GAP,
                        "deepest_header": max(AT13_HEIGHT, ATM13_HEIGHT), "surlok_depth": SURLOK_DEPTH,
                        "hood_z": z_hood, "low_z": z_low},
    }


if __name__ == "__main__":
    print(json.dumps(spec(), indent=1))
