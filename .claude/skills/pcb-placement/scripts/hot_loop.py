#!/usr/bin/env python3
"""Switching-stage placement check against its datasheet, read-only (pcb-placement skill).

Run with KiCad's Python. For each switcher in a spec, measured on the placed board, before
any copper exists:

- the HF input cap across VIN and PGND: on the IC's side, pad edge to the nearest VIN pin and
  from its ground pad to the nearest PGND pin, and the loop's plan area (cap VIN pad, VIN pin,
  PGND pin, cap ground pad, as a polygon of pad centres; the copper loop is larger); the
  stage's other input caps are listed with their gaps;
- the inductor: pad edge from its switch-node pad to the nearest SW pin, and its side;
- the feedback parts (on the FB net): pad edge to the FB pin, and their distance from the
  switch node (SW pads and the inductor's body);
- other parts of foreign nets inside the loop polygon.

The limits come from the datasheet's layout section and are written in the spec with their
source, never invented. Parts are found from the IC's pins by net: input caps are the
two-pad parts with one pad on a VIN pin's net and one on a PGND pin's net.

    $KPY hot_loop.py BOARD.kicad_pcb SPEC.json [--json OUT]

SPEC.json is a list:
  [{"name": "U302 3V3_MAIN buck", "ic": "U302",
    "source": "TI LMQ66430-Q1 datasheet SNVSxxx, 11.1 Layout Guidelines, Figure 11-1",
    "vin": ["3"], "pgnd": ["6", "13", "15"], "sw": ["7"], "fb": ["11"],
    "hf_cap": "C303", "input_caps": ["C303", "C304"],
    "limits": {"cin_gap_mm": 1.0, "loop_area_mm2": 6.0, "l_gap_mm": 1.5,
               "fb_gap_mm": 2.0, "fb_from_sw_mm": 2.0}}]
`hf_cap` names the high-frequency input cap the datasheet puts across the pins (default: the
cap with the smallest loop); `input_caps` lists the stage's input caps (default: every cap
across VIN and PGND within `search_mm`, 10, of the IC: name them when two stages share an
input rail). Leave `fb` out on a fixed-output part whose FB pin is the output rail. Any limit
left out is reported, not graded. Exit 1 on any FAIL.
"""
import argparse
import json
import math
import sys

import pcbnew


def mm(v):
    return pcbnew.ToMM(v)


def box(item):
    b = item.GetBoundingBox()
    return mm(b.GetLeft()), mm(b.GetTop()), mm(b.GetRight()), mm(b.GetBottom())


def gap(a, b):
    ax0, ay0, ax1, ay1 = box(a)
    bx0, by0, bx1, by1 = box(b)
    return math.hypot(max(bx0 - ax1, ax0 - bx1, 0), max(by0 - ay1, ay0 - by1, 0))


def centre(p):
    return mm(p.GetPosition().x), mm(p.GetPosition().y)


def area(poly):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))) / 2


def inside(pt, poly):
    x, y = pt
    c = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            c = not c
    return c


def grade(value, limit, smaller_is_better=True):
    if limit is None or value is None:
        return "info"
    return "PASS" if (value <= limit if smaller_is_better else value >= limit) else "FAIL"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("spec")
    ap.add_argument("--json")
    a = ap.parse_args()
    board = pcbnew.LoadBoard(a.board)
    specs = json.load(open(a.spec))
    out, fails = [], 0

    for s in specs:
        ic = board.FindFootprintByReference(s["ic"])
        lim = s.get("limits", {})
        pins = {k: [p for p in ic.Pads() if p.GetNumber() in s.get(k, [])] for k in ("vin", "pgnd", "sw", "fb")}
        nets = {k: {p.GetNetname() for p in v} for k, v in pins.items()}
        rows = []

        def row(what, value, limit, unit="mm", note=""):
            g = grade(value, limit)
            rows.append({"check": what, "value": None if value is None else round(value, 2),
                         "limit": limit, "unit": unit, "grade": g, "note": note})

        caps, inductors, fbparts = [], [], []
        for fp in board.GetFootprints():
            if fp.GetReference() == s["ic"]:
                continue
            pn = [p.GetNetname() for p in fp.Pads()]
            if len(pn) == 2 and set(pn) & nets["vin"] and set(pn) & nets["pgnd"]:
                caps.append(fp)
            elif fp.GetReference().startswith("L") and set(pn) & nets["sw"]:
                inductors.append(fp)
            elif set(pn) & nets["fb"]:
                fbparts.append(fp)

        caps = [c for c in caps if c.GetReference() in s["input_caps"]] if "input_caps" in s else \
            [c for c in caps if gap(c, ic) <= s.get("search_mm", 10.0)]
        loops = {}
        for c in caps:
            cv = next(p for p in c.Pads() if p.GetNetname() in nets["vin"])
            cg = next(p for p in c.Pads() if p.GetNetname() in nets["pgnd"])
            vpin = min(pins["vin"], key=lambda p: gap(cv, p))
            gpin = min(pins["pgnd"], key=lambda p: gap(cg, p))
            loops[c.GetReference()] = (c, cv, cg, vpin, gpin, [centre(cv), centre(vpin), centre(gpin), centre(cg)])
        if not loops:
            row("input cap across VIN and PGND", None, None, "", "none found within reach of the IC")
            rows[-1]["grade"] = "FAIL"
        else:
            hf = s.get("hf_cap") or min(loops, key=lambda r: area(loops[r][5]))
            c, cv, cg, vpin, gpin, poly = loops[hf]
            row(f"HF cap {hf} on the IC's side", None, None, "",
                "yes" if c.GetLayer() == ic.GetLayer() else "NO: the loop needs vias")
            if c.GetLayer() != ic.GetLayer():
                rows[-1]["grade"] = "FAIL"
            row(f"HF cap {hf} VIN pad to VIN pin {vpin.GetNumber()}", gap(cv, vpin), lim.get("cin_gap_mm"))
            row(f"HF cap {hf} GND pad to PGND pin {gpin.GetNumber()}", gap(cg, gpin), lim.get("cin_gap_mm"))
            row(f"HF cap {hf} loop plan area (pad centres)", area(poly), lim.get("loop_area_mm2"), "mm2",
                "the copper loop is larger")
            others = [fp.GetReference() for fp in board.GetFootprints()
                      if fp.GetReference() not in loops and fp.GetReference() != s["ic"]
                      and fp.GetLayer() == ic.GetLayer() and inside(centre(fp), poly)]
            row(f"other parts inside {hf}'s loop", len(others), 0, "parts", ", ".join(others))
            for r, (c2, cv2, cg2, vp2, gp2, _) in loops.items():
                if r != hf:
                    row(f"other input cap {r}: VIN / GND pad gaps", max(gap(cv2, vp2), gap(cg2, gp2)), None, "mm",
                        f"{gap(cv2, vp2):.2f} / {gap(cg2, gp2):.2f}" + ("" if c2.GetLayer() == ic.GetLayer() else ", other side"))

        for L in inductors:
            lp = next(p for p in L.Pads() if p.GetNetname() in nets["sw"])
            spin = min(pins["sw"], key=lambda p: gap(lp, p))
            row(f"{L.GetReference()} SW pad to SW pin {spin.GetNumber()}", gap(lp, spin), lim.get("l_gap_mm"))
            if L.GetLayer() != ic.GetLayer():
                row(f"{L.GetReference()} on the IC's side", None, None, "", "NO: the SW node needs vias")
                rows[-1]["grade"] = "FAIL"
        for f in fbparts:
            fpad = next(p for p in f.Pads() if p.GetNetname() in nets["fb"])
            fpin = min(pins["fb"], key=lambda p: gap(fpad, p)) if pins["fb"] else None
            if fpin is not None:
                row(f"{f.GetReference()} to FB pin {fpin.GetNumber()}", gap(fpad, fpin), lim.get("fb_gap_mm"))
            sw_items = list(pins["sw"]) + inductors
            d = min((gap(f, x) for x in sw_items), default=None)
            g = grade(d, lim.get("fb_from_sw_mm"), smaller_is_better=False)
            rows.append({"check": f"{f.GetReference()} distance from the switch node", "value": None if d is None else round(d, 2),
                         "limit": lim.get("fb_from_sw_mm"), "unit": "mm (at least)", "grade": g, "note": ""})

        fails += sum(r["grade"] == "FAIL" for r in rows)
        out.append({"name": s.get("name", s["ic"]), "ic": s["ic"], "source": s.get("source"), "rows": rows})
        print(f"\n{s.get('name', s['ic'])}   [{s.get('source', 'NO SOURCE: limits are not graded')}]")
        for r in rows:
            v = "" if r["value"] is None else f"{r['value']} {r['unit']}"
            l = "" if r["limit"] is None else f"limit {r['limit']}"
            print(f"  {r['grade']:4}  {r['check']:48} {v:>14}  {l:12} {r['note']}")
    if a.json:
        json.dump(out, open(a.json, "w"), indent=2)
    print(f"\n{fails} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
