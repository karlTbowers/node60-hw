#!/usr/bin/env python3
"""Check that each version's boards can be fitted into one-piece walls, one board at a time.

A header's shroud passes through a closed cutout in its wall, so a board can only go in by
sliding toward that wall, by the shroud's length past the flange face plus the insertion
clearance: lowered in that far from its place, then slid home. So:

  - a board with headers on two different one-piece walls can't be fitted (it would need a
    split case); a wall made as a separate panel (spec "removable") is fitted after the board,
    slid onto its headers' shrouds, so it doesn't count;
  - lowered, a board must fit inside the walls (or reach out where a panel is still off);
  - sliding, it passes over its standoffs, so a strip that long beside each mounting hole must
    stay free of parts on its underside;
  - lowered and slid, it must clear the headers of the boards already in (lowest board first),
    through its notches;
  - a board that drops onto a mezzanine after sliding needs cutouts that much taller.

Geometry from enclosure_geometry.spec() (x east, y north from the front, inner walls at
`wall` from the outside). Run with any Python 3:  python3 scripts/check_assembly.py [v8 ...]
Exits non-zero if a version that should fit doesn't.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from enclosure_geometry import spec  # noqa: E402
from place_connectors import VERSIONS  # noqa: E402

TOWARD = {"front": (0, -1), "back": (0, 1), "left": (-1, 0), "right": (1, 0)}
WALL_NAME = {"front": "south", "back": "north", "left": "west", "right": "east"}


def body_box(s, c):
    """Plan box of a wall header's body, from its flange face (the inner wall) inward."""
    p, w, o = s["parts"][c["type"].split("_")[0]], s["wall"], s["outside"]
    depth, half = p["panel"] + p["back"], p["along_half"]
    if c["face"] in ("front", "back"):
        y0, y1 = (w, w + depth) if c["face"] == "front" else (o["y"] - w - depth, o["y"] - w)
        return c["x"] - half, y0, c["x"] + half, y1
    x0, x1 = (w, w + depth) if c["face"] == "left" else (o["x"] - w - depth, o["x"] - w)
    return x0, c["y"] - half, x1, c["y"] + half


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def check_version(vid, quiet=False):
    """{fits, steps, problems} for one version."""
    s = spec(vid)
    w, o = s["wall"], s["outside"]
    boards = [{**b, "label": b["label"]} for b in s["boards"]] + [{**s["board"], "label": "main board"}]
    boards.sort(key=lambda b: b["z0"])                      # lowest first
    heads = [c for c in s["cutouts"] if c["face"] in TOWARD]
    removable = set(s.get("removable", []))
    on = lambda b: [c for c in heads if c.get("board", "main") == ("main" if b["label"] == "main board" else b["label"])]
    steps, problems, fitted = [], [], []
    for b in boards:
        faces = sorted({c["face"] for c in on(b)} - removable)
        if len(faces) > 1:
            names = [WALL_NAME[f] for f in faces]
            problems.append(f'{b["label"]}: headers on the {", ".join(names[:-1])} and {names[-1]} walls, so it '
                            "can't be fitted into one-piece walls")
            continue
        dx = dy = travel = 0.0
        if faces:
            travel = max(s["parts"][c["type"].split("_")[0]]["shroud"] for c in on(b) if c["face"] == faces[0])
            travel += s["insert"]["clear"]
            dx, dy = TOWARD[faces[0]]
        lowered = (b["x0"] - dx * travel, b["y0"] - dy * travel, b["x1"] - dx * travel, b["y1"] - dy * travel)
        lim = [-1e9 if "left" in removable else w, -1e9 if "front" in removable else w,
               1e9 if "right" in removable else o["x"] - w, 1e9 if "back" in removable else o["y"] - w]
        if lowered[0] < lim[0] or lowered[1] < lim[1] or lowered[2] > lim[2] or lowered[3] > lim[3]:
            problems.append(f'{b["label"]}: lowered {travel:.1f} mm from its place, it doesn\'t fit inside the walls')
        notches = b.get("notches", [])
        for c in (c for f in fitted for c in on(f)):
            box = body_box(s, c)
            for k in range(11):                             # along the slide, lowered to home
                t = travel * (1 - k / 10)
                at = (b["x0"] - dx * t, b["y0"] - dy * t, b["x1"] - dx * t, b["y1"] - dy * t)
                big = 1e9                                   # a notch is open past the board edge it cuts
                holes = [(n["x0"] - dx * t if n["x0"] > b["x0"] else -big, n["y0"] - dy * t if n["y0"] > b["y0"] else -big,
                          n["x1"] - dx * t if n["x1"] < b["x1"] else big, n["y1"] - dy * t if n["y1"] < b["y1"] else big)
                         for n in notches]
                inside = any(h[0] <= box[0] and h[1] <= box[1] and box[2] <= h[2] and box[3] <= h[3] for h in holes)
                if overlap(at, box) and not inside:
                    problems.append(f'{b["label"]}: hits {c["ref"]} {t:.1f} mm from its place')
                    break
        drop = s["insert"]["drop"] if b["label"] == "main board" else 0.0
        for c in on(b):
            t, base = s["cutout_types"][c["type"]], s["cutout_types"][c["type"].split("_")[0]]
            if t["total"] - base["total"] < drop - 1e-9:
                problems.append(f'{c["ref"]}: cutout not {drop:g} mm taller for the mezzanine drop')
        how = f'lowered {travel:.1f} mm {"north south east west".split()[[(0, 1), (0, -1), (1, 0), (-1, 0)].index((-dx, -dy))]} of its place, slid {WALL_NAME[faces[0]]} into the wall' if faces else "lowered straight in"
        steps.append(f'{b["label"][0].upper() + b["label"][1:]}: {how}' + (f", then dropped {drop:g} mm onto the mezzanine" if drop else "")
                     + (f'; keep a {travel:.1f} mm strip on the {WALL_NAME[faces[0]]} side of each mounting hole '
                        "free of parts on the underside (it slides over its standoffs)" if faces and removable else ""))
        fitted.append(b)
    for f in sorted(removable):
        refs = [c["ref"] for c in heads if c["face"] == f]
        if refs:
            t = max(s["parts"][c["type"].split("_")[0]]["shroud"] for c in heads if c["face"] == f) + s["insert"]["clear"]
            away = {"back": "south", "front": "north", "left": "east", "right": "west"}[f]
            steps.append(f'{WALL_NAME[f].capitalize()} panel: slid {t:.1f} mm {away} onto the shrouds of '
                         f'{", ".join(refs)}, then bolted to the floor and side walls with a gasket')
        else:
            steps.append(f"{WALL_NAME[f].capitalize()} panel: fitted, bolted to the floor and side walls with a gasket")
    out = {"fits": not problems, "steps": steps, "problems": [p[0].upper() + p[1:] for p in problems]}
    if not quiet:
        print(f'{vid}: {"fits" if out["fits"] else "does not fit"}')
        for line in (out["steps"] if out["fits"] else out["problems"]):
            print(f"  {line}")
    return out


def main(argv):
    results = {v: check_version(v) for v in (argv[1:] or VERSIONS)}
    bad = [v for v, r in results.items() if not r["fits"] and VERSIONS[v].get("insert") == "boards"]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv)
