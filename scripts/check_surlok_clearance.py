#!/usr/bin/env python3
"""Check that all four SurLok Plus right-angle plugs on the lid fit together, in every version.

Each version lists the directions its plugs may point (enclosure_geometry: plug_dirs):
west, north and east on a flat lid; outward or north where a raised section would block
an inward plug. The SLPRATPS receptacles have no keyway and the plug rotates 360°. The
script tries every combination of every version and checks,
in the lid plane, every plug against every other plug, every other receptacle's flange
and the raised lid sections, with CLEARANCE between them; each flange must also stay
FLANGE_CLEAR from the raised sections and from each other, and the cable leaving each plug, run straight on,
must pass CABLE_CLEAR beside every raised section in plan (a cable passing over a raised
section would rest on its edge). A plug pointing west or east must also end
inside the board outline, so it stays within the enclosure walls (user, 2026-10-30); a
plug pointing north may overhang the back.

Envelopes (Amphenol SurLok Plus catalog IC-10, Gen 1.0, 5.7 mm):
  right-angle plug  p. 7: D = 18 wide, B = 55.1 long; the head is round on the
                    mating axis, so the plug reaches D/2 behind the axis and
                    B - D/2 ahead of it, in the cable direction
  receptacle flange p. 6: D = 27 square

Geometry from enclosure_geometry.spec() (enclosure frame: x east, y north from the front).
Run with any Python 3:  python3 scripts/check_surlok_clearance.py [v2 ...]
Exits non-zero if any combination of any version collides.
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from enclosure_geometry import spec  # noqa: E402
from place_connectors import VERSIONS  # noqa: E402

PLUG_W, PLUG_L = 18.0, 55.1
FLANGE = 27.0
CLEARANCE = 3.0
FLANGE_CLEAR = 2.0    # receptacle flange to the riser of a raised section: room for the gasket and a tool
CABLE_D = 11.0        # 25 mm² cable outside diameter: ASSUMED (typical 25 mm² flexible cable); confirm with the cable
CABLE_RUN = 150.0     # cable checked this far past the plug, straight on, which is well past any wall
CABLE_CLEAR = 2.0     # cable to a raised section, in plan; it may sag or be routed, so less than a rigid body
DIRS = {"W": (-1, 0), "N": (0, 1), "E": (1, 0)}


def plug_box(x, y, d):
    dx, dy = DIRS[d]
    back, ahead, half = PLUG_W / 2, PLUG_L - PLUG_W / 2, PLUG_W / 2
    if dx:
        x0, x1 = sorted((x - dx * back, x + dx * ahead))
        return x0, y - half, x1, y + half
    y0, y1 = sorted((y - dy * back, y + dy * ahead))
    return x - half, y0, x + half, y1


def cable_box(x, y, d):
    """The cable leaving a plug, from the plug's end straight on for CABLE_RUN."""
    dx, dy = DIRS[d]
    start, h = PLUG_L - PLUG_W / 2, CABLE_D / 2
    if dx:
        x0, x1 = sorted((x + dx * start, x + dx * (start + CABLE_RUN)))
        return x0, y - h, x1, y + h
    y0, y1 = sorted((y + dy * start, y + dy * (start + CABLE_RUN)))
    return x - h, y0, x + h, y1


def flange_box(x, y):
    h = FLANGE / 2
    return x - h, y - h, x + h, y + h


def gap(a, b):
    """Separation between two axis-aligned boxes (negative = overlap)."""
    return max(max(a[0] - b[2], b[0] - a[2]), max(a[1] - b[3], b[1] - a[3]))


def check_version(vid, quiet=False):
    """Check one version; returns {combinations, failures, tightest, where}."""
    s = spec(vid)
    cuts = [c for c in s["cutouts"] if c["type"] == "SURLOK"]
    lid = {c["ref"]: (c["x"], c["y"]) for c in cuts}
    allowed = {c["ref"]: c["plug_dirs"] for c in cuts}
    hoods = [(r["label"], (r["x0"], r["y0"], r["x1"], r["y1"])) for r in s.get("raised", [])]
    bx0, bx1 = s["board"]["x0"], s["board"]["x1"]
    refs = sorted(lid)
    worst, failures, n = (float("inf"), None), 0, 0
    for combo in itertools.product(*(allowed[r] for r in refs)):
        n += 1
        dirs = dict(zip(refs, combo))
        plugs = {r: plug_box(*lid[r], dirs[r]) for r in refs}
        checks = [(gap(flange_box(*lid[a]), box), FLANGE_CLEAR, f"{a} flange vs {label}")
                  for a in refs for label, box in hoods]
        checks += [(gap(flange_box(*lid[a]), flange_box(*lid[b])), FLANGE_CLEAR, f"{a} flange vs {b} flange")
                   for a in refs for b in refs if a < b]
        for a in refs:
            if dirs[a] in "WE":
                checks.append((min(plugs[a][0] - bx0, bx1 - plugs[a][2]), 0.0, f"{a} {dirs[a]} to the board edge"))
            for label, box in hoods:
                checks.append((gap(plugs[a], box), CLEARANCE, f"{a} {dirs[a]} vs {label}"))
                checks.append((gap(cable_box(*lid[a], dirs[a]), box), CABLE_CLEAR, f"{a} {dirs[a]} cable vs {label}"))
            for b in refs:
                if a == b:
                    continue
                checks.append((gap(plugs[a], flange_box(*lid[b])), CLEARANCE, f"{a} {dirs[a]} vs {b} flange"))
                if a < b:
                    checks.append((gap(plugs[a], plugs[b]), CLEARANCE, f"{a} {dirs[a]} vs {b} plug {dirs[b]}"))
        for g, need, what in checks:
            if g < worst[0]:
                worst = (g, what)
            if g < need:
                failures += 1
                if not quiet:
                    print(f"{vid} FAIL {what}: {g:.1f} mm (needs {need:g})")
    if not quiet:
        print(f"{vid}: {n} combinations, {failures} failures; tightest {worst[0]:.1f} mm ({worst[1]})")
    return {"combinations": n, "failures": failures, "tightest": round(worst[0], 2), "where": worst[1]}


def main(argv):
    failures = sum(check_version(v)["failures"] for v in (argv[1:] or VERSIONS))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main(sys.argv)
