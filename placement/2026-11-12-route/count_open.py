#!/usr/bin/env python3
"""count_open.py DRC.json -- errors, and unconnected items split: signal (no test point), supply (no test point), at a test point."""
import json, re, sys
d = json.load(open(sys.argv[1])); S = ("GND", "VBAT", "3V3_MAIN", "1V5_CORE", "VDDAU_AON]", "/OUT")
e = sum(1 for v in d["violations"] if v["severity"] == "error"); sig = sup = tp = 0
for u in d.get("unconnected_items", []):
    s = " | ".join(i["description"] for i in u["items"])
    if re.search(r"of TP\d+", s): tp += 1
    elif any(k in s for k in S): sup += 1
    else: sig += 1
print(f"errors {e}  signal opens {sig}  supply opens {sup}  at test points {tp}")
