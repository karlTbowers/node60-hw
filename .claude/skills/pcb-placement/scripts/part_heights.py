#!/usr/bin/env python3
"""Part heights from each footprint's 3D model body (pcb-placement skill).

A placement's height checks (a lid, the floor under bottom-side parts, a part under a
busbar) are only as good as the heights fed to them. Taking the highest point in a STEP
file is wrong: STEP files also hold axis placements, B-spline control points and
construction points that lie outside the body. On Node60 the relay K501 read 5.58 mm that
way; its body is 5.2 mm (Omron's G6K drawing agrees). This script measures the body:

1. with CadQuery (the library's environment, `~/.cache/dropout/klt-venv/bin/python`, or
   `--cq-python`), tessellating every solid with its assembly transforms applied: the mesh
   vertices lie on the body, curved tops included;
2. without CadQuery, from the B-rep vertices only (CARTESIAN_POINTs that a VERTEX_POINT
   names), which ignores control points but can under-read a domed top and does not apply
   nested assembly transforms (the row says `vertices`, and a WARN says when the file is an
   assembly).

Each row also gives the all-points maximum, so the difference is visible.

    python3 part_heights.py BOARD.kicad_pcb [--refs K501,U401] \
        [--side B --limit 6.17] [--json OUT.json]

Height is measured from the board face the part sits on, outward (a B.Cu part's height is
how far it hangs below the board). The model's offset, scale and x/y rotation from the
footprint are applied. `--limit` lists every part on `--side` taller than the limit.
Exit 1 when a part exceeds `--limit` (or, with `--strict`, has no measurable model); 0 otherwise.
A part with no model (a bare test pad) is listed under NO HEIGHT, never assumed flat.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys

CQ_DEFAULT = os.path.expanduser("~/.cache/dropout/klt-venv/bin/python")

CQ_PROGRAM = r"""
import sys, json, cadquery as cq
out = {}
for path in json.load(sys.stdin):
    try:
        wp = cq.importers.importStep(path)
        vals = wp.vals()
        shape = vals[0] if len(vals) == 1 else cq.Compound.makeCompound(vals)
        verts, _ = shape.tessellate(0.02)
        out[path] = [[v.x, v.y, v.z] for v in verts]
    except Exception as e:
        out[path] = str(e)
json.dump(out, sys.stdout)
"""


def footprints(board_text):
    for m in re.finditer(r'\n\t\(footprint "([^"]+)"([\s\S]*?)\n\t\)', board_text):
        body = m.group(2)
        ref = re.search(r'\(property "Reference" "([^"]+)"', body)
        layer = re.search(r'\(layer "([^"]+)"\)', body)
        models = []
        for mm in re.finditer(r'\(model "([^"]+)"([\s\S]*?)\n\t\t\)', body):
            blk = mm.group(2)
            if re.search(r"\(hide yes\)", blk):
                continue

            def xyz(key, default):
                k = re.search(r"\(" + key + r"\s*\(xyz ([-\d.e]+) ([-\d.e]+) ([-\d.e]+)\)", blk)
                return tuple(float(v) for v in k.groups()) if k else default
            models.append({"path": mm.group(1), "offset": xyz("offset", (0, 0, 0)),
                           "scale": xyz("scale", (1, 1, 1)), "rotate": xyz("rotate", (0, 0, 0))})
        yield (ref.group(1) if ref else "?"), m.group(1), (layer.group(1) if layer else "F.Cu"), models


def expand(path, board_dir):
    env = dict(os.environ)
    env.setdefault("KIPRJMOD", board_dir)
    p = re.sub(r"\$\{([^}]+)\}", lambda m: env.get(m.group(1), m.group(0)), path)
    if not os.path.isabs(p):
        p = os.path.join(board_dir, p)
    if not os.path.exists(p):
        stem = os.path.splitext(p)[0]
        for ext in (".step", ".stp", ".STEP", ".STP"):
            if os.path.exists(stem + ext):
                return stem + ext
    return p


def step_points(path):
    """(vertex points, all points, is_assembly) parsed from the STEP text."""
    text = re.sub(r"\s+", " ", open(path, errors="replace").read())
    scale = 25.4 if re.search(r"CONVERSION_BASED_UNIT\s*\(\s*'INCH'", text) else 1.0
    pts = {}
    for i, c in re.findall(r"#(\d+)\s*=\s*CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\(([^)]*)\)\s*\)", text):
        v = [float(x) for x in c.split(",")]
        if len(v) == 3:
            pts[int(i)] = [x * scale for x in v]
    ids = [int(i) for i in re.findall(r"VERTEX_POINT\s*\(\s*'[^']*'\s*,\s*#(\d+)\s*\)", text)]
    assembly = "NEXT_ASSEMBLY_USAGE_OCCURRENCE" in text
    return [pts[i] for i in ids if i in pts], list(pts.values()), assembly


def transform(points, model):
    sx, sy, sz = model["scale"]
    rx, ry, _ = (math.radians(a) for a in model["rotate"])
    oz = model["offset"][2]
    out = []
    for x, y, z in points:
        x, y, z = x * sx, y * sy, z * sz
        y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
        x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        out.append(z + oz)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--refs", help="comma-separated references (default: every part)")
    ap.add_argument("--side", choices=["F", "B"], help="only parts on this side")
    ap.add_argument("--limit", type=float, help="list parts taller than this (mm), exit 1 if any")
    ap.add_argument("--cq-python", default=CQ_DEFAULT, help="a Python with CadQuery")
    ap.add_argument("--no-cq", action="store_true", help="vertex parse only")
    ap.add_argument("--strict", action="store_true", help="exit 1 when a part has no height")
    ap.add_argument("--json")
    a = ap.parse_args()

    board_dir = os.path.dirname(os.path.abspath(a.board))
    want = set(a.refs.split(",")) if a.refs else None
    parts = []
    for ref, fp, layer, models in footprints(open(a.board, encoding="utf-8").read()):
        side = "B" if layer.startswith("B.") else "F"
        if (want and ref not in want) or (a.side and side != a.side):
            continue
        parts.append({"ref": ref, "footprint": fp, "side": side,
                      "models": [dict(m, file=expand(m["path"], board_dir)) for m in models]})

    files = sorted({m["file"] for p in parts for m in p["models"] if os.path.exists(m["file"])
                    and m["file"].lower().endswith((".step", ".stp"))})
    meshes = {}
    if files and not a.no_cq and os.path.exists(a.cq_python):
        r = subprocess.run([a.cq_python, "-c", CQ_PROGRAM], input=json.dumps(files),
                           capture_output=True, text=True)
        if r.returncode == 0:
            meshes = json.loads(r.stdout)
        else:
            print("WARN: CadQuery run failed, using vertex parse:", r.stderr.strip()[-300:], file=sys.stderr)

    rows, bad = [], 0
    for p in parts:
        best = None
        for m in p["models"]:
            f = m["file"]
            if not os.path.exists(f) or not f.lower().endswith((".step", ".stp")):
                continue
            verts, allp, assembly = step_points(f)
            mesh = meshes.get(f)
            if isinstance(mesh, list) and mesh:
                h, method = max(transform(mesh, m)), "mesh"
            elif verts:
                h, method = max(transform(verts, m)), "vertices" + (" (assembly: WARN)" if assembly else "")
            else:
                continue
            allmax = max(transform(allp, m)) if allp else None
            if best is None or h > best["height_mm"]:
                best = {"height_mm": round(h, 3), "method": method,
                        "all_points_mm": round(allmax, 3) if allmax is not None else None,
                        "model": os.path.relpath(f, board_dir)}
        row = {"ref": p["ref"], "side": p["side"], "footprint": p["footprint"]}
        if best:
            row.update(best)
        else:
            row["height_mm"] = None
            row["method"] = "no model" if not p["models"] else "model not found or not STEP"
            bad += 1
        rows.append(row)

    rows.sort(key=lambda r: -(r["height_mm"] or 0))
    over = [r for r in rows if a.limit is not None and r["height_mm"] is not None and r["height_mm"] > a.limit]
    shown = over if a.limit is not None else rows
    print(f"{'ref':8} side  height  all-pts  method              model")
    for r in shown:
        h = f"{r['height_mm']:.2f}" if r["height_mm"] is not None else "  -  "
        ap_ = f"{r['all_points_mm']:.2f}" if r.get("all_points_mm") is not None else "  -  "
        print(f"{r['ref']:8} {r['side']:4}  {h:>6}  {ap_:>7}  {r['method']:18}  {r.get('model', '')}")
    missing = [r["ref"] for r in rows if r["height_mm"] is None]
    if missing:
        print(f"NO HEIGHT ({len(missing)}): {', '.join(missing)}  -> take each from its datasheet, cite it")
    if a.limit is not None:
        print(f"{len(over)} part(s) on side {a.side or 'F+B'} taller than {a.limit} mm")
    if a.json:
        json.dump(rows, open(a.json, "w"), indent=2)
    return 1 if over or (a.strict and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
