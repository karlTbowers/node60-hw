#!/usr/bin/env python3
"""Fill in the reasons in the three output-channel pose tables (run from the run folder)."""
import json

WHY = {
    "C01": ("core", "CVBB1, VBB to GND. TI SLVSHR0 §9.4.1: as close as possible to the VBB and GND pins. On F.Cu (decaps go on top), directly over the exposed VBB pad"),
    "C02": ("core", "VBB bulk cap, beside the VBB pad, on the channel's VBAT_PROT pour"),
    "C03": ("core", "VDD decap (SW_VDD). On F.Cu (decaps go on top), over pin 3"),
    "C04": ("core", "CSNS, SNS to GND. TI SLVSHR0 §9.4.1: close to the SNS pin (2.36 mm pad gap)"),
    "C05": ("core", "First output's cap to GND, at the first output's pins (6-8)"),
    "C06": ("core", "Second output's cap to GND, at the second output's pins (9-11)"),
    "C07": ("flex", "NTC filter cap, beside the thermistor; position not critical"),
    "R01": ("core", "SW_VDD feed from 3V3_MAIN, on the VDD side of the chip"),
    "R02": ("core", "DI pull-down, by pin 4"),
    "R03": ("core", "LHI pull-down, by pin 5"),
    "R04": ("core", "FLT pull-up to SW_VDD, by pin 12"),
    "R05": ("core", "RSNS, SNS to GND. TI SLVSHR0 §9.4.1: close to the SNS pin (0.55 mm pad gap)"),
    "R06": ("core", "SNS series resistor to the MCU's ADC, from the SNS node to the channel's SNS test point"),
    "R07": ("flex", "NTC divider, beside the thermistor; position not critical"),
    "RT01": ("core", "Thermistor beside the switch, to read its temperature"),
    "TP01": ("flex", "SNS test point (MCU side)"),
    "TP02": ("flex", "FLT test point"),
    "TP03": ("flex", "SPI MISO test point"),
    "TP04": ("flex", "First output's test point"),
    "TP05": ("flex", "Second output's test point"),
    "TP06": ("flex", "GND probe loop for the channel, anywhere within 12 mm of pin 1"),
}
ANCHOR = {
    "6": "Turned 90° (was 180°) and moved 4.3 mm, so the cell is U701's and FLT pin 12 is reachable",
    "7": "The reviewed cell; U601 and U801 are copies of it",
    "8": "Moved to (224, 113): FLT pin 12 was caged at the annealer's pose and at (220, 112); here it routes",
}


def key(ref):
    for p in ("RT", "TP", "C", "R"):
        if ref.startswith(p):
            return p + ref[-2:] if p != "RT" else "RT01"


for name, n in (("out_6x", "6"), ("out_34", "7"), ("out_8x", "8")):
    path = f"blocks/{name}.poses.json"
    d = json.load(open(path))
    for ref, v in d["parts"].items():
        role, why = WHY[key(ref)]
        v["role"], v["why"] = role, why
        v["flex_mm"] = 0 if role == "core" else (12 if key(ref) == "TP06" else 4)
    d["anchor_why"] = ANCHOR[n]
    if n == "8":
        d["parts"]["TP806"]["why"] += "; at (231, 107.75) because the copied pose overlapped J908 (pose_search.py)"
    json.dump(d, open(path, "w"), indent=2)
    print(name, d["anchor_pose"], sum(v["role"] == "flex" for v in d["parts"].values()), "flex of", len(d["parts"]))
