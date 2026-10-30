#!/usr/bin/env python3
"""Node60 enclosure geometry (DEC-020): one source for the dimensioned drawing.

Board and connector positions come from place_connectors.py, so the drawing
follows the PCB. Everything the enclosure adds (wall, gaps) is a named
assumption below; change it here and rebuild the docs.

Enclosure frame, seen from outside: origin at the front-left-bottom outer
corner, x east along the front face, y north (depth from the front face),
z up. The board hangs component side down under the lid, so every header
cutout is upside down: the side of the cutout nearest the board is on top.

    python3 scripts/enclosure_geometry.py      # print the key dimensions
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

# SurLok Plus 5.7 mm receptacle, catalog IC-10: p. 6 (A, B, C, D), p. 13 (panel layout).
SURLOK = {
    "depth": 36.7 - 16.5 - 1.0,   # contact face to panel face (B - A - C): sets board-to-lid
    "cutout_d": 14.3,
    "screw_square": 18.0,         # 4 x M4 screws on this square
    "flange": 27.0,
}

# Header panel cutouts, from Amphenol's "recommended panel cutout" views (drawings
# C-AT13-2P-BMXX rev. A2 and ATM13-2P-BMXX rev. A2). Heights are measured from the
# board's component side; "near" is the cutout edge nearest the board.
AT13 = {
    "height": 27.84,      # body, from Amphenol's STEP (DEC-013 quotes 27.4)
    "axis": 13.8,         # mating axis and screw holes
    "near": 4.8,
    "width": 18.16,       # full-width part, 14.87 from the near edge, R4.32 corners
    "full": 14.87,
    "total": 18.03,       # with the 11.18 key tab at the far edge
    "tab": 11.18,
    "corner": 4.32,
    "holes": 25.40,       # 2 x Ø3.94 on the axis
    "hole_d": 3.94,
    "seal": (35.20, 27.69),   # minimum flat panel area for the flange seal
}
ATM13 = {
    "height": 28.48,      # body, from Amphenol's STEP
    "axis": 15.0,         # mating-shroud centre in Amphenol's STEP (drawing gives no height)
    "near": 15.0 - 8.58,  # holes are 8.58 from the near edge
    "width": 14.00,       # slot, 13.00 from the near edge, R4.00 corners
    "full": 13.00,
    "total": 17.15,       # with the 17.60 wide band at the far edge
    "tab": 17.60,
    "corner": 4.00,
    "holes": 25.79,       # 2 x Ø4.06
    "hole_d": 4.06,
    "seal": (36.82, 26.95),
}

# Inner faces in KiCad coordinates as seen from above the lid (before mirroring).
_X_IN_L = LEFT - EDGE_GAP
_X_IN_R = RIGHT + EDGE_GAP
_Y_IN_F = FRONT + EDGE_GAP
_Y_IN_B = Y0 - BACK_GAP


def ex(x_lid):
    """KiCad X seen from above the lid -> enclosure x."""
    return x_lid - (_X_IN_L - WALL)


def ey(y_kicad):
    """KiCad Y -> enclosure depth from the front outer face."""
    return (_Y_IN_F + WALL) - y_kicad


def geometry():
    inside = {"x": _X_IN_R - _X_IN_L, "y": _Y_IN_F - _Y_IN_B}
    deepest = max(AT13["height"], ATM13["height"])
    z_floor = WALL
    z_cs = z_floor + FLOOR_GAP + deepest          # board component side (faces the floor)
    z_back = z_cs + THICKNESS                     # board back face (faces the lid)
    z_lid_out = z_back + SURLOK["depth"]
    z_lid_in = z_lid_out - WALL
    outside = {"x": inside["x"] + 2 * WALL, "y": inside["y"] + 2 * WALL, "z": z_lid_out}
    inside["z"] = z_lid_in - z_floor

    outputs = [{"ref": f"J{904 + i}", "label": f"OUT{i + 1}", "x": ex(CX + (i - 2.5) * OUT_PITCH),
                "z": z_cs - AT13["axis"]} for i in range(6)]
    t1s_depth = ey(FRONT - T1S_DEPTH * D)
    t1s = [{"ref": "J903", "label": "T1S upstream", "face": "right", "y": t1s_depth, "z": z_cs - ATM13["axis"]},
           {"ref": "J912", "label": "T1S downstream", "face": "left", "y": t1s_depth, "z": z_cs - ATM13["axis"]}]
    nets = {"J910": "VBAT_IN", "J901": "VBAT_IN", "J911": "GND", "J902": "GND"}
    lid = [{"ref": r, "net": nets[r], "x": ex(x), "y": ey(y)} for r, (x, y) in sorted(LID_TERMINALS.items())]
    return {
        "assumptions": {"wall": WALL, "back_gap": BACK_GAP, "floor_gap": FLOOR_GAP, "edge_gap": EDGE_GAP},
        "outside": outside,
        "inside": inside,
        "board": {"x0": ex(LEFT), "x1": ex(RIGHT), "y0": ey(FRONT), "y1": ey(Y0),
                  "z_component_side": z_cs, "z_back_face": z_back, "thickness": THICKNESS},
        "z": {"floor_inner": z_floor, "lid_inner": z_lid_in, "lid_outer": z_lid_out},
        "outputs": outputs, "t1s": t1s, "lid": lid,
        "parts": {"AT13": AT13, "ATM13": ATM13, "SURLOK": SURLOK},
    }


if __name__ == "__main__":
    print(json.dumps(geometry(), indent=1))
