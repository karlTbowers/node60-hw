#!/usr/bin/env python3
"""n2_retry.py BOARD OUT.kicad_pcb LOG.json -- second pass of N2. n2_enlarge.py steps down every via named in an
error, so of two neighbours that only clash with each other both shrink. Here each via below 0.45/0.25 mm is
tried one step up again while its neighbours within 2 mm keep their size; DRC judges; a via that fails alone
is final. Reads and rewrites LOG.json (n2_enlarge.py's). KiCad's Python."""
import json, math, subprocess, sys, os, pcbnew
src, out, log = sys.argv[1:4]; M, F = pcbnew.ToMM, pcbnew.FromMM
HERE = os.path.dirname(os.path.abspath(__file__)); STEPS = [(0.45, 0.25), (0.40, 0.20), (0.35, 0.20)]
L = json.load(open(log)); cand = {(v["x"], v["y"]): v for v in L}
for v in L: v.setdefault("final", v["step"] == 0)
def build(steps):
    b = pcbnew.LoadBoard(src)
    for t in b.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T: continue
        k = (round(M(t.GetPosition().x), 4), round(M(t.GetPosition().y), 4))
        if k in steps:
            d, dr = STEPS[steps[k]]
            for l in b.GetEnabledLayers().Seq():
                if pcbnew.IsCopperLayer(l): t.SetWidth(l, F(d))
            t.SetDrill(F(dr))
    b.Save(out); drc = out.replace(".kicad_pcb", ".drc.json")
    subprocess.run([os.path.join(HERE, "drc.sh"), out, drc], capture_output=True)
    d = json.load(open(drc)); return [v for v in d["violations"] + d["unconnected_items"] if v["severity"] == "error"]
def named(errs, pool):
    """Candidates an error names by position; if it names none, those of `pool` within 2 mm of one of its items."""
    bad = set()
    for e in errs:
        hit = {k for i in e["items"] for k in [(round(i["pos"]["x"], 4), round(i["pos"]["y"], 4))] if k in cand and cand[k]["step"] < cand[k]["base"]}
        if not hit: hit = {k for k in pool if any(math.dist(k, (i["pos"]["x"], i["pos"]["y"])) < 2.0 for i in e["items"])}
        if not hit: sys.exit(f"error far from every tried via: {e}")
        bad |= hit
    return bad
for v in L: v["base"] = v["step"]
rnd = 0
while True:
    pick = []
    for k, v in sorted(cand.items()):
        if not v["final"] and all(math.dist(k, p) > 2.0 for p in pick): pick.append(k)
    if not pick: break
    for k in pick: cand[k]["step"] -= 1
    raised = {k for k, v in cand.items() if v["step"] < v["base"]}; n = 0
    while True:                                   # KiCad reports one violation per track: repeat until a clean run
        errs = build({k: v["step"] for k, v in cand.items()})
        if not errs: break
        for k in named(errs, raised):
            cand[k]["step"] += 1; cand[k]["final"] = True; n += 1
        raised = {k for k, v in cand.items() if v["step"] < v["base"]}
    for k in pick: cand[k]["final"] = cand[k]["final"] or cand[k]["step"] == 0
    rnd += 1; print("round", rnd, "tried", len(pick), "stepped back", n, flush=True)
errs = build({k: v["step"] for k, v in cand.items()}); print("final errors", len(errs))
for v in L: v.pop("base")
for v in L: v["size"] = STEPS[v["step"]]; v.pop("final")
json.dump(L, open(log, "w"), indent=1)
import collections; print(collections.Counter(tuple(v["size"]) for v in L))
