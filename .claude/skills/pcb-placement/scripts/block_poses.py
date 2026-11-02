#!/usr/bin/env python3
"""Pose tables for hand-reviewed blocks (pcb-placement skill). Run with KiCad's Python.

A critical block (the T1S line interface, a buck, the MCU's crystal) is composed by hand,
reviewed by the user, and from then on held as a pose table: every part's pose relative to
the block's anchor, its role (`core` never moves relative to the anchor; `flex` may slide
up to `flex_mm`) and the reason it sits there. The table, not a board, is the record.

    $KPY block_poses.py extract BOARD --anchor K501 --refs K501,R501,... -o blocks/t1s.poses.json
    $KPY block_poses.py apply   BOARD blocks/t1s.poses.json -o OUT.kicad_pcb [--at X Y --rot R]
    $KPY block_poses.py check   BOARD blocks/t1s.poses.json [blocks/*.poses.json ...]
    $KPY block_poses.py copy    BOARD blocks/out12.poses.json --map 'U601=U701,C601=C701,...' -o blocks/out34.poses.json

`extract` writes the table with empty `why` and every part `core`; fill in each reason and
mark the flexible parts before the block goes to the user. `apply` moves the parts onto a copy
(the anchor stays put unless `--at` gives it a new pose); `check` reports, per part, how far it
is from its table pose (exit 1 when a core part moved or a flex part moved beyond its allowance).
`copy` makes an identical channel's table from a reviewed one by a reference map: the copy is
not reviewed again, only where it differs.

Table format:
{"block": "t1s", "anchor": "K501", "approved": null,
 "anchor_pose": {"x": 151.2, "y": 22.0, "rot": 90, "side": "B"},
 "parts": {"C501": {"dx": 1.2, "dy": -3.4, "rot": 0, "side": "B", "role": "core", "flex_mm": 0,
                    "why": "DC-block cap on the line side of K501, as the TI app note draws it"}}}
dx, dy and rot are in the anchor's frame (rotated with it); side is the part's own face.
"""
import argparse
import json
import math
import sys

import pcbnew


def mm(v):
    return pcbnew.ToMM(v)


def pose(fp):
    return {"x": round(mm(fp.GetPosition().x), 4), "y": round(mm(fp.GetPosition().y), 4),
            "rot": round(fp.GetOrientationDegrees() % 360, 3), "side": "B" if fp.IsFlipped() else "F"}


def to_rel(anchor, p):
    a = math.radians(anchor["rot"])
    dx, dy = p["x"] - anchor["x"], p["y"] - anchor["y"]
    # KiCad's y points down and its angles turn counter-clockwise as seen on screen
    rx = dx * math.cos(a) - dy * math.sin(a)
    ry = dx * math.sin(a) + dy * math.cos(a)
    return round(rx, 4), round(ry, 4), round((p["rot"] - anchor["rot"]) % 360, 3)


def to_abs(anchor, rel):
    a = math.radians(anchor["rot"])
    dx, dy = rel["dx"], rel["dy"]
    x = anchor["x"] + dx * math.cos(a) + dy * math.sin(a)
    y = anchor["y"] - dx * math.sin(a) + dy * math.cos(a)
    return x, y, (anchor["rot"] + rel["rot"]) % 360


def find(board, ref):
    fp = board.FindFootprintByReference(ref)
    if fp is None:
        sys.exit(f"ERROR: {ref} is not on the board")
    return fp


def cmd_extract(a):
    board = pcbnew.LoadBoard(a.board)
    anc = pose(find(board, a.anchor))
    parts = {}
    for ref in a.refs.split(","):
        if ref == a.anchor:
            continue
        p = pose(find(board, ref))
        dx, dy, rot = to_rel(anc, p)
        parts[ref] = {"dx": dx, "dy": dy, "rot": rot, "side": p["side"], "role": "core", "flex_mm": 0, "why": ""}
    table = {"block": a.block or a.anchor.lower(), "anchor": a.anchor, "approved": None,
             "anchor_pose": anc, "parts": parts}
    json.dump(table, open(a.out, "w"), indent=2)
    print(f"wrote {a.out}: {len(parts)} parts round {a.anchor}; fill in every 'why' and mark the flex parts")


def check_table(board, table):
    anc_fp = board.FindFootprintByReference(table["anchor"])
    if anc_fp is None:
        return [{"ref": table["anchor"], "status": "FAIL", "note": "anchor not on the board"}]
    anc = pose(anc_fp)
    rows = [{"ref": table["anchor"], "status": "ok", "note": "anchor"}]
    if anc["side"] != table["anchor_pose"]["side"]:
        rows[0] = {"ref": table["anchor"], "status": "FAIL", "note": "anchor changed side"}
    for ref, rel in table["parts"].items():
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            rows.append({"ref": ref, "status": "FAIL", "note": "not on the board"})
            continue
        p = pose(fp)
        x, y, rot = to_abs(anc, rel)
        d = math.hypot(p["x"] - x, p["y"] - y)
        drot = abs(((p["rot"] - rot) + 180) % 360 - 180)
        allow = 0.01 if rel.get("role", "core") == "core" else float(rel.get("flex_mm", 0))
        bad = d > allow + 1e-6 or (rel.get("role", "core") == "core" and drot > 0.01) or p["side"] != rel["side"]
        rows.append({"ref": ref, "status": "FAIL" if bad else "ok", "moved_mm": round(d, 3), "turned_deg": round(drot, 1),
                     "role": rel.get("role", "core"), "allow_mm": allow,
                     "note": "changed side" if p["side"] != rel["side"] else ""})
    return rows


def cmd_check(a):
    board = pcbnew.LoadBoard(a.board)
    fails = 0
    for path in a.tables:
        t = json.load(open(path))
        rows = check_table(board, t)
        bad = [r for r in rows if r["status"] == "FAIL"]
        fails += len(bad)
        unreasoned = [r for r, v in t["parts"].items() if not v.get("why")]
        print(f"{t['block']}: {len(rows)} parts, {len(bad)} off their table pose; approved {t.get('approved') or 'NOT YET'}")
        for r in bad:
            print(f"  FAIL {r['ref']}: moved {r.get('moved_mm')} mm, turned {r.get('turned_deg')} deg "
                  f"({r.get('role')}, allowed {r.get('allow_mm')} mm) {r.get('note', '')}")
        if unreasoned:
            print(f"  WARN no reason given for: {', '.join(unreasoned)}")
    return 1 if fails else 0


def cmd_apply(a):
    board = pcbnew.LoadBoard(a.board)
    t = json.load(open(a.table))
    anc_fp = find(board, t["anchor"])
    if a.at:
        anc_fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(a.at[0]), pcbnew.FromMM(a.at[1])))
        if a.rot is not None:
            anc_fp.SetOrientationDegrees(a.rot)
    anc = pose(anc_fp)
    for ref, rel in t["parts"].items():
        fp = find(board, ref)
        if (fp.IsFlipped() and rel["side"] == "F") or (not fp.IsFlipped() and rel["side"] == "B"):
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        x, y, rot = to_abs(anc, rel)
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        fp.SetOrientationDegrees(rot)
    board.Save(a.out)
    print(f"wrote {a.out}: {len(t['parts'])} parts placed round {t['anchor']} at ({anc['x']}, {anc['y']}) rot {anc['rot']}."
          " Run check_assembly on it: this moves parts, it does not check them.")


def cmd_copy(a):
    t = json.load(open(a.table))
    m = dict(pair.split("=") for pair in a.map.split(","))
    missing = [r for r in [t["anchor"], *t["parts"]] if r not in m]
    if missing:
        sys.exit(f"ERROR: the map does not name {', '.join(missing)}")
    board = pcbnew.LoadBoard(a.board)
    new = {"block": a.block or t["block"] + "_copy", "anchor": m[t["anchor"]], "approved": None,
           "copied_from": {"table": a.table, "approved": t.get("approved")},
           "anchor_pose": pose(find(board, m[t["anchor"]])),
           "parts": {m[r]: dict(v) for r, v in t["parts"].items()}}
    json.dump(new, open(a.out, "w"), indent=2)
    print(f"wrote {a.out}: copy of {t['block']} round {new['anchor']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract"); e.add_argument("board"); e.add_argument("--anchor", required=True)
    e.add_argument("--refs", required=True); e.add_argument("--block"); e.add_argument("-o", "--out", required=True)
    p = sub.add_parser("apply"); p.add_argument("board"); p.add_argument("table"); p.add_argument("-o", "--out", required=True)
    p.add_argument("--at", type=float, nargs=2); p.add_argument("--rot", type=float)
    c = sub.add_parser("check"); c.add_argument("board"); c.add_argument("tables", nargs="+")
    k = sub.add_parser("copy"); k.add_argument("board"); k.add_argument("table"); k.add_argument("--map", required=True)
    k.add_argument("--block"); k.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    return {"extract": cmd_extract, "apply": cmd_apply, "check": cmd_check, "copy": cmd_copy}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
