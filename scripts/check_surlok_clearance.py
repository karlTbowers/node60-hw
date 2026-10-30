#!/usr/bin/env python3
"""Check that all four SurLok Plus right-angle plugs on the lid fit together.

Each plug may point west, north or east (the SLPRATPS receptacles have no
keyway and the plug rotates 360°). The script tries all 3^4 combinations and
checks, in the lid plane, every plug against every other plug and against every
other receptacle's flange, with CLEARANCE between them. A plug pointing west or
east must also end inside the board outline, so it stays within the enclosure
walls (user, 2026-10-30); a plug pointing north may overhang the back.

Envelopes (Amphenol SurLok Plus catalog IC-10, Gen 1.0, 5.7 mm):
  right-angle plug  p. 7: D = 18 wide, B = 55.1 long; the head is round on the
                    mating axis, so the plug reaches D/2 behind the axis and
                    B - D/2 ahead of it, in the cable direction
  receptacle flange p. 6: D = 27 square

Run with any Python 3:  python3 scripts/check_surlok_clearance.py
Exits non-zero if any combination collides.
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from place_connectors import LEFT, LID_TERMINALS, RIGHT  # noqa: E402

PLUG_W, PLUG_L = 18.0, 55.1
FLANGE = 27.0
CLEARANCE = 3.0

# Directions in the enclosure plan seen from above the lid: x east, y south
# (KiCad Y grows toward the front face, which is south).
DIRS = {"W": (-1, 0), "N": (0, -1), "E": (1, 0)}


def plug_box(x, y, d):
    dx, dy = DIRS[d]
    back, ahead, half = PLUG_W / 2, PLUG_L - PLUG_W / 2, PLUG_W / 2
    if dx:
        x0, x1 = sorted((x - dx * back, x + dx * ahead))
        return x0, y - half, x1, y + half
    y0, y1 = sorted((y - dy * back, y + dy * ahead))
    return x - half, y0, x + half, y1


def flange_box(x, y):
    h = FLANGE / 2
    return x - h, y - h, x + h, y + h


def gap(a, b):
    """Separation between two axis-aligned boxes (negative = overlap)."""
    dx = max(a[0] - b[2], b[0] - a[2])
    dy = max(a[1] - b[3], b[1] - a[3])
    return max(dx, dy)


def main():
    refs = sorted(LID_TERMINALS)
    worst = (float("inf"), None)
    failures = 0
    for combo in itertools.product(DIRS, repeat=len(refs)):
        dirs = dict(zip(refs, combo))
        plugs = {r: plug_box(*LID_TERMINALS[r], dirs[r]) for r in refs}
        for a in refs:
            if dirs[a] in "WE":
                g = min(plugs[a][0] - LEFT, RIGHT - plugs[a][2])
                if g < worst[0]:
                    worst = (g, f"{a} {dirs[a]} to the board edge")
                if g < 0:
                    failures += 1
                    print(f"FAIL {a} {dirs[a]} passes the board edge by {-g:.1f} mm")
            for b in refs:
                if a == b:
                    continue
                for what, box in (("plug", plugs[b]), ("flange", flange_box(*LID_TERMINALS[b]))):
                    if what == "plug" and a > b:
                        continue
                    g = gap(plugs[a], box)
                    if g < worst[0]:
                        worst = (g, f"{a} {dirs[a]} vs {b} {what}" + (f" {dirs[b]}" if what == "plug" else ""))
                    if g < CLEARANCE:
                        failures += 1
                        print(f"FAIL {a} {dirs[a]} vs {b} {what}: {g:.1f} mm")
    n = 3 ** len(refs)
    print(f"{n} combinations, {failures} failures; tightest {worst[0]:.1f} mm ({worst[1]})")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
