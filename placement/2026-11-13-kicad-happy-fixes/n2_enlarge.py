#!/usr/bin/env python3
"""n2_enlarge.py BOARD OUT.kicad_pcb LOG.json -- N2: enlarge the 0.35/0.20 mm vias outside U401's body.
Each goes to 0.45/0.25 mm; KiCad's DRC (the board's own rules, zones refilled) judges, and a via named in any
error steps down to 0.40/0.20 mm (0.10 mm ring as well), then back to 0.35/0.20. Repeats until no error names
a candidate. BOARD's folder must hold the project (work/). KiCad's Python."""
import json, subprocess, sys, os, pcbnew
src, out, log = sys.argv[1:4]; M, F = pcbnew.ToMM, pcbnew.FromMM
HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [(0.45, 0.25), (0.40, 0.20), (0.35, 0.20)]
b = pcbnew.LoadBoard(src)
u = b.FindFootprintByReference("U401"); bb = u.GetBoundingBox(False)
box = [M(bb.GetLeft()), M(bb.GetTop()), M(bb.GetRight()), M(bb.GetBottom())]
cand = {}
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T and abs(M(t.GetWidth(pcbnew.F_Cu)) - 0.35) < 1e-6:
        x, y = M(t.GetPosition().x), M(t.GetPosition().y)
        if not (box[0] <= x <= box[2] and box[1] <= y <= box[3]):
            cand[(round(x, 4), round(y, 4))] = {"net": t.GetNetname(), "step": 0, "locked": t.IsLocked()}
print("U401 body", [round(v, 2) for v in box], "candidates", len(cand))
rnd = 0
while True:
    b = pcbnew.LoadBoard(src)
    for t in b.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T: continue
        k = (round(M(t.GetPosition().x), 4), round(M(t.GetPosition().y), 4))
        if k in cand:
            d, dr = STEPS[cand[k]["step"]]
            for l in b.GetEnabledLayers().Seq():
                if pcbnew.IsCopperLayer(l): t.SetWidth(l, F(d))
            t.SetDrill(F(dr))
    b.Save(out)
    drc = out.replace(".kicad_pcb", ".drc.json")
    subprocess.run([os.path.join(HERE, "drc.sh"), out, drc], capture_output=True)
    d = json.load(open(drc)); bad = set(); other = 0
    for v in d["violations"] + d["unconnected_items"]:
        if v["severity"] != "error": continue
        hit = False
        for it in v["items"]:
            k = (round(it["pos"]["x"], 4), round(it["pos"]["y"], 4))
            if k in cand and it["description"].startswith("Via") and cand[k]["step"] < 2: bad.add(k); hit = True
        if not hit:
            other += 1; near = sorted(cand, key=lambda k: min((k[0] - it["pos"]["x"]) ** 2 + (k[1] - it["pos"]["y"]) ** 2 for it in v["items"]))
            for k in near[:2]:                       # an error naming no candidate (a zone cut off, a track): the enlarged vias nearest it step down
                if cand[k]["step"] < 2: bad.add(k)
            print("  other:", v["type"], [(i["description"][:50], i["pos"]) for i in v["items"]])
    rnd += 1; print("round", rnd, "errors naming candidates:", len(bad), "others:", other, flush=True)
    if not bad: break
    for k in bad: cand[k]["step"] += 1
json.dump([{"x": k[0], "y": k[1], **v, "size": STEPS[v["step"]]} for k, v in sorted(cand.items())], open(log, "w"), indent=1)
import collections; print(collections.Counter(STEPS[v["step"]] for v in cand.values()))
