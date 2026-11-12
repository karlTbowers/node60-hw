#!/usr/bin/env python3
"""What each fast route laid, per run and per variant (mean of its runs). KiCad's Python.

    $KPY route_metrics.py judge/base judge/attempts ... [--json out.json]

For every run folder (NAME.rK) it reads rules.json (KiCad's grade against the board's own rules) and
compares the routed board s6 with the router's input s0: vias and track added, by layer and for the
watched nets. Signal nets only in the totals: KRT routes supply nets pad to pad across the planes
(it does not count a pour as joining), so their fast-route copper says nothing about the real board.
"""
import sys, json, glob, os, math, collections, re
import pcbnew
M = pcbnew.ToMM
SUPPLY = re.compile(r"(^GND$|3V3_MAIN$|1V5_CORE|VBAT|VDDAU|/OUT\d|V11|V25|_REG$|_SW$|_VCC$)")
WATCH = ["NTC_SW1", "NTC_SW2", "NTC_SW3", "I2C0_TELEMETRY_SCL", "I2C0_TELEMETRY_SDA", "T1S_IRQ_L", "TMP175_ALERT_L",
         "T1S_MODE0", "T1S_MODE1", "T1S_PHYAD4", "NTC_RSENSE", "LM_FLT_L", "BATT_MON"]


def copper(path):
    b = pcbnew.LoadBoard(path)
    vias = collections.Counter(); length = collections.defaultdict(lambda: collections.Counter())
    for t in b.GetTracks():
        n = t.GetNetname().split("/")[-1]
        if t.Type() == pcbnew.PCB_VIA_T:
            vias[n] += 1
        else:
            length[n][t.GetLayerName().split(".")[0]] += M(t.GetLength())
    return vias, length


def run(d):
    r = {"dir": d}
    try:
        g = json.load(open(os.path.join(d, "rules.json")))
        r.update(blocking=g["blocking"], unconnected=g["unconnected_items"], open_nets=sorted(n.split("/")[-1] for n in g["open_nets"]),
                 rule_hits=sum(g.get("custom_rule_hits", {}).values()), other_errors=sum(g.get("other_errors", {}).values()))
    except Exception as e:
        r["error"] = f"no grade: {e}"; return r
    v0, l0 = copper(os.path.join(d, "s0.kicad_pcb")); v1, l1 = copper(os.path.join(d, "s6.kicad_pcb"))
    sig = lambda n: not SUPPLY.search(n)
    r["sig_vias"] = sum(c for n, c in v1.items() if sig(n)) - sum(c for n, c in v0.items() if sig(n))
    lay = collections.Counter()
    for n in l1:
        if sig(n):
            for L, mm in l1[n].items():
                lay[L] += mm - l0.get(n, {}).get(L, 0)
    r["sig_mm"] = {L: round(v, 1) for L, v in lay.items()}
    r["sig_mm_total"] = round(sum(lay.values()), 1)
    r["sig_mm_In2"] = round(lay.get("In2", 0), 1)
    r["watch"] = {n: {"vias": v1.get(n, 0) - v0.get(n, 0), "mm": round(sum(l1.get(n, {}).values()) - sum(l0.get(n, {}).values()), 1)} for n in WATCH}
    r["open_signal"] = [n for n in r["open_nets"] if sig(n)]
    return r


def main():
    args = sys.argv[1:]; out = None
    if "--json" in args:
        i = args.index("--json"); out = args[i + 1]; del args[i:i + 2]
    runs = {}
    for batch in args:
        for d in sorted(glob.glob(os.path.join(batch, "*.r[0-9]*"))):
            name = os.path.basename(d).rsplit(".r", 1)[0]
            runs.setdefault(name, []).append(run(d))
    if out:
        json.dump(runs, open(out, "w"), indent=1)
    print(f"{'variant':8} {'run':>3} {'blocking':>8} {'unconn':>6} {'sig vias':>8} {'sig mm':>8} {'In2 mm':>7}  open signal nets")
    for name, rs in runs.items():
        for k, r in enumerate(rs, 1):
            if "error" in r:
                print(f"{name:8} {k:>3}  {r['error']}"); continue
            print(f"{name:8} {k:>3} {r['blocking']:>8} {r['unconnected']:>6} {r['sig_vias']:>8} {r['sig_mm_total']:>8} {r['sig_mm_In2']:>7}  {', '.join(r['open_signal'])}")
    print("\nwatched nets, vias / mm per run:")
    print(f"{'variant':8} " + " ".join(f"{n[-11:]:>13}" for n in WATCH))
    for name, rs in runs.items():
        for r in rs:
            if "error" in r: continue
            print(f"{name:8} " + " ".join(f"{r['watch'][n]['vias']:>3}/{r['watch'][n]['mm']:>7.1f}  " for n in WATCH))


if __name__ == "__main__":
    main()
