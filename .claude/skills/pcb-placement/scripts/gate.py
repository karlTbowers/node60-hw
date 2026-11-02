#!/usr/bin/env python3
"""The placement gate: one table, every row measured (pcb-placement skill). Run with KiCad's Python.

    $KPY gate.py BOARD.kicad_pcb --plan RUN/plan.json [--fast-route RUN/sS_fast.kicad_pcb]
        [--fast-score RUN/sS_fast.score.json] [-o RUN/gate]

Reads the machine half of the plan (`references/plan.md` gives the format), runs this skill's
checks and KRT's (`check_assembly`, `check_floorplan`) where the plan names them, measures its
own rows (fiducials, net classes, via sites beside high-current pads, block pose tables) and
writes `gate.md` and `gate.json`. A row is PASS, FAIL, WARN, NOT RUN (the input it needs is
missing; a NOT RUN row blocks like a FAIL), or ACCEPTED (a FAIL the user accepted by decision,
listed in the plan's `accepted`). The board passes when no row is FAIL or NOT RUN.
Exit 0 on pass, 1 otherwise.
"""
import argparse
import datetime
import fnmatch
import hashlib
import json
import math
import os
import re
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from escape_budget import blocking_areas  # noqa: E402

KPY = sys.executable


def mm(v):
    return pcbnew.ToMM(v)


def run(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines()
                    if "Debug:" not in l and "assert" not in l)
    return r.returncode, out


def last_lines(text, n=3):
    lines = [l for l in text.strip().splitlines() if l.strip()]
    return " / ".join(lines[-n:])


def fiducial_row(board, plan):
    spec = plan.get("fiducials")
    if not spec:
        return ("Fiducials", "FID parts per assembled side; 2 or 4, not symmetric under a half turn", "NOT RUN",
                "the plan names no assembled sides (`fiducials.sides`)")
    ebb = board.GetBoardEdgesBoundingBox()
    cx, cy = mm(ebb.GetCenter().x), mm(ebb.GetCenter().y)
    notes, ok = [], True
    for side in spec["sides"]:
        pts = [(mm(f.GetPosition().x), mm(f.GetPosition().y)) for f in board.GetFootprints()
               if (f.GetReference().startswith("FID") or "iducial" in f.GetFPIDAsString())
               and (f.IsFlipped() == (side == "B"))]
        good = len(pts) in spec.get("count", [2, 4])
        sym = pts and all(any(math.hypot(2 * cx - x - u, 2 * cy - y - v) < 1.0 for u, v in pts) for x, y in pts)
        if not good or sym:
            ok = False
        notes.append(f"{side}: {len(pts)}" + (" (symmetric: a half-turned board reads the same)" if sym else ""))
    return ("Fiducials", "FID parts per assembled side; 2 or 4, not symmetric under a half turn",
            "PASS" if ok else "FAIL", "; ".join(notes))


def netclass_row(board, plan, project):
    rows = plan.get("net_classes")
    if not rows:
        return ("Net classes", "each planned class assigned to its nets, track width at least its minimum", "NOT RUN",
                "the plan lists no net classes (`net_classes`)")
    pro = json.load(open(project))
    ns = pro.get("net_settings", {})
    classes = {c["name"]: c for c in ns.get("classes", [])}
    assign = ns.get("netclass_assignments") or {}
    patterns = ns.get("netclass_patterns") or []
    nets = [n for n in board.GetNetsByName().keys() if str(n)]

    def class_of(net):
        if net in assign:
            v = assign[net]
            return v[0] if isinstance(v, list) else v
        for p in patterns:
            if fnmatch.fnmatchcase(net, p["pattern"]) or re.fullmatch(p["pattern"].replace("*", ".*"), net):
                return p["netclass"]
        return "Default"

    bad = []
    for r in rows:
        hits = [str(n) for n in nets if fnmatch.fnmatchcase(str(n), r["nets"]) or fnmatch.fnmatchcase(str(n).lstrip("/"), r["nets"])]
        if not hits:
            bad.append(f"no net matches {r['nets']}")
        for n in hits:
            c = class_of(n)
            if c != r["class"]:
                bad.append(f"{n} is {c}, planned {r['class']}")
            elif r.get("min_track_mm") and classes.get(c, {}).get("track_width", 0) + 1e-9 < r["min_track_mm"]:
                bad.append(f"{c} track {classes[c].get('track_width')} < {r['min_track_mm']} mm")
    return ("Net classes", "each planned class assigned to its nets, track width at least its minimum",
            "FAIL" if bad else "PASS", "; ".join(bad[:8]) + (f" (+{len(bad) - 8} more)" if len(bad) > 8 else "")
            if bad else f"{len(rows)} planned class row(s) on the board")


def via_sites_row(board, plan, rules_text):
    hc = plan.get("high_current")
    if not hc:
        return ("Vias at high-current layer changes", "free via sites within reach of each pad vs ceil(I / I per via)",
                "NOT RUN", "the plan lists no high-current pads (`high_current`)")
    via, space = plan["via_mm"], plan["space_mm"]
    pitch = via + space
    areas = blocking_areas(board, rules_text, blocks=("via",))
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    short = []
    for h in hc:
        ref, num = h["pad"].split(".")
        fp = board.FindFootprintByReference(ref)
        pad = next((p for p in fp.Pads() if p.GetNumber() == num), None) if fp else None
        if pad is None:
            short.append(f"{h['pad']} not found")
            continue
        need = math.ceil(h["amps"] / h["via_amps"])
        net = pad.GetNetname()
        px, py = mm(pad.GetPosition().x), mm(pad.GetPosition().y)
        reach = h.get("radius_mm", 3.0) + max(mm(pad.GetSizeX()), mm(pad.GetSizeY())) / 2
        free = 0
        steps = int(reach / pitch)
        for i in range(-steps, steps + 1):
            for j in range(-steps, steps + 1):
                x, y = px + i * pitch, py + j * pitch
                if math.hypot(x - px, y - py) > reach:
                    continue
                pt = pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
                if any(z.Outline().Contains(pt) and net.lstrip("/") not in ex for z, _, ex in areas.values()):
                    continue
                clear = True
                for q in pads:
                    bb = q.GetBoundingBox()
                    m = via / 2 + (space if q.GetNetname() != net else 0)
                    if mm(bb.GetLeft()) - m < x < mm(bb.GetRight()) + m and mm(bb.GetTop()) - m < y < mm(bb.GetBottom()) + m:
                        clear = False
                        break
                free += clear
        if free < need:
            short.append(f"{h['pad']} ({net}, {h['amps']} A): {free} free site(s), needs {need}")
    return ("Vias at high-current layer changes", "free via sites within reach of each pad vs ceil(I / I per via)",
            "FAIL" if short else "PASS", "; ".join(short) if short else f"{len(hc)} pad(s) have room")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--fast-route", help="the fast-routed board of this placement")
    ap.add_argument("--fast-score", help="KRT quick_score JSON of that fast route")
    ap.add_argument("-o", "--out", help="output stem (default: <plan dir>/gate)")
    a = ap.parse_args()

    base = os.path.dirname(os.path.abspath(a.plan))
    plan = json.load(open(a.plan))
    P = lambda p: p if p is None or os.path.isabs(os.path.expanduser(p)) else os.path.join(base, p)  # noqa: E731
    project, rules = P(plan.get("project")), P(plan.get("rules"))
    rules_text = open(rules).read() if rules and os.path.exists(rules) else ""
    board = pcbnew.LoadBoard(a.board)
    rows = []
    krt = os.path.expanduser(plan.get("krt", "~/Dev/KiCadRoutingTools"))
    intent, baseline = P(plan.get("intent")), P(plan.get("baseline"))

    # KRT legality
    if os.path.isdir(krt) and baseline:
        rc, out = run([KPY, "-X", "utf8", "py_tools/check_assembly.py", os.path.abspath(a.board), "--baseline", baseline], cwd=krt)
        ok = "VERDICT: buildable" in out
        rows.append(("Buildable", "KRT check_assembly --baseline (parts on the board, courtyards, bodies, pads)",
                     "PASS" if ok else "FAIL", last_lines(out, 2)))
    else:
        rows.append(("Buildable", "KRT check_assembly --baseline", "NOT RUN", "plan needs `krt` and `baseline`"))
    if os.path.isdir(krt) and intent:
        rc, out = run([KPY, "-X", "utf8", "py_tools/check_floorplan.py", os.path.abspath(a.board), "--intent", intent], cwd=krt)
        n = out.count("[ERROR]")
        rows.append(("Floorplan intent", "KRT check_floorplan --intent (edges, groups, templates, keep-outs, decaps)",
                     "PASS" if n == 0 else "FAIL", f"{n} error(s)" + (f", {out.count('[WARN')} warning(s)" if "[WARN" in out else "")))
    else:
        rows.append(("Floorplan intent", "KRT check_floorplan --intent", "NOT RUN", "plan needs `krt` and `intent`"))

    # parity, against the schematic beside the board's project
    sch = P(plan.get("schematic"))
    if sch and os.path.exists(sch):
        import tempfile
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            stem = os.path.splitext(os.path.basename(sch))[0]
            shutil.copy(a.board, os.path.join(tmp, stem + ".kicad_pcb"))
            for ext in (".kicad_pro", ".kicad_dru"):
                src = os.path.splitext(project or sch)[0] + ext
                if os.path.exists(src):
                    shutil.copy(src, os.path.join(tmp, stem + ext))
            for f in os.listdir(os.path.dirname(sch)):
                if f.endswith(".kicad_sch"):
                    shutil.copy(os.path.join(os.path.dirname(sch), f), tmp)
            sheets = os.path.join(os.path.dirname(sch), "sheets")
            if os.path.isdir(sheets):
                shutil.copytree(sheets, os.path.join(tmp, "sheets"))
            for f in ("sym-lib-table", "fp-lib-table", "lib"):
                if os.path.exists(os.path.join(os.path.dirname(sch), f)):
                    os.symlink(os.path.join(os.path.dirname(sch), f), os.path.join(tmp, f))
            outj = os.path.join(tmp, "p.json")
            cli = plan.get("kicad_cli", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
            run([cli, "pcb", "drc", "--schematic-parity", "--format", "json", "-o", outj, os.path.join(tmp, stem + ".kicad_pcb")])
            par = json.load(open(outj)).get("schematic_parity", []) if os.path.exists(outj) else None
        if par is None:
            rows.append(("Schematic parity", "kicad-cli pcb drc --schematic-parity", "NOT RUN", "DRC did not run"))
        else:
            kinds = {}
            for x in par:
                kinds[x["type"]] = kinds.get(x["type"], 0) + 1
            hard = {k: v for k, v in kinds.items() if k != "footprint_symbol_field_mismatch"}
            st = "FAIL" if hard else ("WARN" if kinds else "PASS")
            rows.append(("Schematic parity", "kicad-cli pcb drc --schematic-parity (field mismatches warn)", st,
                         ", ".join(f"{k} {v}" for k, v in kinds.items()) or "0 items"))
    else:
        rows.append(("Schematic parity", "kicad-cli pcb drc --schematic-parity", "NOT RUN", "plan needs `schematic`"))

    # heights
    for h in plan.get("heights", []):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json") as tj:
            rc, out = run(["python3", os.path.join(HERE, "part_heights.py"), a.board, "--side", h["side"],
                           "--json", tj.name])
            hs = json.load(open(tj.name)) if os.path.getsize(tj.name) else []
        given = {d["ref"]: d for d in plan.get("declared_heights", [])}
        over, unknown = [], []
        for r in hs:
            hgt = r["height_mm"] if r["height_mm"] is not None else given.get(r["ref"], {}).get("height_mm")
            if hgt is None:
                unknown.append(r["ref"])
            elif hgt > h["limit_mm"]:
                over.append(f"{r['ref']} {hgt:.2f} mm")
        st = "FAIL" if over else ("WARN" if unknown else "PASS")
        note = (f"over: {', '.join(over)}" if over else "none over") + \
               (f"; no height for {len(unknown)} ({', '.join(unknown[:6])}{'…' if len(unknown) > 6 else ''}): declare them" if unknown else "")
        rows.append((f"Heights, {h['side']} side, {h.get('area', 'whole board')}",
                     f"part_heights.py: model body, limit {h['limit_mm']} mm ({h.get('source', 'no source')})", st, note))
    if not plan.get("heights"):
        rows.append(("Heights", "part_heights.py against the enclosure's limits", "NOT RUN", "the plan lists no height limits"))

    # BGA escape
    for ref in plan.get("bgas", []):
        rc, out = run([KPY, os.path.join(HERE, "escape_budget.py"), a.board, "--ref", ref, "--track", str(plan["track_mm"]),
                       "--space", str(plan["space_mm"]), "--via", str(plan["via_mm"]), "--plane-nets", ",".join(plan.get("plane_nets", [])),
                       "--signal-layers", ",".join(plan["signal_layers"])] + (["--rules", rules] if rules else []))
        rows.append((f"BGA escape {ref}", "escape_budget.py: layers needed vs planned, nothing over the ball field",
                     "PASS" if rc == 0 else "FAIL", last_lines(out, 2)))

    # capacity
    if plan.get("signal_layers"):
        rc, out = run([KPY, os.path.join(HERE, "layer_capacity.py"), a.board, "--signal-layers", ",".join(plan["signal_layers"]),
                       "--plane-nets", ",".join(plan.get("plane_nets", [])), "--track", str(plan["track_mm"]),
                       "--space", str(plan["space_mm"])] + (["--rules", rules] if rules else []))
        warn = re.search(r"(\d+) over 60 %", out)
        st = "FAIL" if rc else ("WARN" if warn and warn.group(1) != "0" else "PASS")
        rows.append(("Layer capacity", "layer_capacity.py: MST demand vs tracks per 10 mm window", st, last_lines(out, 1)))

    # switchers
    if plan.get("switchers"):
        rc, out = run([KPY, os.path.join(HERE, "hot_loop.py"), a.board, P(plan["switchers"])])
        rows.append(("Switcher hot loops", "hot_loop.py against each datasheet's layout limits",
                     "PASS" if rc == 0 else "FAIL", last_lines(out, 1)))
    else:
        rows.append(("Switcher hot loops", "hot_loop.py", "NOT RUN", "the plan names no switcher spec (`switchers`)"))

    # blocks
    if plan.get("blocks"):
        rc, out = run([KPY, os.path.join(HERE, "block_poses.py"), "check", a.board] + [P(b) for b in plan["blocks"]])
        unapproved = out.count("approved NOT YET")
        st = "FAIL" if rc or unapproved else "PASS"
        rows.append(("Critical blocks", "block_poses.py check: core parts exact, flex within allowance, approved",
                     st, "; ".join(l.strip() for l in out.splitlines() if l and not l.startswith("  WARN"))[:400]))
    else:
        rows.append(("Critical blocks", "block_poses.py check", "NOT RUN", "the plan lists no block tables"))

    rows.append(fiducial_row(board, plan))
    rows.append(netclass_row(board, plan, project) if project else
                ("Net classes", "planned classes on the board", "NOT RUN", "plan needs `project`"))
    rows.append(via_sites_row(board, plan, rules_text))

    # DONE: the fast route
    if a.fast_score and os.path.exists(a.fast_score):
        sc = json.load(open(a.fast_score))
        rows.append(("Fast route, KRT score", "quick_score: blocking (open nets, floorplan, assembly)",
                     "PASS" if sc.get("blocking", 1) == 0 else "FAIL",
                     f"blocking {sc.get('blocking')}, joins_needed {sc.get('joins_needed')}"))
    else:
        rows.append(("Fast route, KRT score", "quick_score of the judging route", "NOT RUN", "pass --fast-score"))
    if a.fast_route and project:
        rc, out = run(["python3", os.path.join(HERE, "grade_route.py"), a.fast_route, "--project", project]
                      + (["--rules", rules] if rules else []))
        rows.append(("Fast route, board's own rules", "grade_route.py: KiCad DRC with the board's .kicad_pro and .kicad_dru",
                     "PASS" if rc == 0 else "FAIL", last_lines(out, 4)))
    else:
        rows.append(("Fast route, board's own rules", "grade_route.py", "NOT RUN", "pass --fast-route"))

    accepted = {x["check"]: x for x in plan.get("accepted", [])}
    final = []
    for name, how, st, note in rows:
        if st == "FAIL" and name in accepted:
            st, note = "ACCEPTED", f"{note} (accepted: {accepted[name].get('decision', '')} {accepted[name].get('note', '')})"
        final.append({"check": name, "how": how, "status": st, "result": note})
    passed = not any(r["status"] in ("FAIL", "NOT RUN") for r in final)

    sha = hashlib.sha256(open(a.board, "rb").read()).hexdigest()[:16]
    stem = a.out or os.path.join(base, "gate")
    lines = [f"# Placement gate: {os.path.basename(a.board)}", "",
             f"- Date: {datetime.date.today().isoformat()}; KiCad {pcbnew.Version()}; board sha256 {sha}…",
             f"- Verdict: **{'PASS' if passed else 'NOT PASSED'}**", "",
             "| Check | How it is measured | Status | Result |", "|---|---|---|---|"]
    for r in final:
        lines.append(f"| {r['check']} | {r['how']} | {r['status']} | {r['result'].replace('|', '/')} |")
    open(stem + ".md", "w").write("\n".join(lines) + "\n")
    json.dump({"board": os.path.abspath(a.board), "sha256": sha, "pass": passed, "rows": final},
              open(stem + ".json", "w"), indent=2)
    for r in final:
        print(f"{r['status']:9} {r['check']:38} {r['result'][:110]}")
    print(f"\n{'PASS' if passed else 'NOT PASSED'}; wrote {stem}.md")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
