#!/usr/bin/env python3
"""Draw a 3V3 feed option over a window of the board, one panel per layer (Node60, 2026-11-05).

    $KPY trunk_picture.py COPPER.json RESULT.json OPTION OUT.png [--box X0,Y0,X1,Y1] [--scale 6]
        [--layers F.Cu,B.Cu,In3.Cu] [--title T] [--sub S] [--mark REF.PAD:label,...]
        [--overlay RESULT.json:OPTION] [--pocket X0,Y0,X1,Y1 ...] [--feeds NAME|NAME...]

Seen from above. Pours tinted by kind (VBAT nets blue, GND grey, outputs amber, 3V3 green), busbar
F.Cu areas outlined, pads grey, vias dots; the option's feeds thick (one colour each) with their vias
ringed; an overlay option dashed grey; pockets dashed magenta; marked pads ringed and labelled.
Each panel is clipped to the window.
"""
import argparse
import json

from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("copper"); ap.add_argument("result"); ap.add_argument("option"); ap.add_argument("out")
ap.add_argument("--box", default="60,56,242,124"); ap.add_argument("--scale", type=float, default=6.0)
ap.add_argument("--layers", default="F.Cu,B.Cu"); ap.add_argument("--title", default=""); ap.add_argument("--sub", default=None)
ap.add_argument("--mark", default=""); ap.add_argument("--overlay", default="")
ap.add_argument("--pocket", action="append", default=[]); ap.add_argument("--feeds", default="")
a = ap.parse_args()
C = json.load(open(a.copper)); R = json.load(open(a.result))[a.option]
X0, Y0, X1, Y1 = (float(v) for v in a.box.split(","))
S = a.scale
PW, PH = int((X1 - X0) * S), int((Y1 - Y0) * S)
LAY = a.layers.split(",")


def font(n, bold=False):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf", n)
    except OSError:
        return ImageFont.load_default()


F15, F12, F11 = font(16, True), font(13), font(11)
FEED = [(214, 40, 40), (30, 110, 220), (20, 150, 70), (200, 110, 0), (150, 60, 190), (0, 150, 160), (110, 110, 110), (230, 60, 150), (90, 70, 40)]
feeds = [f for f in R["feeds"] if not a.feeds or f["name"] in a.feeds.split("|")]
fcol = {f["name"]: FEED[i % len(FEED)] for i, f in enumerate(R["feeds"])}


def kind(net):
    if "VBAT" in net:
        return (90, 140, 210, 75)
    if net == "GND":
        return (150, 150, 150, 40)
    if "/OUT" in net:
        return (235, 160, 50, 95)
    if "3V3" in net:
        return (60, 175, 90, 95)
    return (180, 120, 200, 55)


def P(x, y):
    return ((x - X0) * S, (y - Y0) * S)


def panel(lname):
    im = Image.new("RGB", (PW, PH), (251, 250, 246)); d = ImageDraw.Draw(im, "RGBA")
    for z in C["zones"]:
        if z["layer"] != lname:
            continue
        for o in z["fill"]:
            pts = [P(x, y) for x, y in o["outer"]]
            if len(pts) > 2:
                d.polygon(pts, fill=kind(z["net"]))
            for h in o["holes"]:
                hp = [P(x, y) for x, y in h]
                if len(hp) > 2:
                    d.polygon(hp, fill=(251, 250, 246, 255))
    for p in C["pads"]:
        for o in p["layers"].get(lname, []):
            pts = [P(x, y) for x, y in o["outer"]]
            if len(pts) > 2:
                d.polygon(pts, fill=(150, 148, 140, 220))
    for v in C["vias"]:
        if X0 - 1 <= v["x"] <= X1 + 1 and Y0 - 1 <= v["y"] <= Y1 + 1:
            q = P(v["x"], v["y"]); r = max(1.0, v["size"] / 2 * S * 0.8)
            d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=(105, 105, 105, 140))
    for t in C["tracks"]:
        if t["layer"] == lname:
            d.line([P(*t["a"]), P(*t["b"])], fill=(95, 95, 95, 200), width=max(1, int(t["w"] * S)))
    if lname == "F.Cu":
        for ar in C["areas"]:
            if ar["name"].startswith("BUSBAR"):
                for o in ar["outline"]:
                    pts = [P(x, y) for x, y in o["outer"]]
                    d.line(pts + [pts[0]], fill=(40, 60, 160), width=2)
                    xs = [x for x, _ in o["outer"]]; ys = [y for _, y in o["outer"]]
                    d.text(P(max(min(xs), X0) + 1, max(min(ys), Y0) + 0.4), ar["name"].replace("BUSBAR_", "") + " busbar: F.Cu tracks of its own net only",
                           fill=(40, 60, 160), font=F11)
    for pk in a.pocket:
        q0, q1, q2, q3 = (float(v) for v in pk.split(","))
        for (xa, ya, xb, yb) in ((q0, q1, q2, q1), (q2, q1, q2, q3), (q2, q3, q0, q3), (q0, q3, q0, q1)):
            n = max(2, int(((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5 * S / 8))
            for k in range(0, n, 2):
                d.line([P(xa + (xb - xa) * k / n, ya + (yb - ya) * k / n), P(xa + (xb - xa) * (k + 1) / n, ya + (yb - ya) * (k + 1) / n)],
                       fill=(200, 0, 120), width=2)
    if a.overlay:
        rp, on = a.overlay.rsplit(":", 1)
        for f in json.load(open(rp))[on]["feeds"]:
            for pc in f["pieces"]:
                for t in pc.get("tracks", []):
                    if t["layer"] != lname:
                        continue
                    pts = [P(x, y) for x, y in t["pts"]]
                    for i in range(len(pts) - 1):
                        (xa, ya), (xb, yb) = pts[i], pts[i + 1]
                        n = max(2, int(((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5 / 8))
                        for k in range(0, n, 2):
                            d.line([(xa + (xb - xa) * k / n, ya + (yb - ya) * k / n), (xa + (xb - xa) * (k + 1) / n, ya + (yb - ya) * (k + 1) / n)],
                                   fill=(60, 60, 60), width=max(3, int(0.45 * S)))
    for f in feeds:
        c = fcol[f["name"]]
        for pc in f["pieces"]:
            for t in pc.get("tracks", []):
                if t["layer"] == lname:
                    d.line([P(x, y) for x, y in t["pts"]], fill=c + (255,), width=max(3, int(0.6 * S)))
            for (x, y) in pc.get("vias", []):
                q = P(x, y); r = max(4, 0.45 * S)
                d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], outline=c + (255,), width=3)
    pads = {(p["ref"], p["num"]): p for p in C["pads"]}
    for m in [m for m in a.mark.split(",") if m]:
        key, _, lab = m.partition(":")
        r_, n_ = key.split(".")
        p = pads.get((r_, n_))
        if p and lname in p["layers"]:
            q = P(p["x"], p["y"]); r = max(5, 0.55 * S)
            d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], outline=(200, 0, 120), width=2)
            d.text((q[0] + r + 2, q[1] - 7), lab or key, fill=(160, 0, 95), font=F12)
    d.rectangle([0, 0, PW - 1, PH - 1], outline=(185, 185, 185))
    d.rectangle([0, 0, int(d.textlength(lname + " (seen from above)", font=F12)) + 10, 18], fill=(251, 250, 246, 230))
    d.text((5, 2), f"{lname} (seen from above)", fill=(40, 40, 40), font=F12)
    return im


PAD, TOP, GAP = 14, 50 if (a.sub is not None or R.get("about")) else 30, 12
legend_rows = []
row, x = [], 0
for f in feeds:
    t = f"{f['name']}: {f['total']['mm']} mm, {f['total']['vias']} vias" + ("" if f["ok"] else " (failed)")
    w = 26 + int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(t, font=F12)) + 20
    if x + w > PW and row:
        legend_rows.append(row); row, x = [], 0
    row.append((f, t)); x += w
if row:
    legend_rows.append(row)
H = TOP + len(LAY) * (PH + GAP) + 20 * len(legend_rows) + 10
img = Image.new("RGB", (PW + 2 * PAD, H), (251, 250, 246)); d = ImageDraw.Draw(img)
d.text((PAD, 6), a.title or a.option, fill=(20, 20, 20), font=F15)
if a.sub is not None or R.get("about"):
    d.text((PAD, 28), a.sub if a.sub is not None else R.get("about", ""), fill=(70, 70, 70), font=F12)
for k, l in enumerate(LAY):
    img.paste(panel(l), (PAD, TOP + k * (PH + GAP)))
ly = TOP + len(LAY) * (PH + GAP)
for row in legend_rows:
    x = PAD
    for f, t in row:
        c = fcol[f["name"]]
        d.rectangle([x, ly + 5, x + 18, ly + 11], fill=c)
        d.text((x + 24, ly), t, fill=(30, 30, 30), font=F12)
        x += 26 + int(d.textlength(t, font=F12)) + 20
    ly += 20
img.save(a.out)
print(a.out)
