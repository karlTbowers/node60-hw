#!/usr/bin/env python3
"""Write the T1S line's hand route as a draw_t1s.py spec (Node60, 2026-11-05; user: "route the T1S
trunk with the PHY pair"). Plain Python; every coordinate is derived here, so edit this, not the JSON.

Trunk on F.Cu, coupled 0.165/0.15 mm about y 46 (N north, P south): at J912 N passes north of P's pin,
at J903 P passes south of N's pin (the AT13 pins put N west of P at both ends). ESD: D504 (N) and D501
(P) on a via in their pad; D503 (P) and D502 (N) on B.Cu from their connector pin. The PHY's and the
relay's taps leave the trunk west of U501 (B.Cu is clear there; under the trunk at x 153.5-158.5 are
U501's pins) through one via per line onto In2, run as a pair to C511/C512 (a via in pad 2 of each),
and continue on B.Cu to K501 pins 3 and 6. CMC pair C511/C512 pad 1 to FL501 pins 4/3 on B.Cu. PHY pair
FL501 pins 1/2 to U501 pins 30/31: they cross once (FL501's P winding sits west, U501's P pin east),
P hopping over N on F.Cu through two vias. Moves: C502 (VDDA decap) off the trunk's line to
(156.76, 47.3) on F.Cu, its pad 1 on a 3V3 via that also takes U501 pin 29 (VDDA) on B.Cu; the REFCLK
via 0.25 mm east to make room. TXD0 and the corridor's power vias are deleted here (KRT and
draw_power.py redraw them).
"""
import json
import math
import sys

W = 0.165                 # T1S pair width (class T1S_100R)
G = 0.15                  # pair gap
H = (W + G) / 2           # half pitch: lines at y 46 -/+ H
YN, YP = 46 - H, 46 + H
V = {"size": 0.35, "drill": 0.2}


def via(net, x, y):
    return dict(V, net=net, at=[round(x, 4), round(y, 4)])


def trk(net, layer, pts, w=W):
    return {"net": net, "layer": layer, "width": w, "points": [[round(x, 4), round(y, 4)] for x, y in pts]}


def length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def offset_path(c, h):
    """the polyline c offset by h to its left-hand side seen along it in board coordinates (y down:
    for a path heading south (+y), +h is west); miter joins"""
    def norm(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        return (-dy / L, dx / L)                    # rotate (dx, dy) by -90 degrees: south -> east
    segs = []
    for a, b in zip(c, c[1:]):
        n = norm(a, b)
        segs.append(((a[0] + h * n[0], a[1] + h * n[1]), (b[0] + h * n[0], b[1] + h * n[1])))
    out = [segs[0][0]]
    for (a1, b1), (a2, b2) in zip(segs, segs[1:]):
        d1 = (b1[0] - a1[0], b1[1] - a1[1]); d2 = (b2[0] - a2[0], b2[1] - a2[1])
        den = d1[0] * d2[1] - d1[1] * d2[0]
        t = ((a2[0] - a1[0]) * d2[1] - (a2[1] - a1[1]) * d2[0]) / den
        out.append((a1[0] + t * d1[0], a1[1] + t * d1[1]))
    out.append(segs[-1][1])
    return out


def main(out):
    tracks, vias = [], []
    # trunk: straight and coupled from x 140.35 to 169.65; fans out to the pins without running parallel
    S = 0.45                                              # tap stub: trunk line to its via
    if SWAP:      # FL501/K501 swapped (user, 2026-11-05): P east along the chain, N's via straight above its In2 line
        XN, XP = TAP_XP, 149.815
    else:
        XN = 149.815                                      # N's tap via straight above its In2 line
        XP = TAP_XP
    n_trunk = [(133.4, 46.0), (134.75, 44.65), (138.4, 44.65), (139.86, 45.35), (139.86 + (YN - 45.35), YN), (XN, YN), (171.4, YN)]
    p_trunk = [(138.6, YP), (XP, YP), (169.65, YP), (170.53, 46.7), (171.5, 47.35), (175.25, 47.35), (176.6, 46.0)]
    tracks += [trk("/T1S_N", "F.Cu", n_trunk), trk("/T1S_P", "F.Cu", p_trunk)]
    vias += [via("/T1S_N", 139.86, 45.35), via("/T1S_P", 170.53, 46.7)]            # D504, D501 in pad
    tracks += [trk("/T1S_P", "B.Cu", [(137.6, 46.0), (138.3, 46.7), (139.47, 46.7)]),   # D503
               trk("/T1S_N", "B.Cu", [(172.4, 46.0), (170.8, 46.0), (170.14, 45.35)])]   # D502, clear of TXD1
    # taps: a via on a 0.45 mm stub off each line, P south of the trunk, N north; then In2 as a pair
    tracks += [trk("/T1S_P", "F.Cu", [(XP, YP), (XP, YP + S)]), trk("/T1S_N", "F.Cu", [(XN, YN), (XN, YN - S)])]
    vias += [via("/T1S_P", XP, YP + S), via("/T1S_N", XN, YN - S)]
    # the pair's centre line: south at x XN - H, south-east until its centre reaches x 155, south, split
    cx = XN + H if SWAP else XN - H
    y3 = 54.3
    y2 = y3 - 0.3
    y1 = y2 - (155.0 - cx)
    centre = [(cx, 47.6), (cx, y1), (155.0, y2), (155.0, y3)]
    west, east = offset_path(centre, H), offset_path(centre, -H)   # west / south-west, east / north-east
    if SWAP:
        # P east: its via south of the trunk jogs west onto its line; N straight down from its via
        p_tap = [(XP, YP + S), (XP, YP + S + 0.5), (east[0][0], YP + S + 0.5 + (XP - east[0][0]))] + east[1:] + [(156.25, y3 + (156.25 - 155.0 - H)), (156.25, 56.1)]
        n_tap = [(XN, YN - S), (XN, 47.8)] + west[1:] + [(153.75, y3 + (155.0 - H - 153.75)), (153.75, 56.1)]
        xp_cap, xn_cap, xp_k, xn_k = 156.25, 153.75, 158.5, 151.5      # C511 east, C512 west; K501 pin 6 (P), 3 (N)
    else:
        p_tap = [(XP, YP + S), (XP, YP + S + 0.5), (west[0][0], YP + S + 0.5 + (west[0][0] - XP))] + west[1:] + [(153.75, y3 + (155.0 - H - 153.75)), (153.75, 56.1)]
        # N's lead-in split above T1S_COUPLED_IN2, which starts at y 48.0, so only the coupled part is checked
        n_tap = [(XN, YN - S), (XN, 47.8)] + east[1:] + [(156.25, y3 + (156.25 - 155.0 - H)), (156.25, 56.1)]
        xp_cap, xn_cap, xp_k, xn_k = 153.75, 156.25, 151.5, 158.5
    tracks += [trk("/T1S_P", "In2.Cu", p_tap), trk("/T1S_N", "In2.Cu", n_tap)]
    vias += [via("/T1S_P", xp_cap, 56.1), via("/T1S_N", xn_cap, 56.1)]              # C511/C512 pad 2
    tracks += [trk("/T1S_P", "B.Cu", [(xp_cap, 56.1), (xp_cap, 62.73), (xp_k, 62.73)]),   # K501's P pole
               trk("/T1S_N", "B.Cu", [(xn_cap, 56.1), (xn_cap, 62.73), (xn_k, 62.73)])]   # K501's N pole
    if SWAP:
        # CMC pair: cap pad 1 to FL501 3 (P) / 4 (N); PHY pair straight from FL501 2 (P) / 1 (N) to U501 30 / 31
        tracks += [trk("/T1S/T1S_CMC_P", "B.Cu", [(156.25, 52.6), (155.5, 51.85)]),
                   trk("/T1S/T1S_CMC_N", "B.Cu", [(153.75, 52.6), (154.5, 51.85)])]
        tracks += [trk("/T1S/T1S_PHY_P", "B.Cu", [(155.5, 47.9), (155.5, 47.4), (155.25, 47.15), (155.25, 46.3)]),
                   trk("/T1S/T1S_PHY_N", "B.Cu", [(154.5, 47.9), (154.5, 47.4), (154.75, 47.15), (154.75, 46.3)])]
    else:
        # CMC pair: cap pad 1 to FL501 4 (P) / 3 (N)
        tracks += [trk("/T1S/T1S_CMC_P", "B.Cu", [(153.75, 52.6), (154.5, 51.85)]),
                   trk("/T1S/T1S_CMC_N", "B.Cu", [(156.25, 52.6), (155.5, 51.85)])]
        # PHY pair: N on B.Cu, P over it on F.Cu
        tracks += [trk("/T1S/T1S_PHY_N", "B.Cu", [(154.75, 46.3), (154.75, 47.15), (155.5, 47.9)]),
                   trk("/T1S/T1S_PHY_P", "B.Cu", [(155.25, 46.3), (155.25, 46.85)]),
                   trk("/T1S/T1S_PHY_P", "F.Cu", [(155.25, 46.85), (154.5, 48.0)])]
        vias += [via("/T1S/T1S_PHY_P", 155.25, 46.85), via("/T1S/T1S_PHY_P", 154.5, 48.0)]
    # VDDA: pin 29 to a 3V3 via in C502's pad 1 (C502 on F.Cu, upright); REFCLK via moved east
    tracks += [dict(trk("3V3_MAIN", "B.Cu", [(155.75, 46.3), (155.75, 46.75), (156.3, 47.3)], 0.2), locked=False),
               trk("/T1S/T1S_REFCLK", "B.Cu", [(156.75, 46.0), (157.0, 47.35)], 0.15),
               trk("/T1S/T1S_REFCLK", "In2.Cu", [(157.0, 47.35), (156.8, 46.0)], 0.15)]
    vias += [via("/T1S/T1S_REFCLK", 157.0, 47.35)]      # the VDDA via is draw_power.py's (a "points" entry)
    moves = {"C502": {"x": 156.3, "y": 47.76, "rot": C502_ROT, "side": "F"}}
    if SWAP:      # the P-side parts change sides with P: C511 (P) east, C512 west; the termination resistors swap
        moves.update({"C511": {"x": 156.25, "y": 54.65, "rot": -90.0, "side": "B"}, "C512": {"x": 153.75, "y": 54.65, "rot": -90.0, "side": "B"},
                      "R516": {"x": 161.0, "y": 66.75, "rot": 90.0, "side": "B"}, "R517": {"x": 161.0, "y": 62.0, "rot": 90.0, "side": "B"},
                      "R518": {"x": 149.0, "y": 66.5, "rot": 90.0, "side": "B"}, "R519": {"x": 149.0, "y": 61.5, "rot": 90.0, "side": "B"}})
    spec = {
        "moves": moves,
        "delete": [{"net": "3V3_MAIN", "rect": [154.8, 45.8, 155.2, 47.0]},        # C502's old track and via
                   {"net": "3V3_MAIN", "rect": [152.2, 46.9, 152.4, 47.1]},        # C507's pad via (corridor)
                   {"net": "3V3_MAIN", "rect": [164.15, 46.1, 164.35, 46.3]},      # R506's pad via (corridor)
                   {"net": "/T1S/T1S_REFCLK", "rect": [156.7, 46.05, 156.8, 47.5]},  # REFCLK via, its B and In2 stubs
                   {"net": "/RMII0_T1S_TXD0"}]                                     # re-routed by KRT
                  + ([{"net": n} for n in ("/T1S_P", "/T1S_N", "/T1S/T1S_CMC_P", "/T1S/T1S_CMC_N", "/T1S/T1S_PHY_P",
                                           "/T1S/T1S_PHY_N", "/T1S/T1S_P_DROP", "/T1S/T1S_P_END", "/T1S/T1S_N_DROP",
                                           "/T1S/T1S_N_END", "/T1S/T1S_TERM_CT", "/T1S/T1S_TERM_COIL_S",
                                           "/T1S/T1S_TERM_COIL_R", "/T1S_TERM_DROP", "/T1S_TERM_END")] if SWAP else []),
        "tracks": tracks, "vias": vias,
        "areas": [{"name": "T1S_PINS_U501", "layers": ["B.Cu"], "rect": [154.0, 45.5, 156.55, 47.55]},
                  {"name": "T1S_COUPLED_F", "layers": ["F.Cu"], "rect": [140.6, 45.6, 169.4, 46.4]},
                  {"name": "T1S_COUPLED_IN2", "layers": ["In2.Cu"], "rect": [cx - 0.4, 48.0, 155.4, y2 + 0.1]}],
    }
    json.dump(spec, open(out, "w"), indent=1)
    lp, ln = length(p_tap) + S, length(n_tap) + S
    print(f"{out}: {len(tracks)} tracks, {len(vias)} vias; taps (stub + In2, vias apart) P {lp:.2f} mm, N {ln:.2f} mm")


TAP_XP = float(sys.argv[2]) if len(sys.argv) > 2 else 149.0
C502_ROT = float(sys.argv[3]) if len(sys.argv) > 3 else 90.0
SWAP = len(sys.argv) > 4 and sys.argv[4] == "swap"      # FL501/K501 swapped (needs swap_pins.py on the board)


if __name__ == "__main__":
    main(sys.argv[1])
