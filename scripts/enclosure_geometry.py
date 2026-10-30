#!/usr/bin/env python3
"""Node60 enclosure geometry (DEC-020): the spec for the enclosure drawing.

The handbook's enclosure-drawing skill draws from this: spec() returns the geometry
spec (format: the skill's references/spec.md) and scripts/enclosure_drawing.py, the
skill's engine copied into this repo, turns it into the views on the docs site.

Board and connector positions come from place_connectors.py, so the drawing follows
the PCB. Everything the enclosure adds (wall, gaps) is a named assumption below; change
it here and rebuild the docs.

Enclosure frame, seen from outside: origin at the front-left-bottom outer corner, x east
along the front face, y north (depth from the front face), z up. The board hangs
component side down under the lid, so every header cutout has its near edge (the edge
nearest the board) on top.

    python3 scripts/enclosure_geometry.py       # print the spec
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from place_connectors import (  # noqa: E402
    CX, D, EDGE_GAP, FRONT, LEFT, LID_TERMINALS, OUT_PITCH, RIGHT, T1S_DEPTH, THICKNESS, Y0,
)

# Enclosure assumptions: PROVISIONAL until an enclosure is chosen.
WALL = 3.0            # wall, floor and lid thickness
BACK_GAP = 2.0        # board's back edge to the back wall (no connector there)
FLOOR_GAP = 3.0       # deepest header to the floor

# Header heights above the board, measured from Amphenol's STEP models (the drawings give
# the cutouts but not, for the ATM13, their height).
AT13_HEIGHT, AT13_AXIS = 27.84, 13.8      # axis per drawing C-AT13-2P-BMXX rev. A2
ATM13_HEIGHT, ATM13_AXIS = 28.48, 15.0    # axis = mating-shroud centre in the STEP
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

# Inner faces in KiCad coordinates as seen from above the lid (before mirroring).
_X_IN_L, _X_IN_R = LEFT - EDGE_GAP, RIGHT + EDGE_GAP
_Y_IN_F, _Y_IN_B = FRONT + EDGE_GAP, Y0 - BACK_GAP


def ex(x_lid):
    """KiCad X seen from above the lid -> enclosure x."""
    return x_lid - (_X_IN_L - WALL)


def ey(y_kicad):
    """KiCad Y -> enclosure depth from the front outer face."""
    return (_Y_IN_F + WALL) - y_kicad


def spec():
    z_floor = WALL
    z_cs = z_floor + FLOOR_GAP + max(AT13_HEIGHT, ATM13_HEIGHT)   # component side (faces the floor)
    z_back = z_cs + THICKNESS                                     # back face (faces the lid)
    z_lid_out = z_back + SURLOK_DEPTH
    cutouts = [{"ref": f"J{904 + i}", "label": f"OUT{i + 1}", "face": "front", "type": "AT13",
                "x": ex(CX + (i - 2.5) * OUT_PITCH), "z": z_cs - AT13_AXIS} for i in range(6)]
    y_t1s = ey(FRONT - T1S_DEPTH * D)
    cutouts += [{"ref": "J903", "label": "T1S upstream", "face": "right", "type": "ATM13", "y": y_t1s,
                 "z": z_cs - ATM13_AXIS},
                {"ref": "J912", "label": "T1S downstream", "face": "left", "type": "ATM13", "y": y_t1s,
                 "z": z_cs - ATM13_AXIS}]
    nets = {"J910": "VBAT_IN", "J901": "VBAT_IN", "J911": "GND", "J902": "GND"}
    cutouts += [{"ref": r, "label": nets[r], "face": "top", "type": "SURLOK", "x": ex(x), "y": ey(y)}
                for r, (x, y) in sorted(LID_TERMINALS.items())]
    return {
        "title": "Node60 enclosure",
        "outside": {"x": _X_IN_R - _X_IN_L + 2 * WALL, "y": _Y_IN_F - _Y_IN_B + 2 * WALL, "z": z_lid_out},
        "wall": WALL,
        "board": {"x0": ex(LEFT), "x1": ex(RIGHT), "y0": ey(FRONT), "y1": ey(Y0), "z0": z_cs, "z1": z_back,
                  "note": "component side (z0) faces the floor"},
        "levels": [{"z": z_floor, "label": "floor, inside"}, {"z": z_lid_out - WALL, "label": "lid, inside"}],
        "cutout_types": CUTOUT_TYPES,
        "cutouts": cutouts,
        "assumptions": {"back_gap": BACK_GAP, "floor_gap": FLOOR_GAP, "edge_gap": EDGE_GAP,
                        "deepest_header": max(AT13_HEIGHT, ATM13_HEIGHT), "surlok_depth": SURLOK_DEPTH},
    }


if __name__ == "__main__":
    print(json.dumps(spec(), indent=1))
