#!/usr/bin/env python3
"""Draw the placement plan's picture (board mm, x east, y south): outline, fixed parts, busbars and lid
bosses, the zones the plan reserves, and the critical-net lanes. Writes decisions/img/plan.svg."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = json.load(open(os.path.join(HERE, "poses_now.json")))
plan = json.load(open(os.path.join(HERE, "plan.json")))
X0, Y0, X1, Y1 = 40.0, 30.0, 270.0, 140.0
S = 5  # px per mm
W, H = (X1 - X0 + 20) * S, (Y1 - Y0 + 34) * S


def px(x, y):
    return (x - X0 + 10) * S, (y - Y0 + 10) * S


out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" font-family="sans-serif">',
       f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>']


def rect(x0, y0, x1, y1, fill, stroke, dash="", op=1.0, sw=1.5):
    a, b = px(x0, y0)
    c, d = px(x1, y1)
    out.append(f'<rect x="{a:.1f}" y="{b:.1f}" width="{c - a:.1f}" height="{d - b:.1f}" fill="{fill}" fill-opacity="{op}" '
               f'stroke="{stroke}" stroke-width="{sw}" {"stroke-dasharray=%r" % dash if dash else ""}/>')


def text(x, y, s, size=11, color="#222", anchor="middle", weight="normal"):
    a, b = px(x, y)
    out.append(f'<text x="{a:.1f}" y="{b:.1f}" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>')


def line(pts, color, w=3, dash=""):
    d = " ".join(f"{'M' if i == 0 else 'L'}{px(*p)[0]:.1f},{px(*p)[1]:.1f}" for i, p in enumerate(pts))
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" {"stroke-dasharray=%r" % dash if dash else ""}/>')


# board
rect(X0, Y0, X1, Y1, "#f4f1e8", "#555", sw=2)
# zones the plan reserves
rect(139, 40, 171, 62, "#7b5ea7", "#7b5ea7", "6,4", 0.12)
text(155, 61, "T1S line zone (B)", 10, "#5b3e87")
rect(178, 30.5, 240, 59, "#2e86de", "#2e86de", "6,4", 0.08)
text(226, 34, "MCU zone (B)", 10, "#1b5fa8")
rect(150, 30.5, 178, 40, "#2e86de", "#2e86de", "3,3", 0.06)
text(164, 36, "PHY zone", 9, "#1b5fa8")
# heat zones
rect(88, 70, 152, 96, "#e17055", "#e17055", "2,3", 0.10)
text(120, 73.5, "heat: FET bank + shunt, 60 A", 10, "#a3402a")
for r in ("U601", "U701", "U801"):
    x, y, _ = P[r]
    rect(x - 7, y - 5, x + 7, y + 5, "#e17055", "#e17055", "2,3", 0.10)
    text(x, y - 6, f"heat: {r} 2 x 10 A", 9, "#a3402a")
# busbars and their copper rule areas
for x0, y0, x1, y1, lab in ((66.975, 61.075, 243.025, 80.125, "GND busbar 3/4 in: F.Cu GND only"),
                            (92.475, 90.075, 217.525, 109.125, "VBAT_IN busbar 3/4 in: F.Cu VBAT_IN only")):
    rect(x0, y0, x1, y1, "#c58b3a", "#9a6418", "", 0.30, 2)
    text((x0 + x1) / 2, y0 + 4.5, lab, 11, "#6e4510", weight="bold")
# lid bosses
h = next(h for h in plan["heights"] if h.get("circles"))
for c in h["circles"]:
    a, b = px(c["x"], c["y"])
    out.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="{c["d"] / 2 * S:.1f}" fill="#999" fill-opacity="0.35" stroke="#555"/>')
text(93, 117, "lid bosses Ø8: parts there under 5.0 mm", 9, "#444")
# fixed parts
for r, (x, y, side) in P.items():
    if not r.startswith("J9"):
        continue
    if r in ("J901", "J902", "J910", "J911"):
        a, b = px(x, y)
        out.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="{4.65 * S:.1f}" fill="none" stroke="#9a6418" stroke-width="2"/>')
        text(x, y + 1.5, r, 10, "#6e4510", weight="bold")
    else:
        rect(x - 9, y - 4, x + 9, y + 4, "#dfe6e9", "#636e72", "", 0.9)
        text(x, y + 1.5, r, 10, "#2d3436", weight="bold")
# critical-net lanes
j912, j903 = (135.5, 46), (174.5, 46)
line([j912, j903], "#7b5ea7", 4)
text(155, 44, "T1S trunk (100 Ω pair, B/In)", 10, "#5b3e87")
line([(155, 47), (155, 54), P["FL501"][:2], P["U501"][:2]], "#7b5ea7", 3, "6,3")
line([P["U501"][:2], P["U401"][:2]], "#0984e3", 3)
text(188, 56.5, "RMII 50 MHz", 9, "#0652a3")
line([P["Y401"][:2], (P["U401"][0] - 4, P["U401"][1])], "#00b894", 3)
line([P["R201"][:2], P["U202"][:2]], "#d63031", 3, "8,4")
text((P["R201"][0] + P["U202"][0]) / 2, 86, "INA228 Kelvin pair: 71 mm now, budget 10 mm", 10, "#b71c1c", weight="bold")
for r in ("U401", "U501", "U202", "R201", "Y401"):
    x, y, _ = P[r]
    a, b = px(x, y)
    out.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="5" fill="#2d3436"/>')
    text(x + 1, y - 1.5, r, 9, "#2d3436", "start")
# legend
ly = Y1 + 8
for i, (c, lab) in enumerate((("#c58b3a", "busbar copper rule area"), ("#7b5ea7", "T1S"), ("#0984e3", "RMII"),
                              ("#00b894", "MCU crystal"), ("#d63031", "Kelvin sense"), ("#e17055", "heat zone"))):
    x = X0 + 2 + i * 38
    rect(x, ly - 2.5, x + 4, ly + 0.5, c, c, "", 0.6)
    text(x + 5, ly + 0.3, lab, 10, "#222", "start")
out.append("</svg>")
os.makedirs(os.path.join(HERE, "decisions", "img"), exist_ok=True)
open(os.path.join(HERE, "decisions", "img", "plan.svg"), "w").write("\n".join(out))
print("decisions/img/plan.svg")
