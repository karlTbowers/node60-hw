#!/usr/bin/env python3
"""Grade a fast-routed board against the board's OWN copper rules (pcb-placement skill).

KRT's judging route ranks seeds by its own score. That score does not run KiCad's
DRC, and not every step of a routing chain reads the board's `.kicad_dru` (on Node60
the fanout and plane steps put 53 vias under the busbars, where only the bar's own
net may have F.Cu copper). So a seed is DONE only when KiCad itself, with the board's
real `.kicad_pro` and `.kicad_dru`, finds no blocking item on its fast route.

    python3 grade_route.py ROUTED.kicad_pcb --project node60.kicad_pro --rules node60.kicad_dru \
        [--json OUT.json] [--no-refill]

The board is copied with the given project and rules into a temporary folder under one
basename (KiCad loads `<name>.kicad_pro` and `<name>.kicad_dru` beside `<name>.kicad_pcb`),
zones are refilled (a fast route leaves planes unfilled) and `kicad-cli pcb drc` runs
there. Blocking: any unconnected item, any hit on a custom rule of the rules file, any
short or clearance/hole error. Warnings (silk, dangling vias) are counted, not blocking.
Exit 0 when nothing blocks, 1 when something does, 2 when DRC could not run.
"""
import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

KICAD_CLI_CANDIDATES = (
    "kicad-cli",
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
    "/usr/bin/kicad-cli",
)

# DRC error types a route can cause and a placement must leave room to avoid.
BLOCKING_TYPES = {
    "shorting_items", "clearance", "hole_clearance", "copper_edge_clearance",
    "tracks_crossing", "items_not_allowed", "track_width", "via_diameter",
    "annular_width", "drill_out_of_range", "hole_to_hole", "diff_pair_gap_out_of_range",
    "diff_pair_uncoupled_length_too_long", "length_out_of_range", "skew_out_of_range",
    "too_many_vias", "connection_width", "zones_intersect",
}


def kicad_cli():
    for c in KICAD_CLI_CANDIDATES:
        p = shutil.which(c) or (c if os.path.exists(c) else None)
        if p:
            return p
    return None


def rule_names(dru_path):
    if not dru_path:
        return []
    text = "\n".join(line for line in open(dru_path, encoding="utf-8").read().splitlines()
                     if not line.lstrip().startswith("#"))
    return re.findall(r'\(rule\s+"([^"]+)"', text) + re.findall(r"\(rule\s+([^\s\"()]+)", text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board")
    ap.add_argument("--project", required=True, help="the board's real .kicad_pro (DRC floors, net classes)")
    ap.add_argument("--rules", help="the board's real .kicad_dru (custom rules); omit only if it has none")
    ap.add_argument("--json", help="write the grade here")
    ap.add_argument("--no-refill", action="store_true", help="grade zones as stored")
    a = ap.parse_args()

    cli = kicad_cli()
    if not cli:
        print("ERROR: kicad-cli not found", file=sys.stderr)
        return 2
    rules = rule_names(a.rules)
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, "graded")
        shutil.copy(a.board, base + ".kicad_pcb")
        shutil.copy(a.project, base + ".kicad_pro")
        if a.rules:
            shutil.copy(a.rules, base + ".kicad_dru")
        out = os.path.join(tmp, "drc.json")
        cmd = [cli, "pcb", "drc", "--severity-all", "--format", "json", "-o", out]
        if not a.no_refill:
            cmd.append("--refill-zones")
        cmd.append(base + ".kicad_pcb")
        r = subprocess.run(cmd, capture_output=True, text=True)
        if not os.path.exists(out):
            print("ERROR: DRC did not run:\n" + r.stdout + r.stderr, file=sys.stderr)
            return 2
        drc = json.load(open(out))

    viol = drc.get("violations", [])
    unconnected = drc.get("unconnected_items", [])
    open_nets = sorted({i.get("description", "").split("[")[-1].split("]")[0]
                        for u in unconnected for i in u.get("items", []) if "[" in i.get("description", "")})

    by_rule = collections.defaultdict(list)
    other_errors = collections.Counter()
    warnings = collections.Counter()
    for v in viol:
        m = re.search(r"\(rule '([^']+)'\)", v.get("description", ""))
        name = m.group(1) if m else None
        if name and name in rules:
            by_rule[name].append(" / ".join(i.get("description", "") for i in v.get("items", [])))
        elif v.get("severity") == "error" and v.get("type") in BLOCKING_TYPES:
            other_errors[v["type"]] += 1
        else:
            warnings[v.get("type")] += 1

    capped = [t for t, n in collections.Counter(v.get("type") for v in viol).items() if n >= 199]
    blocking = len(unconnected) + sum(len(x) for x in by_rule.values()) + sum(other_errors.values())
    grade = {
        "board": os.path.abspath(a.board),
        "kicad": drc.get("kicad_version"),
        "refilled": not a.no_refill,
        "blocking": blocking,
        "unconnected_items": len(unconnected),
        "open_nets": open_nets,
        "custom_rule_hits": {k: {"count": len(v), "examples": v[:5]} for k, v in by_rule.items()},
        "custom_rules_loaded": rules,
        "other_errors": dict(other_errors),
        "warnings": dict(warnings),
        "capped_types": capped,
    }

    print(f"KiCad DRC with the board's own rules ({len(rules)} custom rule(s) loaded)")
    print(f"  unconnected items : {len(unconnected)}" + (f"  nets: {', '.join(open_nets[:12])}" if open_nets else ""))
    for k, v in by_rule.items():
        print(f"  rule '{k}': {len(v)}   e.g. {v[0]}")
    for k, n in other_errors.items():
        print(f"  {k}: {n}")
    print(f"  not blocking (silk, dangling, library, mask): {sum(warnings.values())}")
    if capped:
        print(f"  NOTE: {', '.join(capped)} reached KiCad's 199-entry report cap; the count is a floor")
    print(f"BLOCKING={blocking}")
    if a.json:
        json.dump(grade, open(a.json, "w"), indent=2)
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
