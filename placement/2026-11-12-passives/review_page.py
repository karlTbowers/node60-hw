#!/usr/bin/env python3
"""Build the review page of the passive-placement study (decisions/D32-passive-moves.json and .html)
from the attempt specs, the copper table (copper_table.py) and the fast-route table (route_metrics.py).

    python3 review_page.py            # then decision_page.py builds the HTML
Verdicts and prose live in VERDICT below; every number is read from data/*.json."""
import json, os, statistics as st
H = os.path.dirname(os.path.abspath(__file__))
cu = json.load(open(f"{H}/data/copper_table.json"))
rt = json.load(open(f"{H}/data/routes.json"))
base_c, base_r = cu["00-main"], [r for k in ("base", "base3") for r in rt.get(k, []) if "error" not in r]
VAR = {"01-tmp175-home": "a01", "02-east-feed": "a02", "03a-i2c-pullups-row": "a03", "03b-i2c-pullups-stair": "a03b",
       "04-irq-pullup": "a04", "05-ntc-to-mcu": "a05", "06-phy-strap": "a06", "07a-combined": "a07", "07b-combined": "a07b",
       "08-no-3v3-into-cells": "a08", "09-everything": "a09", "10-tvs-pour": "a10"}
V = json.load(open(f"{H}/verdicts.json"))


def runs(v):
    return [r for r in rt.get(v, []) if "error" not in r]


def spread(rs, k):
    return ", ".join(str(r[k]) for r in rs) if rs else "not run"


def watch(rs, nets, what):
    if not rs: return "not run"
    return ", ".join(str(round(sum(r["watch"][n][what] for n in nets), 1 if what == "mm" else 0)).rstrip("0").rstrip(".") if what == "mm"
                     else str(sum(r["watch"][n][what] for n in nets)) for r in rs)


def option(key, board, imgs):
    v = V[board]; a = json.load(open(f"{H}/attempts/{v['spec']}.json")); c = cu[board]; rs = runs(VAR[board])
    m = [{"label": "KiCad DRC errors, board's own rules", "value": "0", "limit": "0", "status": "pass"},
         {"label": "3V3 track in the power band", "value": f"{c['3v3_band_mm']:.0f} mm", "limit": f"main {base_c['3v3_band_mm']:.0f} mm",
          "status": "pass" if c["3v3_band_mm"] < base_c["3v3_band_mm"] - 1 else "info"},
         {"label": "3V3 vias on the board", "value": str(c["3v3_vias"]), "limit": f"main {base_c['3v3_vias']}",
          "status": "pass" if c["3v3_vias"] < base_c["3v3_vias"] else ("warn" if c["3v3_vias"] > base_c["3v3_vias"] else "info")},
         {"label": "Fast route, blocking items per run", "value": spread(rs, "blocking"), "limit": "main " + spread(base_r, "blocking"), "status": v.get("route_status", "info")},
         {"label": "Fast route, unconnected items per run", "value": spread(rs, "unconnected"), "limit": "main " + spread(base_r, "unconnected"), "status": "info"},
         {"label": "Fast route, signal vias laid per run", "value": spread(rs, "sig_vias"), "limit": "main " + spread(base_r, "sig_vias"), "status": "info"},
         {"label": "Fast route, signal track on In2 per run (mm)", "value": spread(rs, "sig_mm_In2"), "limit": "main " + spread(base_r, "sig_mm_In2"), "status": "info"}]
    if v.get("nets"):
        m.append({"label": "This move's nets: vias per run", "value": watch(rs, v["nets"], "vias"), "limit": "main " + watch(base_r, v["nets"], "vias"), "status": v.get("net_status", "info")})
        m.append({"label": "This move's nets: track per run (mm)", "value": watch(rs, v["nets"], "mm"), "limit": "main " + watch(base_r, v["nets"], "mm"), "status": "info"})
    m.append({"label": "Approved block tables touched", "value": v.get("blocks", "none"), "limit": "none", "status": "warn" if v.get("blocks") else "pass"})
    return {"key": key, "name": v["name"], "summary": a["why"] + ("\n\n" + v["found"] if v.get("found") else ""),
            "images": [{"path": f"../img/{i[0]}", "caption": i[1]} for i in imgs], "measures": m,
            "gains": v["gains"], "costs": v["costs"]}


page = json.load(open(f"{H}/page_text.json"))
page["options"] = [option(k, b, i) for k, b, i in page.pop("option_list")]
json.dump(page, open(f"{H}/decisions/D32-passive-moves.json", "w"), indent=1)
print("written decisions/D32-passive-moves.json")
