#!/usr/bin/env python3
"""sync_tables.py BOARD NOTE TABLE.poses.json [...] -- after a landing that moved parts on purpose: for every part
of each block table that is off its table pose on BOARD, write the board's pose into the table and add NOTE to
its reason (test points put back after routing; R501 and C509 of the T1S block, D34). Uses block_poses.py
extract for the poses. Run with KiCad's Python from the repo root."""
import json, subprocess, sys, tempfile, os
board, note, tables = sys.argv[1], sys.argv[2], sys.argv[3:]
BP = ".claude/skills/pcb-placement/scripts/block_poses.py"
for tp in tables:
    s = open(tp).read(); d = json.loads(s); ind = 1 if json.dumps(d, indent=1, ensure_ascii=False) == s.rstrip("\n") else 2
    refs = [d["anchor"]] + list(d["parts"])
    tmp = tempfile.mktemp(suffix=".json")
    subprocess.run([sys.executable, BP, "extract", board, "--anchor", d["anchor"], "--refs", ",".join(refs), "-o", tmp], capture_output=True)
    x = json.load(open(tmp)); os.remove(tmp); n = []
    for ref, p in d["parts"].items():
        q = x["parts"].get(ref)
        if q is None: continue
        if abs(q["dx"] - p["dx"]) > 0.011 or abs(q["dy"] - p["dy"]) > 0.011 or abs((q["rot"] - p["rot"] + 180) % 360 - 180) > 0.1 or q["side"] != p["side"]:
            p.update(dx=q["dx"], dy=q["dy"], rot=q["rot"], side=q["side"]); p["why"] = (p.get("why", "") + " " + note).strip(); n.append(ref)
    if n:
        d["approved"] = (d.get("approved") or "") + f"; {', '.join(n)} re-posed 2026-11-12 (D34, routing run)"
        open(tp, "w").write(json.dumps(d, indent=ind, ensure_ascii=False) + ("\n" if s.endswith("\n") else ""))
    print(os.path.basename(tp), "re-posed:", ", ".join(n) or "none")
